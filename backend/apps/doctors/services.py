"""
Business logic ของฝั่งแพทย์ — คำนวณ "เวลาที่แพทย์ว่างตามตาราง" ของวันหนึ่ง

แยกออกจาก view/serializer ตามแนวทางของโปรเจกต์ และ scheduling นำไปใช้ต่อ
โดยหักคิวที่จองแล้วออกอีกชั้นหนึ่ง
"""
from __future__ import annotations

from datetime import date

from django.db.models import Q

from apps.common.time_intervals import IntervalSet, TimeInterval
from apps.common.timezone_utils import local_day_bounds
from apps.doctors.models import Doctor, DoctorSchedule, RecurrenceType, TimeBlock


class DoctorAvailabilityService:
    """คำนวณเวลาทำงาน/เวลาที่ถูกบล็อกของแพทย์หนึ่งคน"""

    def __init__(self, doctor: Doctor) -> None:
        self.doctor = doctor
        self.clinic = doctor.clinic
        self.timezone_name: str = doctor.clinic.timezone

    def working_intervals_on(self, target_date: date) -> IntervalSet:
        """
        เวลาออกตรวจของแพทย์ในวันนั้น หลังตัดให้อยู่ในเวลาเปิด-ปิดของสาขาแล้ว

        แพทย์ที่ถูกปิดใช้งาน (is_active=False) ถือว่าไม่มีเวลาว่างเลย
        """
        if not self.doctor.is_active:
            return IntervalSet([])

        schedules = DoctorSchedule.objects.filter(
            doctor=self.doctor, day_of_week=target_date.weekday(), is_active=True
        )
        intervals = [
            schedule.interval_on(target_date, self.timezone_name) for schedule in schedules
        ]
        return IntervalSet(intervals).clamped_to(self.clinic.opening_interval_on(target_date))

    def blocked_intervals_on(self, target_date: date) -> list[TimeInterval]:
        """ช่วงเวลาที่ถูกบล็อกในวันนั้น (แผ่รายการที่ตั้งค่าให้ซ้ำออกมาแล้ว)"""
        candidates = TimeBlock.objects.filter(doctor=self.doctor).filter(
            self._relevant_time_block_filter(target_date)
        )
        occurrences = [
            occurrence
            for time_block in candidates
            if (occurrence := time_block.occurrence_on(target_date, self.timezone_name)) is not None
        ]
        return occurrences

    def free_intervals_on(self, target_date: date) -> IntervalSet:
        """เวลาทำงาน − เวลาที่ถูกบล็อก (ยังไม่หักคิวที่จองแล้ว)"""
        return self.working_intervals_on(target_date).subtract(
            self.blocked_intervals_on(target_date)
        )

    def _relevant_time_block_filter(self, target_date: date) -> Q:
        """
        ดึงเฉพาะ TimeBlock ที่มีโอกาสเกี่ยวข้องกับวันนั้น เพื่อไม่ต้องโหลดทั้งตาราง

        - แบบไม่ซ้ำ: ต้องคาบเกี่ยวกับช่วงเวลาของวันนั้น
        - แบบซ้ำ: ต้องเริ่มก่อนจบวันนั้น และยังไม่พ้นวันสิ้นสุดการซ้ำ

        เป็นการกรองแบบ "กว้างไว้ก่อน" — `occurrence_on()` จะตัดช่วงจริงอีกชั้นหนึ่ง
        """
        day_start, day_end = local_day_bounds(target_date, self.timezone_name)

        single_occurrence = (
            Q(is_recurring=False)
            & Q(start_datetime__lt=day_end)
            & Q(end_datetime__gt=day_start)
        )
        recurring = (
            Q(is_recurring=True)
            & ~Q(recurrence=RecurrenceType.NONE)
            & Q(start_datetime__lt=day_end)
            & (Q(recurrence_end_date__isnull=True) | Q(recurrence_end_date__gte=target_date))
        )
        return single_occurrence | recurring
