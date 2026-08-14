"""
แพทย์ ตารางออกตรวจประจำสัปดาห์ และช่วงเวลาที่ถูกบล็อก

โมเดลสามตัวนี้เป็น "ข้อมูลตั้งต้น" ของการคำนวณเวลาว่าง:
    DoctorSchedule  = เวลาที่แพทย์ออกตรวจ (recurring รายสัปดาห์)
    TimeBlock       = เวลาที่ถูกตัดออก (พักเที่ยง/ลา/เคสด่วน) รองรับ recurring
"""
from __future__ import annotations

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from apps.common.models import TimeStampedModel
from apps.common.time_intervals import TimeInterval
from apps.common.timezone_utils import combine_local, local_day_bounds, to_local

hex_color_validator = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
    message="ต้องเป็นรหัสสีแบบ hex เช่น #2563eb",
)


class Weekday(models.IntegerChoices):
    """วันในสัปดาห์ — ใช้เลขเดียวกับ `date.weekday()` ของ Python (จันทร์ = 0)"""

    MONDAY = 0, "จันทร์"
    TUESDAY = 1, "อังคาร"
    WEDNESDAY = 2, "พุธ"
    THURSDAY = 3, "พฤหัสบดี"
    FRIDAY = 4, "ศุกร์"
    SATURDAY = 5, "เสาร์"
    SUNDAY = 6, "อาทิตย์"


class Doctor(TimeStampedModel):
    """โปรไฟล์แพทย์ที่ผูกกับบัญชีผู้ใช้ role=doctor"""

    user = models.OneToOneField(
        "accounts.User",
        verbose_name="บัญชีผู้ใช้",
        on_delete=models.PROTECT,
        related_name="doctor_profile",
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", verbose_name="สาขา", on_delete=models.PROTECT, related_name="doctors"
    )
    display_name = models.CharField("ชื่อที่แสดง", max_length=150)
    specialties = models.CharField("ความเชี่ยวชาญ", max_length=255, blank=True)
    color = models.CharField(
        "สีในปฏิทิน", max_length=7, default="#2563eb", validators=[hex_color_validator]
    )
    is_active = models.BooleanField("ออกตรวจอยู่", default=True)

    class Meta:
        verbose_name = "แพทย์"
        verbose_name_plural = "แพทย์"
        ordering = ["display_name"]
        indexes = [models.Index(fields=["clinic", "is_active"])]

    def __str__(self) -> str:
        return self.display_name

    def clean(self) -> None:
        super().clean()
        # แพทย์ต้องอยู่สาขาเดียวกับบัญชีผู้ใช้ของตัวเอง มิฉะนั้น branch scoping
        # ของทั้งสองฝั่งจะขัดกัน (login เห็นสาขาหนึ่ง แต่คิวไปโผล่อีกสาขา)
        if self.user_id and self.user.clinic_id and self.user.clinic_id != self.clinic_id:
            raise ValidationError({"clinic": "สาขาของแพทย์ต้องตรงกับสาขาของบัญชีผู้ใช้"})


