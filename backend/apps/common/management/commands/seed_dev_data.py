"""
สร้างข้อมูลตั้งต้นสำหรับการพัฒนา (dev seed)

สำคัญ: นี่คือสคริปต์แยกที่ต้องสั่งรันเอง ไม่ได้ผูกกับ business logic ใด ๆ
และไม่ทำงานบนสภาพแวดล้อม production (ต้องใส่ --force ถึงจะข้ามการป้องกัน)
ตามข้อกำหนดข้อ 7 ที่ห้ามฝัง mock data ไว้ในโค้ดหลัก

วิธีใช้:
    python manage.py seed_dev_data
    python manage.py seed_dev_data --reset   # ล้างข้อมูลตัวอย่างเดิมก่อนสร้างใหม่
"""
from __future__ import annotations

import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import User
from apps.clinics.models import Clinic
from apps.common.roles import UserRole
from apps.doctors.models import Doctor, DoctorSchedule, TimeBlock, Weekday
from apps.patients.services import PatientRegistrationService
from apps.scheduling.models import Appointment
from apps.scheduling.services import AppointmentBookingService, SlotAvailabilityService
from apps.services.models import ServiceType

DEFAULT_PASSWORD = "ClinicDev!2026"

#: จำนวนวันข้างหน้าที่ยอมไล่หา "วันที่แพทย์ออกตรวจ" เพื่อสร้างคิวตัวอย่าง
SAMPLE_SEARCH_DAYS = 7

CLINIC_SEED = [
    {
        "code": "BKK",
        "name": "คลินิกสาขาสุขุมวิท",
        "address": "123 ถนนสุขุมวิท กรุงเทพฯ",
        "phone": "021234567",
        "opening_time": time(9, 0),
        "closing_time": time(19, 0),
    },
    {
        "code": "CNX",
        "name": "คลินิกสาขาเชียงใหม่",
        "address": "45 ถนนนิมมานเหมินท์ เชียงใหม่",
        "phone": "052123456",
        "opening_time": time(10, 0),
        "closing_time": time(18, 0),
    },
]

SERVICE_SEED = [
    {"name": "ฉีดโบลดริ้วรอย", "category": "ฉีด", "duration_minutes": 30, "price": "8500.00"},
    {"name": "ฟิลเลอร์ร่องแก้ม", "category": "ฉีด", "duration_minutes": 45, "price": "12000.00"},
    {"name": "เลเซอร์หน้าใส", "category": "เลเซอร์", "duration_minutes": 60, "price": "3500.00"},
    {"name": "ปรึกษาแพทย์", "category": "ปรึกษา", "duration_minutes": 15, "price": "500.00"},
    {
        "name": "ดริปวิตามินผิว",
        "category": "ดริป",
        "duration_minutes": 60,
        "price": "2500.00",
        "requires_doctor": False,
    },
]

DOCTOR_SEED = {
    "BKK": [
        ("doctor.ploy@clinic.test", "พญ. พลอย รักษาดี", "#2563eb", [0, 1, 2, 3, 4]),
        ("doctor.non@clinic.test", "นพ. นนท์ ผิวใส", "#16a34a", [0, 2, 4, 5]),
    ],
    "CNX": [
        ("doctor.mint@clinic.test", "พญ. มิ้นท์ ใจงาม", "#db2777", [1, 2, 3, 4, 5]),
    ],
}

PATIENT_SEED = [
    ("สมหญิง", "ใจดี", "0811111111"),
    ("สมชาย", "รักสุขภาพ", "0822222222"),
    ("ปรียา", "แสงทอง", "0833333333"),
    ("วิชัย", "มั่นคง", "0844444444"),
]


