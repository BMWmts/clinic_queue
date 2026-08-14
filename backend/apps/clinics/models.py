"""
สาขาของคลินิก (multi-branch)

ทุกข้อมูลปฏิบัติการ (แพทย์ ตาราง คิว) ผูกกับสาขา และค่าตั้งค่าที่มีผลต่อ
การคำนวณคิว เช่น เวลาเปิด-ปิด, ความละเอียดของตาราง (slot interval)
ถูกเก็บไว้ที่นี่ เพื่อให้แต่ละสาขากำหนดนโยบายของตัวเองได้
"""
from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.time_intervals import TimeInterval
from apps.common.timezone_utils import combine_local

branch_code_validator = RegexValidator(
    regex=r"^[A-Z0-9\-]{2,20}$",
    message="รหัสสาขาใช้ได้เฉพาะ A-Z, 0-9 และ - ความยาว 2-20 ตัวอักษร",
)


class SmsProvider(models.TextChoices):
    """ผู้ให้บริการ SMS — แต่ละสาขาเลือกใช้คนละเจ้าได้"""

    DEFAULT = "default", "ใช้ค่าเริ่มต้นของระบบ"
    CONSOLE = "console", "เขียนลง log (สำหรับพัฒนา)"
    THAIBULKSMS = "thaibulksms", "Thai Bulk SMS"
    TWILIO = "twilio", "Twilio"


class Clinic(TimeStampedModel):
    """สาขาหนึ่งของคลินิก"""

    name = models.CharField("ชื่อสาขา", max_length=150)
    code = models.CharField(
        "รหัสสาขา", max_length=20, unique=True, validators=[branch_code_validator],
        help_text="ใช้เป็น prefix ของรหัสคนไข้ เช่น BKK",
    )
    address = models.TextField("ที่อยู่", blank=True)
    phone = models.CharField("เบอร์โทรสาขา", max_length=20, blank=True)

    opening_time = models.TimeField("เวลาเปิดทำการ")
    closing_time = models.TimeField("เวลาปิดทำการ")
    timezone = models.CharField(
        "โซนเวลา", max_length=64, default="Asia/Bangkok",
        help_text="ใช้แปลงเวลาที่เก็บเป็น UTC ในฐานข้อมูลให้เป็นเวลาท้องถิ่นของสาขา",
    )

    slot_interval_minutes = models.PositiveSmallIntegerField(
        "ความละเอียดของตารางคิว (นาที)",
        default=15,
        validators=[MinValueValidator(5), MaxValueValidator(120)],
        help_text="ระบบจะเสนอเวลาเริ่มคิวเป็นช่วง ๆ ตามค่านี้ เช่น ทุก 15 นาที",
    )
    non_doctor_service_capacity = models.PositiveSmallIntegerField(
        "จำนวนเคสพร้อมกันสูงสุดของบริการที่ไม่ต้องมีแพทย์",
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text="ใช้เป็นเพดานกันการรับคิวเกินกำลังของสาขาสำหรับบริการที่ไม่ต้องใช้แพทย์",
    )

    sms_provider = models.CharField(
        "ผู้ให้บริการ SMS", max_length=20, choices=SmsProvider.choices,
        default=SmsProvider.DEFAULT,
    )
    sms_sender_name = models.CharField(
        "ชื่อผู้ส่ง SMS", max_length=20, blank=True,
        help_text="ชื่อที่แสดงเป็นผู้ส่งข้อความ (ตามที่ลงทะเบียนไว้กับผู้ให้บริการ)",
    )

    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "สาขา"
        verbose_name_plural = "สาขา"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(closing_time__gt=models.F("opening_time")),
                name="clinic_closing_time_after_opening_time",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def clean(self) -> None:
        super().clean()
        if self.opening_time and self.closing_time and self.opening_time >= self.closing_time:
            raise ValidationError({"closing_time": "เวลาปิดต้องหลังเวลาเปิด"})

    def save(self, *args, **kwargs) -> None:
        self.code = self.code.upper().strip()
        super().save(*args, **kwargs)

    def opening_interval_on(self, target_date: date) -> TimeInterval:
        """
        ช่วงเวลาเปิดทำการของวันนั้นในรูป datetime พร้อม timezone

        ใช้เป็นขอบเขตนอกสุดของการคำนวณ slot — ต่อให้แพทย์ตั้งตารางไว้กว้างกว่า
        ระบบก็จะไม่เสนอเวลานอกเวลาทำการของสาขา
        """
        return TimeInterval(
            combine_local(target_date, self.opening_time, self.timezone),
            combine_local(target_date, self.closing_time, self.timezone),
        )
