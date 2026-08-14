"""
ตัวช่วยสร้างข้อมูลสำหรับการทดสอบเท่านั้น

หมายเหตุ: นี่คือ test fixture ตามข้อกำหนดข้อ 7 (อนุญาตให้ใช้ในเทสต์)
ไม่ใช่ mock data ที่ปนอยู่ในโค้ดของระบบจริง — ไฟล์นี้อยู่ใต้ tests/ เท่านั้น
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from apps.accounts.models import User
from apps.clinics.models import Clinic
from apps.common.roles import UserRole
from apps.doctors.models import Doctor, DoctorSchedule, TimeBlock
from apps.patients.models import Patient
from apps.services.models import ServiceType

BANGKOK = ZoneInfo("Asia/Bangkok")


def next_monday(reference: date | None = None) -> date:
    """
    วันจันทร์ถัดไปในอนาคตเสมอ

    เทสต์ใช้วันในอนาคตเพื่อไม่ให้กฎ "ห้ามจองเวลาที่ผ่านไปแล้ว" มารบกวนผลลัพธ์
    """
    reference = reference or date.today()
    days_ahead = (7 - reference.weekday()) % 7 or 7
    return reference + timedelta(days=days_ahead)


def bangkok_datetime(target_date: date, hour: int, minute: int = 0) -> datetime:
    """ประกอบเวลาไทยสำหรับใช้ในเทสต์"""
    return datetime.combine(target_date, time(hour, minute), tzinfo=BANGKOK)


class ClinicTestDataMixin:
    """สร้างชุดข้อมูลพื้นฐาน (สาขา/แพทย์/บริการ/คนไข้) ให้ TestCase ใช้ซ้ำ"""

    def create_clinic(
        self,
        *,
        code: str = "BKK",
        name: str = "สาขาสุขุมวิท",
        opening_time: time = time(9, 0),
        closing_time: time = time(18, 0),
        slot_interval_minutes: int = 15,
        non_doctor_service_capacity: int = 1,
    ) -> Clinic:
        return Clinic.objects.create(
            name=name,
            code=code,
            opening_time=opening_time,
            closing_time=closing_time,
            timezone="Asia/Bangkok",
            slot_interval_minutes=slot_interval_minutes,
            non_doctor_service_capacity=non_doctor_service_capacity,
        )

    def create_user(
        self,
        *,
        clinic: Clinic | None,
        email: str,
        role: str = UserRole.STAFF,
        password: str = "TestPass!2026",
    ) -> User:
        return User.objects.create_user(
            email=email,
            password=password,
            full_name=email.split("@")[0],
            role=role,
            clinic=clinic,
        )

    def create_doctor(
        self,
        *,
        clinic: Clinic,
        email: str = "doctor@clinic.test",
        display_name: str = "พญ. ทดสอบ",
        weekly_hours: list[tuple[int, time, time]] | None = None,
    ) -> Doctor:
        """
        สร้างแพทย์พร้อมตารางออกตรวจ (ค่าเริ่มต้น: จันทร์ 09:00-17:00)

        ส่ง `weekly_hours=[]` เพื่อสร้างแพทย์ที่ยังไม่มีตารางออกตรวจเลย
        (ต่างจากไม่ส่งค่ามา ซึ่งจะได้ตารางเริ่มต้น)
        """
        user = self.create_user(clinic=clinic, email=email, role=UserRole.DOCTOR)
        doctor = Doctor.objects.create(user=user, clinic=clinic, display_name=display_name)

        default_hours = [(0, time(9, 0), time(17, 0))]
        for day_of_week, start_time, end_time in (
            default_hours if weekly_hours is None else weekly_hours
        ):
            DoctorSchedule.objects.create(
                doctor=doctor,
                clinic=clinic,
                day_of_week=day_of_week,
                start_time=start_time,
                end_time=end_time,
            )
        return doctor

    def create_time_block(
        self,
        *,
        doctor: Doctor,
        start: datetime,
        end: datetime,
        reason: str = "lunch",
        is_recurring: bool = False,
        recurrence: str = "none",
    ) -> TimeBlock:
        return TimeBlock.objects.create(
            doctor=doctor,
            clinic=doctor.clinic,
            start_datetime=start,
            end_datetime=end,
            reason=reason,
            is_recurring=is_recurring,
            recurrence=recurrence,
        )

    def create_service(
        self,
        *,
        name: str = "ฉีดโบลดริ้วรอย",
        duration_minutes: int = 30,
        requires_doctor: bool = True,
        price: str = "3500.00",
    ) -> ServiceType:
        return ServiceType.objects.create(
            name=name,
            duration_minutes=duration_minutes,
            requires_doctor=requires_doctor,
            price=Decimal(price),
        )

    def create_patient(
        self,
        *,
        clinic: Clinic,
        first_name: str = "สมหญิง",
        last_name: str = "ใจดี",
        phone: str = "0812345678",
        patient_code: str | None = None,
    ) -> Patient:
        return Patient.objects.create(
            patient_code=patient_code or f"{clinic.code}-{Patient.objects.count() + 1:06d}",
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            home_clinic=clinic,
        )
