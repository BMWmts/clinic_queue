"""
เทสต์ระดับ API ของหน้าจอคิว

เน้นสองเรื่อง: หน้าคิววันนี้แสดงข้อมูลครบ และ walk-in ต้องถูกปฏิเสธเมื่อคิวเต็มจริง
"""
from __future__ import annotations

from datetime import time, timedelta

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.roles import UserRole
from apps.scheduling.models import Appointment, AppointmentStatus
from apps.scheduling.services import AppointmentBookingService
from apps.scheduling.tests.factories import (
    ClinicTestDataMixin,
    bangkok_datetime,
    next_monday,
)


class QueueApiTests(ClinicTestDataMixin, APITestCase):
    def setUp(self) -> None:
        self.clinic = self.create_clinic()
        self.doctor = self.create_doctor(clinic=self.clinic)
        self.service = self.create_service(duration_minutes=30)
        self.patient = self.create_patient(clinic=self.clinic)
        self.staff = self.create_user(clinic=self.clinic, email="staff@clinic.test")
        self.monday = next_monday()

        booking = AppointmentBookingService(clinic=self.clinic, performed_by=self.staff)
        self.appointment = booking.book(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            scheduled_start=bangkok_datetime(self.monday, 10),
        )
        self.client.force_authenticate(self.staff)

    def test_today_endpoint_returns_queue_with_summary(self) -> None:
        response = self.client.get(reverse("queue-today"), {"date": self.monday.isoformat()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["total"], 1)
        self.assertEqual(response.data["summary"]["booked"], 1)
        self.assertEqual(len(response.data["appointments"]), 1)
        self.assertEqual(
            response.data["appointments"][0]["patient_code"], self.patient.patient_code
        )

    def test_status_update_follows_state_machine(self) -> None:
        url = reverse("queue-appointment-status", args=[self.appointment.pk])

        response = self.client.patch(url, {"status": AppointmentStatus.CHECKED_IN})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], AppointmentStatus.CHECKED_IN)
        self.assertIsNotNone(response.data["checked_in_at"])

    def test_invalid_status_jump_returns_conflict(self) -> None:
        url = reverse("queue-appointment-status", args=[self.appointment.pk])

        response = self.client.patch(url, {"status": AppointmentStatus.COMPLETED})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "invalid_status_transition")

    def test_reschedule_to_taken_time_returns_conflict(self) -> None:
        booking = AppointmentBookingService(clinic=self.clinic, performed_by=self.staff)
        booking.book(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            scheduled_start=bangkok_datetime(self.monday, 14),
        )
        url = reverse("queue-appointment-reschedule", args=[self.appointment.pk])

        response = self.client.patch(
            url, {"scheduled_start": bangkok_datetime(self.monday, 14).isoformat()}
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "slot_unavailable")

    def test_doctor_cannot_update_another_doctors_appointment(self) -> None:
        other_doctor = self.create_doctor(
            clinic=self.clinic, email="doctor2@clinic.test", display_name="นพ. สอง"
        )
        self.client.force_authenticate(other_doctor.user)

        response = self.client.patch(
            reverse("queue-appointment-status", args=[self.appointment.pk]),
            {"status": AppointmentStatus.CHECKED_IN},
        )

        self.assertEqual(response.status_code, 403)

    def test_doctor_can_update_own_appointment(self) -> None:
        self.client.force_authenticate(self.doctor.user)

        response = self.client.patch(
            reverse("queue-appointment-status", args=[self.appointment.pk]),
            {"status": AppointmentStatus.CHECKED_IN},
        )

        self.assertEqual(response.status_code, 200)


class WalkInApiTests(ClinicTestDataMixin, APITestCase):
    """walk-in ผ่าน API ต้องยึดกฎห้าม overbook เหมือนกับชั้น service"""

    def setUp(self) -> None:
        # เปิดทำการ 1 ชั่วโมง + บริการ 30 นาที = รับได้สูงสุด 2 คิว
        self.clinic = self.create_clinic(opening_time=time(9, 0), closing_time=time(10, 0))
        self.doctor = self.create_doctor(
            clinic=self.clinic, weekly_hours=[(0, time(9, 0), time(10, 0))]
        )
        self.service = self.create_service(duration_minutes=30)
        self.staff = self.create_user(
            clinic=self.clinic, email="staff@clinic.test", role=UserRole.STAFF
        )
        self.monday = next_monday()
        self.client.force_authenticate(self.staff)

    def walk_in_payload(self, **overrides) -> dict:
        payload = {
            "new_patient": {"first_name": "สมชาย", "last_name": "ทดสอบ", "phone": "0801112222"},
            "service_type": self.service.pk,
            "doctor": self.doctor.pk,
            "preferred_start": bangkok_datetime(self.monday, 9).isoformat(),
        }
        payload.update(overrides)
        return payload

    def test_walk_in_registers_new_patient_and_creates_appointment(self) -> None:
        response = self.client.post(
            reverse("queue-walk-in"), self.walk_in_payload(), format="json"
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["source"], "walk_in")
        self.assertTrue(response.data["patient_code"].startswith(f"{self.clinic.code}-"))

    def test_walk_in_reuses_existing_patient_with_same_phone(self) -> None:
        self.client.post(reverse("queue-walk-in"), self.walk_in_payload(), format="json")

        second = self.client.post(
            reverse("queue-walk-in"), self.walk_in_payload(), format="json"
        )

        self.assertEqual(second.status_code, 201)
        from apps.patients.models import Patient

        self.assertEqual(Patient.objects.filter(phone="0801112222").count(), 1)

    def test_walk_in_is_rejected_when_no_slot_is_left(self) -> None:
        for _ in range(2):
            self.client.post(reverse("queue-walk-in"), self.walk_in_payload(), format="json")

        response = self.client.post(
            reverse("queue-walk-in"), self.walk_in_payload(), format="json"
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["error"]["code"], "slot_unavailable")
        self.assertEqual(Appointment.objects.count(), 2)

    def test_walk_in_requires_doctor_for_doctor_service(self) -> None:
        response = self.client.post(
            reverse("queue-walk-in"), self.walk_in_payload(doctor=None), format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("doctor", response.data)