class DoctorSchedule(TimeStampedModel):
    """ตารางออกตรวจประจำสัปดาห์ (หนึ่งแถว = หนึ่งช่วงเวลาของหนึ่งวัน)"""

    doctor = models.ForeignKey(
        Doctor, verbose_name="แพทย์", on_delete=models.CASCADE, related_name="schedules"
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", verbose_name="สาขา", on_delete=models.PROTECT,
        related_name="doctor_schedules",
    )
    day_of_week = models.PositiveSmallIntegerField("วันในสัปดาห์", choices=Weekday.choices)
    start_time = models.TimeField("เวลาเริ่มออกตรวจ")
    end_time = models.TimeField("เวลาเลิกออกตรวจ")
    is_active = models.BooleanField("ใช้งานอยู่", default=True)

    class Meta:
        verbose_name = "ตารางออกตรวจ"
        verbose_name_plural = "ตารางออกตรวจ"
        ordering = ["day_of_week", "start_time"]
        indexes = [models.Index(fields=["doctor", "day_of_week", "is_active"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="doctor_schedule_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["doctor", "day_of_week", "start_time"],
                name="doctor_schedule_unique_start_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.doctor.display_name} {self.get_day_of_week_display()} {self.start_time}-{self.end_time}"

    def clean(self) -> None:
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": "เวลาเลิกต้องหลังเวลาเริ่ม"})

        if self.doctor_id:
            self.clinic = self.doctor.clinic  # สาขาต้องตามแพทย์เสมอ
            if self._overlaps_existing_schedule():
                raise ValidationError(
                    {"start_time": "ช่วงเวลานี้ทับกับตารางออกตรวจอื่นของแพทย์ในวันเดียวกัน"}
                )

    def _overlaps_existing_schedule(self) -> bool:
        """ตารางของแพทย์คนเดียวกันในวันเดียวกันต้องไม่ทับกัน (ป้องกันการนับเวลาว่างซ้ำ)"""
        siblings = DoctorSchedule.objects.filter(
            doctor_id=self.doctor_id, day_of_week=self.day_of_week
        ).exclude(pk=self.pk)
        return siblings.filter(
            start_time__lt=self.end_time, end_time__gt=self.start_time
        ).exists()

    def save(self, *args, **kwargs) -> None:
        if self.doctor_id and not self.clinic_id:
            self.clinic = self.doctor.clinic
        super().save(*args, **kwargs)

    def interval_on(self, target_date: date, timezone_name: str) -> TimeInterval:
        """แปลงตารางประจำสัปดาห์เป็นช่วงเวลาจริงของวันที่ระบุ"""
        return TimeInterval(
            combine_local(target_date, self.start_time, timezone_name),
            combine_local(target_date, self.end_time, timezone_name),
        )


class TimeBlockReason(models.TextChoices):
    LUNCH = "lunch", "พักเที่ยง"
    MEETING = "meeting", "ประชุม"
    URGENT_CASE = "urgent_case", "เคสด่วน"
    LEAVE = "leave", "ลา"
    OTHER = "other", "อื่น ๆ"


class RecurrenceType(models.TextChoices):
    NONE = "none", "ไม่ซ้ำ"
    DAILY = "daily", "ทุกวัน"
    WEEKLY = "weekly", "ทุกสัปดาห์"


class TimeBlock(TimeStampedModel):
    """
    ช่วงเวลาที่แพทย์ไม่รับคิว

    กรณีซ้ำ (เช่น พักเที่ยงทุกวัน) เก็บเป็นแถวเดียวแล้ว "แผ่" ออกตอนคำนวณ
    ด้วย `occurrence_on()` เพื่อไม่ให้ตารางบวมด้วยแถวซ้ำ ๆ นับพันแถว
    """

    doctor = models.ForeignKey(
        Doctor, verbose_name="แพทย์", on_delete=models.CASCADE, related_name="time_blocks"
    )
    clinic = models.ForeignKey(
        "clinics.Clinic", verbose_name="สาขา", on_delete=models.PROTECT, related_name="time_blocks"
    )
    start_datetime = models.DateTimeField("เริ่มบล็อก", db_index=True)
    end_datetime = models.DateTimeField("สิ้นสุดบล็อก")
    reason = models.CharField(
        "เหตุผล", max_length=20, choices=TimeBlockReason.choices, default=TimeBlockReason.OTHER
    )
    note = models.CharField("บันทึกเพิ่มเติม", max_length=255, blank=True)

    is_recurring = models.BooleanField("ซ้ำตามรอบ", default=False)
    recurrence = models.CharField(
        "รูปแบบการซ้ำ", max_length=10, choices=RecurrenceType.choices, default=RecurrenceType.NONE
    )
    recurrence_end_date = models.DateField(
        "ซ้ำถึงวันที่", null=True, blank=True,
        help_text="เว้นว่างหมายถึงซ้ำไปเรื่อย ๆ",
    )

    class Meta:
        verbose_name = "ช่วงเวลาที่ถูกบล็อก"
        verbose_name_plural = "ช่วงเวลาที่ถูกบล็อก"
        ordering = ["start_datetime"]
        indexes = [models.Index(fields=["doctor", "start_datetime"])]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_datetime__gt=models.F("start_datetime")),
                name="time_block_end_after_start",
            )
        ]

    def __str__(self) -> str:
        return f"{self.doctor.display_name} {self.get_reason_display()} {self.start_datetime:%Y-%m-%d %H:%M}"

    def clean(self) -> None:
        super().clean()
        if self.start_datetime and self.end_datetime and self.start_datetime >= self.end_datetime:
            raise ValidationError({"end_datetime": "เวลาสิ้นสุดต้องหลังเวลาเริ่ม"})

        if self.is_recurring and self.recurrence == RecurrenceType.NONE:
            raise ValidationError({"recurrence": "ต้องเลือกรูปแบบการซ้ำเมื่อเปิดใช้งานการซ้ำ"})

        if self.is_recurring and self.duration > timedelta(days=1):
            raise ValidationError(
                {"end_datetime": "ช่วงเวลาที่ซ้ำตามรอบต้องยาวไม่เกิน 1 วัน"}
            )

        if self.doctor_id:
            self.clinic = self.doctor.clinic

    def save(self, *args, **kwargs) -> None:
        if self.doctor_id and not self.clinic_id:
            self.clinic = self.doctor.clinic
        if not self.is_recurring:
            self.recurrence = RecurrenceType.NONE
        super().save(*args, **kwargs)

    @property
    def duration(self) -> timedelta:
        return self.end_datetime - self.start_datetime

    def occurrence_on(self, target_date: date, timezone_name: str) -> TimeInterval | None:
        """
        ช่วงเวลาที่บล็อกนี้ครอบคลุมในวันที่ระบุ (คืน None ถ้าวันนั้นไม่โดนบล็อก)

        คำนวณโดยยึด "เวลานาฬิกาท้องถิ่น" ของสาขา เช่น พักเที่ยง 12:00-13:00
        ต้องเป็นเที่ยงวันตามเวลาไทยเสมอ ไม่ใช่เลื่อนตาม UTC
        """
        local_start = to_local(self.start_datetime, timezone_name)
        local_end = to_local(self.end_datetime, timezone_name)

        if not self.is_recurring or self.recurrence == RecurrenceType.NONE:
            # บล็อกครั้งเดียว: ตัดเฉพาะส่วนที่ตกอยู่ในวันนั้น (รองรับบล็อกยาวข้ามวัน เช่น ลาหลายวัน)
            day_start, day_end = local_day_bounds(target_date, timezone_name)
            block = TimeInterval(self.start_datetime, self.end_datetime)
            return block.clamped_to(TimeInterval(day_start, day_end))

        if self.recurrence_end_date and target_date > self.recurrence_end_date:
            return None
        if target_date < local_start.date():
            return None
        if self.recurrence == RecurrenceType.WEEKLY and target_date.weekday() != local_start.weekday():
            return None

        occurrence_start = combine_local(target_date, local_start.time(), timezone_name)
        return TimeInterval(occurrence_start, occurrence_start + (local_end - local_start))