class Command(BaseCommand):
    help = "สร้างข้อมูลตัวอย่างสำหรับการพัฒนา (ห้ามใช้บน production)"

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--reset", action="store_true", help="ลบข้อมูลตัวอย่างเดิมก่อนสร้างใหม่"
        )
        parser.add_argument(
            "--force", action="store_true", help="ยืนยันการรันแม้ DEBUG=False"
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        self._ensure_utf8_console()

        if not settings.DEBUG and not options["force"]:
            raise CommandError(
                "ปฏิเสธการรันเพราะ DEBUG=False — ใส่ --force ถ้าต้องการรันจริง ๆ"
            )

        if options["reset"]:
            self._reset()

        clinics = self._create_clinics()
        services = self._create_services()
        self._create_super_admin()

        for clinic in clinics.values():
            self._create_branch_users(clinic)

        doctors = self._create_doctors(clinics)
        patients = self._create_patients(clinics)
        self._create_sample_appointments(clinics, doctors, services, patients)

        self.stdout.write(self.style.SUCCESS("สร้างข้อมูลตัวอย่างเรียบร้อย"))
        self.stdout.write(f"บัญชีทดสอบทั้งหมดใช้รหัสผ่าน: {DEFAULT_PASSWORD}")
        self.stdout.write("  super admin : root@clinic.test")
        self.stdout.write("  ผู้จัดการสาขา : admin.bkk@clinic.test / admin.cnx@clinic.test")
        self.stdout.write("  เจ้าหน้าที่   : staff.bkk@clinic.test / staff.cnx@clinic.test")
        self.stdout.write("  แพทย์        : doctor.ploy@clinic.test ฯลฯ")

    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_utf8_console() -> None:
        """
        คอนโซล Windows ใช้ code page cp1252 เป็นค่าเริ่มต้น ทำให้พิมพ์ภาษาไทยแล้ว error
        จึงสั่งให้ stdout ใช้ UTF-8 ก่อนเริ่มทำงาน (ไม่กระทบข้อมูลที่บันทึกลงฐานข้อมูล)
        """
        stream = getattr(sys, "stdout", None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    def _reset(self) -> None:
        self.stdout.write("กำลังลบข้อมูลตัวอย่างเดิม...")
        Appointment.objects.all().delete()
        TimeBlock.objects.all().delete()
        DoctorSchedule.objects.all().delete()
        Doctor.objects.all().delete()
        User.objects.filter(email__endswith="@clinic.test").delete()

    def _create_clinics(self) -> dict[str, Clinic]:
        clinics: dict[str, Clinic] = {}
        for payload in CLINIC_SEED:
            clinic, _ = Clinic.objects.get_or_create(code=payload["code"], defaults=payload)
            clinics[clinic.code] = clinic
        return clinics

    def _create_services(self) -> list[ServiceType]:
        services: list[ServiceType] = []
        for payload in SERVICE_SEED:
            data = {**payload, "price": Decimal(payload["price"])}
            name = data.pop("name")
            service, _ = ServiceType.objects.get_or_create(name=name, defaults=data)
            services.append(service)
        return services

    def _create_super_admin(self) -> User:
        existing = User.objects.filter(email="root@clinic.test").first()
        if existing:
            return existing
        return User.objects.create_superuser(
            email="root@clinic.test", password=DEFAULT_PASSWORD, full_name="ผู้ดูแลระบบ"
        )

    def _create_branch_users(self, clinic: Clinic) -> None:
        branch_key = clinic.code.lower()
        for role, email, full_name in [
            (UserRole.ADMIN, f"admin.{branch_key}@clinic.test", f"ผู้จัดการ {clinic.name}"),
            (UserRole.STAFF, f"staff.{branch_key}@clinic.test", f"เจ้าหน้าที่ {clinic.name}"),
        ]:
            if User.objects.filter(email=email).exists():
                continue
            User.objects.create_user(
                email=email,
                password=DEFAULT_PASSWORD,
                full_name=full_name,
                role=role,
                clinic=clinic,
            )

    def _create_doctors(self, clinics: dict[str, Clinic]) -> list[Doctor]:
        doctors: list[Doctor] = []

        for clinic_code, doctor_rows in DOCTOR_SEED.items():
            clinic = clinics[clinic_code]
            for email, display_name, color, working_days in doctor_rows:
                user = User.objects.filter(email=email).first() or User.objects.create_user(
                    email=email,
                    password=DEFAULT_PASSWORD,
                    full_name=display_name,
                    role=UserRole.DOCTOR,
                    clinic=clinic,
                )
                doctor, created = Doctor.objects.get_or_create(
                    user=user,
                    defaults={
                        "clinic": clinic,
                        "display_name": display_name,
                        "color": color,
                        "specialties": "ผิวหนังและความงาม",
                    },
                )
                if created:
                    self._create_doctor_schedule(doctor, working_days)
                doctors.append(doctor)

        return doctors

    def _create_doctor_schedule(self, doctor: Doctor, working_days: list[int]) -> None:
        """ตารางออกตรวจ: เช้า 09:00-12:00 และบ่าย 13:00-17:00 พร้อมพักเที่ยงแบบซ้ำทุกวัน"""
        for day_of_week in working_days:
            for start_time, end_time in [(time(9, 0), time(12, 0)), (time(13, 0), time(17, 0))]:
                DoctorSchedule.objects.get_or_create(
                    doctor=doctor,
                    clinic=doctor.clinic,
                    day_of_week=Weekday(day_of_week),
                    start_time=start_time,
                    defaults={"end_time": end_time},
                )

        zone = ZoneInfo(doctor.clinic.timezone)
        lunch_start = datetime.combine(date.today(), time(12, 0), tzinfo=zone)
        TimeBlock.objects.get_or_create(
            doctor=doctor,
            reason="lunch",
            defaults={
                "clinic": doctor.clinic,
                "start_datetime": lunch_start,
                "end_datetime": lunch_start + timedelta(hours=1),
                "is_recurring": True,
                "recurrence": "daily",
                "note": "พักเที่ยงประจำวัน",
            },
        )

    def _create_patients(self, clinics: dict[str, Clinic]) -> list:
        clinic = clinics["BKK"]
        registration = PatientRegistrationService(clinic=clinic)
        patients = []

        for first_name, last_name, phone in PATIENT_SEED:
            existing = registration.find_existing_by_phone(phone).first()
            patients.append(
                existing
                or registration.create_patient(
                    first_name=first_name, last_name=last_name, phone=phone
                )
            )
        return patients

    def _create_sample_appointments(
        self,
        clinics: dict[str, Clinic],
        doctors: list[Doctor],
        services: list[ServiceType],
        patients: list,
    ) -> None:
        """
        จองคิวตัวอย่างผ่าน service จริง เพื่อให้ข้อมูลที่ได้ผ่านกฎกันคิวชนเหมือนของจริง

        ไล่หา "วันที่แพทย์ออกตรวจจริง" ก่อนเสมอ เพราะแพทย์แต่ละคนลงตรวจคนละวัน
        ถ้ายึดวันพรุ่งนี้กับแพทย์คนแรกตายตัว พอ seed ตรงกับวันหยุดของแพทย์คนนั้น
        จะไม่ได้คิวตัวอย่างเลยและหน้าจอคิวจะว่างเปล่าโดยไม่มีสาเหตุที่ชัดเจน
        """
        clinic = clinics["BKK"]
        clinic_doctors = [doctor for doctor in doctors if doctor.clinic_id == clinic.pk]
        service = next(service for service in services if service.requires_doctor)
        if not clinic_doctors or not patients:
            return

        workday = self._find_workday_with_slots(clinic, service, clinic_doctors)
        if workday is None:
            self.stdout.write(
                f"ไม่พบวันที่แพทย์ออกตรวจในช่วง {SAMPLE_SEARCH_DAYS} วันข้างหน้า จึงข้ามการสร้างคิวตัวอย่าง"
            )
            return

        doctor, target_date, slots = workday
        booking = AppointmentBookingService(clinic=clinic)
        created = 0

        # เว้นทีละ 4 slot เพื่อให้คิวตัวอย่างกระจายทั้งวัน ไม่กองติดกันตอนเช้า
        for patient, slot in zip(patients, slots[::4]):
            if Appointment.objects.filter(patient=patient, scheduled_start=slot.start).exists():
                continue
            booking.book(
                patient=patient,
                service_type=service,
                doctor=doctor,
                scheduled_start=slot.start,
            )
            created += 1

        self.stdout.write(
            f"สร้างคิวตัวอย่างวันที่ {target_date} ของ {doctor.display_name} จำนวน {created} คิว"
        )

    @staticmethod
    def _find_workday_with_slots(
        clinic: Clinic, service: ServiceType, doctors: list[Doctor]
    ) -> tuple[Doctor, date, list] | None:
        """หาคู่ (แพทย์, วันที่) ที่มีเวลาว่างพอสร้างคิวตัวอย่างได้ — คืน None ถ้าไม่เจอ"""
        for day_offset in range(1, SAMPLE_SEARCH_DAYS + 1):
            target_date = date.today() + timedelta(days=day_offset)
            for doctor in doctors:
                slots = SlotAvailabilityService(clinic, service, doctor).available_slots(target_date)
                if slots:
                    return doctor, target_date, slots
        return None
