"""
การนัดหมาย/คิว — เอนทิตีกลางของทั้งระบบ

ทุกการจองสร้างโดยเจ้าหน้าที่ (ไม่มีหน้าจองสาธารณะ) `source` จึงมีแค่
`staff_created` (จองล่วงหน้า) และ `walk_in` (เดินเข้ามาหน้าร้าน)

logic ที่ผูกกับตัวข้อมูลโดยตรง เช่น การเช็คว่าคิวสองคิวชนกันหรือไม่
และการเปลี่ยนสถานะที่อนุญาต ถูกเก็บไว้เป็น method ของ model
ส่วน logic ที่ต้องดูข้อมูลรอบข้าง (ตารางแพทย์ เวลาว่าง) อยู่ใน services.py
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.exceptions import InvalidStatusTransitionError
from apps.common.models import AuditableModel
from apps.common.time_intervals import TimeInterval


class AppointmentStatus(models.TextChoices):
    BOOKED = "booked", "จองแล้ว"
    CONFIRMED = "confirmed", "ยืนยันแล้ว"
    CHECKED_IN = "checked_in", "รอพบแพทย์"
    IN_PROGRESS = "in_progress", "กำลังรักษา"
    COMPLETED = "completed", "เสร็จสิ้น"
    CANCELLED = "cancelled", "ยกเลิก"
    NO_SHOW = "no_show", "ไม่มาตามนัด"


class AppointmentSource(models.TextChoices):
    STAFF_CREATED = "staff_created", "เจ้าหน้าที่จองให้"
    WALK_IN = "walk_in", "เดินเข้ามา (walk-in)"


#: สถานะที่ยังถือว่า "กินเวลา" ในตาราง — ใช้ทั้งตอนคำนวณ slot ว่างและตอนกันคิวชน
#: (ยกเลิกกับไม่มาตามนัด คืนเวลาให้ตารางเพื่อให้รับคิวอื่นแทนได้)
OCCUPYING_STATUSES: tuple[str, ...] = (
    AppointmentStatus.BOOKED,
    AppointmentStatus.CONFIRMED,
    AppointmentStatus.CHECKED_IN,
    AppointmentStatus.IN_PROGRESS,
    AppointmentStatus.COMPLETED,
)

#: สถานะปลายทางที่อนุญาตจากแต่ละสถานะ — ป้องกันการข้ามขั้นตอนหน้างาน
ALLOWED_STATUS_TRANSITIONS: dict[str, tuple[str, ...]] = {
    AppointmentStatus.BOOKED: (
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ),
    AppointmentStatus.CONFIRMED: (
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ),
    AppointmentStatus.CHECKED_IN: (
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    ),
    AppointmentStatus.IN_PROGRESS: (AppointmentStatus.COMPLETED,),
    AppointmentStatus.COMPLETED: (),
    AppointmentStatus.CANCELLED: (),
    AppointmentStatus.NO_SHOW: (),
}


class AppointmentQuerySet(models.QuerySet):
    """Query ที่ใช้ซ้ำบ่อย — รวมไว้ที่เดียวเพื่อไม่ให้เงื่อนไขเดียวกันกระจายหลายที่"""

    def occupying(self) -> "AppointmentQuerySet":
        """เฉพาะคิวที่ยังกินเวลาในตาราง"""
        return self.filter(status__in=OCCUPYING_STATUSES)

    def overlapping(self, start, end) -> "AppointmentQuerySet":
        """คิวที่ช่วงเวลาซ้อนทับกับช่วงที่ระบุ (ชนขอบพอดีไม่ถือว่าซ้อน)"""
        return self.filter(scheduled_start__lt=end, scheduled_end__gt=start)

    def for_clinic_day(self, clinic, day_start, day_end) -> "AppointmentQuerySet":
        return self.filter(clinic=clinic).overlapping(day_start, day_end)


class Appointment(AuditableModel):
    """การนัดหมายหนึ่งคิว"""

    Status = AppointmentStatus
    Source = AppointmentSource

    patient = models.ForeignKey(
        "patients.Patient", verbose_name="คนไข้", on_delete=models.PROTECT,
        related_name="appointments",
    )
    doctor = models.ForeignKey(
        "doctors.Doctor",
        verbose_name="แพทย์",
        on_delete=models.PROTECT,
        related_name="appointments",
        null=True,
        blank=True,
        help_text="เว้นว่างได้เฉพาะบริการที่ไม่ต้องมีแพทย์",
    )
    service_type = models.ForeignKey(
        "services.ServiceType", verbose_name="บริการ", on_delete=models.PROTECT,
        related_name="appointments",
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", verbose_name="สาขา", on_delete=models.PROTECT, related_name="appointments"
    )

    scheduled_start = models.DateTimeField("เวลานัดเริ่ม", db_index=True)
    scheduled_end = models.DateTimeField("เวลานัดสิ้นสุด")

    status = models.CharField(
        "สถานะ", max_length=15, choices=AppointmentStatus.choices,
        default=AppointmentStatus.BOOKED, db_index=True,
    )
    source = models.CharField(
        "ที่มาของคิว", max_length=15, choices=AppointmentSource.choices,
        default=AppointmentSource.STAFF_CREATED,
    )
    note = models.CharField(
        "โน้ตสั้น", max_length=255, blank=True, help_text='เช่น "แพ้ยาชา", "ขอหมอคนเดิม"'
    )

    # เวลาจริงหน้างาน — ใช้คำนวณเวลารอเฉลี่ยในรายงาน
    checked_in_at = models.DateTimeField("เวลาเช็คอิน", null=True, blank=True)
    started_at = models.DateTimeField("เวลาเริ่มรักษา", null=True, blank=True)
    completed_at = models.DateTimeField("เวลาเสร็จสิ้น", null=True, blank=True)
    cancelled_reason = models.CharField("เหตุผลที่ยกเลิก", max_length=255, blank=True)

    objects = AppointmentQuerySet.as_manager()

    class Meta:
        verbose_name = "การนัดหมาย"
        verbose_name_plural = "การนัดหมาย"
        ordering = ["scheduled_start"]
        indexes = [
            models.Index(fields=["clinic", "scheduled_start"]),
            models.Index(fields=["doctor", "scheduled_start"]),
            models.Index(fields=["status", "scheduled_start"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(scheduled_end__gt=models.F("scheduled_start")),
                name="appointment_end_after_start",
            )
        ]

    def __str__(self) -> str:
        return f"{self.patient.patient_code} {self.scheduled_start:%Y-%m-%d %H:%M} ({self.get_status_display()})"

    # ------------------------------------------------------------------
    # logic ที่ผูกกับตัวคิวโดยตรง
    # ------------------------------------------------------------------
    @property
    def interval(self) -> TimeInterval:
        """ช่วงเวลาของคิวนี้ในรูปแบบที่ใช้คำนวณร่วมกับตารางแพทย์ได้"""
        return TimeInterval(self.scheduled_start, self.scheduled_end)

    @property
    def occupies_slot(self) -> bool:
        return self.status in OCCUPYING_STATUSES

    def overlaps_with(self, other: "Appointment") -> bool:
        """คิวสองคิวชนกันหรือไม่ (นับเฉพาะคิวที่ยังกินเวลาอยู่)"""
        if not (self.occupies_slot and other.occupies_slot):
            return False
        return self.interval.overlaps_with(other.interval)

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in ALLOWED_STATUS_TRANSITIONS.get(self.status, ())

    def apply_status(self, new_status: str) -> None:
        """
        เปลี่ยนสถานะพร้อมบันทึกเวลาจริงของแต่ละขั้น (ยังไม่ save ลง DB)

        รวม logic ไว้ที่เดียวเพื่อให้ทุกทางเข้า (หน้าคิว, แพทย์, งานอัตโนมัติ)
        ได้ timestamp ครบเหมือนกัน
        """
        if new_status == self.status:
            return

        if not self.can_transition_to(new_status):
            raise InvalidStatusTransitionError(
                f"เปลี่ยนสถานะจาก '{self.get_status_display()}' ไปเป็น "
                f"'{AppointmentStatus(new_status).label}' ไม่ได้",
                details={"from": self.status, "to": new_status},
            )

        now = timezone.now()
        self.status = new_status
        if new_status == AppointmentStatus.CHECKED_IN and self.checked_in_at is None:
            self.checked_in_at = now
        elif new_status == AppointmentStatus.IN_PROGRESS and self.started_at is None:
            self.started_at = now
        elif new_status == AppointmentStatus.COMPLETED:
            self.completed_at = now

    @property
    def waiting_minutes(self) -> int | None:
        """เวลารอจริงตั้งแต่เช็คอินจนได้เริ่มรักษา (ใช้ในรายงาน)"""
        if self.checked_in_at and self.started_at:
            return int((self.started_at - self.checked_in_at).total_seconds() // 60)
        return None

    def clean(self) -> None:
        super().clean()
        if self.scheduled_start and self.scheduled_end and self.scheduled_start >= self.scheduled_end:
            raise ValidationError({"scheduled_end": "เวลาสิ้นสุดต้องหลังเวลาเริ่ม"})

        if self.service_type_id and self.service_type.requires_doctor and self.doctor_id is None:
            raise ValidationError({"doctor": "บริการนี้ต้องระบุแพทย์"})

        if self.doctor_id and self.clinic_id and self.doctor.clinic_id != self.clinic_id:
            raise ValidationError({"doctor": "แพทย์ที่เลือกไม่ได้อยู่ในสาขานี้"})
