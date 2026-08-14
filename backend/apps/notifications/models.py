"""
บันทึกการส่ง SMS

เก็บทุกครั้งที่ระบบพยายามส่งข้อความ เพื่อให้ตรวจสอบย้อนหลังได้ว่า
คนไข้ได้รับการแจ้งเตือนหรือไม่ และใช้กันการส่งซ้ำ (idempotency)
"""
from __future__ import annotations

from django.db import models

from apps.common.models import TimeStampedModel


class SmsStatus(models.TextChoices):
    PENDING = "pending", "รอส่ง"
    SENT = "sent", "ส่งแล้ว"
    FAILED = "failed", "ส่งไม่สำเร็จ"


class SmsKind(models.TextChoices):
    APPOINTMENT_REMINDER = "appointment_reminder", "แจ้งเตือนนัดหมาย"
    MANUAL = "manual", "ส่งด้วยเจ้าหน้าที่"


class SMSLog(TimeStampedModel):
    """หนึ่งแถว = หนึ่งข้อความที่ระบบพยายามส่ง"""

    clinic = models.ForeignKey(
        "clinics.Clinic", verbose_name="สาขา", on_delete=models.PROTECT, related_name="sms_logs"
    )
    patient = models.ForeignKey(
        "patients.Patient", verbose_name="คนไข้", on_delete=models.PROTECT, related_name="sms_logs"
    )
    appointment = models.ForeignKey(
        "scheduling.Appointment",
        verbose_name="การนัดหมาย",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sms_logs",
    )

    kind = models.CharField(
        "ประเภทข้อความ", max_length=30, choices=SmsKind.choices,
        default=SmsKind.APPOINTMENT_REMINDER,
    )
    message = models.TextField("ข้อความที่ส่ง")
    status = models.CharField(
        "สถานะ", max_length=10, choices=SmsStatus.choices, default=SmsStatus.PENDING, db_index=True
    )
    provider = models.CharField("ผู้ให้บริการที่ใช้ส่ง", max_length=20, blank=True)
    provider_message_id = models.CharField("รหัสอ้างอิงจากผู้ให้บริการ", max_length=100, blank=True)
    error_message = models.CharField("สาเหตุที่ส่งไม่สำเร็จ", max_length=255, blank=True)
    sent_at = models.DateTimeField("เวลาที่ส่งสำเร็จ", null=True, blank=True)

    class Meta:
        verbose_name = "บันทึกการส่ง SMS"
        verbose_name_plural = "บันทึกการส่ง SMS"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["clinic", "-created_at"])]
        constraints = [
            # กันการแจ้งเตือนนัดเดิมซ้ำ: หนึ่งนัดมีข้อความเตือนได้ครั้งเดียว
            # (แถวที่ส่งไม่สำเร็จไม่ถูกนับ เพื่อให้ retry ได้)
            models.UniqueConstraint(
                fields=["appointment", "kind"],
                condition=~models.Q(status=SmsStatus.FAILED),
                name="sms_unique_reminder_per_appointment",
            )
        ]

    def __str__(self) -> str:
        return f"SMS → {self.patient.masked_phone} ({self.get_status_display()})"

    def mark_sent(self, provider: str, provider_message_id: str = "") -> None:
        from django.utils import timezone

        self.status = SmsStatus.SENT
        self.provider = provider
        self.provider_message_id = provider_message_id
        self.sent_at = timezone.now()
        self.save(update_fields=["status", "provider", "provider_message_id", "sent_at", "updated_at"])

    def mark_failed(self, provider: str, error_message: str) -> None:
        self.status = SmsStatus.FAILED
        self.provider = provider
        self.error_message = error_message[:255]
        self.save(update_fields=["status", "provider", "error_message", "updated_at"])
