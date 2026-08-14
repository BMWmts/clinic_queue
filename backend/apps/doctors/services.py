"""
Business logic ของฝั่งแพทย์

    DoctorRegistrationService — รับแพทย์ใหม่เข้าทำงาน (บัญชี + โปรไฟล์)
    DoctorAvailabilityService — คำนวณ "เวลาที่แพทย์ว่างตามตาราง" ของวันหนึ่ง

แยกออกจาก view/serializer ตามแนวทางของโปรเจกต์ และ scheduling นำส่วนคำนวณเวลาว่าง
ไปใช้ต่อโดยหักคิวที่จองแล้วออกอีกชั้นหนึ่ง
"""
from __future__ import annotations

import logging
from datetime import date

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q

from apps.clinics.models import Clinic
from apps.common.roles import UserRole
from apps.common.time_intervals import IntervalSet, TimeInterval
from apps.common.timezone_utils import local_day_bounds
from apps.doctors.models import Doctor, DoctorSchedule, RecurrenceType, TimeBlock

logger = logging.getLogger(__name__)


class DoctorRegistrationService:
    """
    รับแพทย์เข้าทำงาน — สร้างบัญชีผู้ใช้และโปรไฟล์แพทย์พร้อมกัน

    แพทย์หนึ่งคนต้องมีทั้งบัญชีล็อกอิน (accounts.User role=doctor) และโปรไฟล์
    (doctors.Doctor) การสร้างทีละอย่างผ่าน API แยกกันมีความเสี่ยงว่าถ้าขั้นที่สอง
    ล้มเหลวจะเหลือบัญชีค้างที่ล็อกอินได้แต่ไม่มีตารางออกตรวจ จึงรวมไว้ใน
    transaction เดียวที่นี่
    """

    def __init__(self, clinic: Clinic, created_by=None) -> None:
        self.clinic = clinic
        self.created_by = created_by

    @transaction.atomic
    def create_doctor(
        self,
        *,
        email: str,
        full_name: str,
        password: str,
        display_name: str,
        phone: str = "",
        specialties: str = "",
        color: str = "#2563eb",
    ) -> Doctor:
        """สร้างบัญชี + โปรไฟล์แพทย์ในสาขานี้ (คืน Doctor ที่บันทึกแล้ว)"""
        user_model = get_user_model()

        user = user_model.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            phone=phone,
            role=UserRole.DOCTOR,
            clinic=self.clinic,
        )

        doctor = Doctor(
            user=user,
            clinic=self.clinic,
            display_name=display_name or full_name,
            specialties=specialties,
            color=color,
        )
        doctor.full_clean()
        doctor.save()

        logger.info("รับแพทย์ใหม่ #%s เข้าสาขา %s", doctor.pk, self.clinic.code)
        return doctor


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
