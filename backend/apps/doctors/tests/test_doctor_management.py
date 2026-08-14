"""
เทสต์การจัดการแพทย์ผ่าน API — รับแพทย์ใหม่ ตั้งตารางออกตรวจ และบล็อกวันลา

จุดที่ต้องคุมเป็นพิเศษ: การสร้างแพทย์แตะสองตาราง (User + Doctor) ถ้าพลาดกลางทาง
ต้องไม่เหลือบัญชีค้างที่ล็อกอินได้แต่ไม่มีโปรไฟล์แพทย์
"""
from __future__ import annotations

from datetime import time

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.accounts.models import User
from apps.common.roles import UserRole
from apps.doctors.models import Doctor, DoctorSchedule
from apps.scheduling.services import SlotAvailabilityService
from apps.scheduling.tests.factories import (
    ClinicTestDataMixin,
    bangkok_datetime,
    next_monday,
)


class DoctorCreationApiTests(ClinicTestDataMixin, APITestCase):
    def setUp(self) -> None:
        self.clinic = self.create_clinic()
        self.manager = self.create_user(
            clinic=self.clinic, email="admin@clinic.test", role=UserRole.ADMIN
        )
        self.client.force_authenticate(self.manager)

    def new_doctor_payload(self, **overrides) -> dict:
        payload = {
            "email": "newdoctor@clinic.test",
            "full_name": "พญ. ใหม่ ใจดี",
            "password": "DoctorPass!2026",
            "display_name": "พญ. ใหม่",
            "specialties": "ผิวหนัง",
            "color": "#16a34a",
        }
        payload.update(overrides)
        return payload

    def test_creating_doctor_also_creates_login_account(self) -> None:
        response = self.client.post(reverse("doctor-list"), self.new_doctor_payload())

        self.assertEqual(response.status_code, 201)
        doctor = Doctor.objects.get(pk=response.data["id"])
        self.assertEqual(doctor.clinic, self.clinic)
        self.assertEqual(doctor.user.role, UserRole.DOCTOR)
        self.assertEqual(doctor.user.clinic, self.clinic)

    def test_created_doctor_can_log_in(self) -> None:
        """รหัสผ่านต้องถูก hash อย่างถูกต้อง ไม่ใช่เก็บเป็นข้อความธรรมดา"""
        self.client.post(reverse("doctor-list"), self.new_doctor_payload())
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("auth-login"),
            {"email": "newdoctor@clinic.test", "password": "DoctorPass!2026"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["user"]["role"], UserRole.DOCTOR)

    def test_duplicate_email_is_rejected(self) -> None:
        self.client.post(reverse("doctor-list"), self.new_doctor_payload())

        response = self.client.post(reverse("doctor-list"), self.new_doctor_payload())

        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.data)
        self.assertEqual(Doctor.objects.count(), 1)

    def test_weak_password_is_rejected_without_creating_account(self) -> None:
        response = self.client.post(
            reverse("doctor-list"), self.new_doctor_payload(password="12345678")
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email="newdoctor@clinic.test").exists())

    def test_staff_cannot_create_doctor(self) -> None:
        staff = self.create_user(clinic=self.clinic, email="staff@clinic.test")
        self.client.force_authenticate(staff)

        response = self.client.post(reverse("doctor-list"), self.new_doctor_payload())

        self.assertEqual(response.status_code, 403)

    def test_new_doctor_has_no_bookable_slot_until_schedule_is_added(self) -> None:
        """
        แพทย์ที่เพิ่งรับเข้ามายังจองคิวไม่ได้จนกว่าจะมีตารางออกตรวจ

        เป็นพฤติกรรมที่ตั้งใจ (ไม่ใช่บั๊ก) — หน้าจอจึงต้องเตือนให้ตั้งตารางต่อทันที
        """
        response = self.client.post(reverse("doctor-list"), self.new_doctor_payload())
        doctor = Doctor.objects.get(pk=response.data["id"])
        service = self.create_service(duration_minutes=30)

        availability = SlotAvailabilityService(self.clinic, service, doctor)
        self.assertEqual(availability.available_slots(next_monday()), [])

        DoctorSchedule.objects.create(
            doctor=doctor,
            clinic=self.clinic,
            day_of_week=0,
            start_time=time(9, 0),
            end_time=time(12, 0),
        )
        self.assertGreater(len(availability.available_slots(next_monday())), 0)


class DoctorScheduleApiTests(ClinicTestDataMixin, APITestCase):
    """ตารางออกตรวจและวันลา — จัดการผ่าน API ที่หน้าจอ "จัดการแพทย์" เรียกใช้"""

    def setUp(self) -> None:
        self.clinic = self.create_clinic()
        self.doctor = self.create_doctor(clinic=self.clinic, weekly_hours=[])
        self.manager = self.create_user(
            clinic=self.clinic, email="admin@clinic.test", role=UserRole.ADMIN
        )
        self.client.force_authenticate(self.manager)

    def test_adding_schedule_row(self) -> None:
        response = self.client.post(
            reverse("doctor-schedule-list"),
            {
                "doctor": self.doctor.pk,
                "day_of_week": 0,
                "start_time": "09:00",
                "end_time": "12:00",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["clinic"], self.clinic.pk)

    def test_overlapping_schedule_rows_are_rejected(self) -> None:
        payload = {
            "doctor": self.doctor.pk,
            "day_of_week": 0,
            "start_time": "09:00",
            "end_time": "12:00",
        }
        self.client.post(reverse("doctor-schedule-list"), payload)

        response = self.client.post(
            reverse("doctor-schedule-list"), {**payload, "start_time": "11:00", "end_time": "14:00"}
        )

        self.assertEqual(response.status_code, 400)

    def test_end_time_before_start_time_is_rejected(self) -> None:
        response = self.client.post(
            reverse("doctor-schedule-list"),
            {
                "doctor": self.doctor.pk,
                "day_of_week": 0,
                "start_time": "15:00",
                "end_time": "09:00",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_adding_time_off_block(self) -> None:
        monday = next_monday()

        response = self.client.post(
            reverse("time-block-list"),
            {
                "doctor": self.doctor.pk,
                "start_datetime": bangkok_datetime(monday, 9).isoformat(),
                "end_datetime": bangkok_datetime(monday, 17).isoformat(),
                "reason": "leave",
                "note": "ลาพักร้อน",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["reason_display"], "ลา")
