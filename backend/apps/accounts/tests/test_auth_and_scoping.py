"""
เทสต์ระดับ API: การเข้าสู่ระบบ และการจำกัดข้อมูลตามสาขา (branch scoping)

การรั่วของข้อมูลข้ามสาขาถือเป็นบั๊กร้ายแรงของระบบนี้ จึงต้องมีเทสต์คุมไว้
"""
from __future__ import annotations

from datetime import timedelta

from django.urls import reverse
from rest_framework.test import APITestCase

from apps.common.roles import UserRole
from apps.scheduling.models import Appointment
from apps.scheduling.tests.factories import (
    ClinicTestDataMixin,
    bangkok_datetime,
    next_monday,
)

PASSWORD = "TestPass!2026"


class AuthenticationApiTests(ClinicTestDataMixin, APITestCase):
    def setUp(self) -> None:
        self.clinic = self.create_clinic()
        self.user = self.create_user(clinic=self.clinic, email="staff@clinic.test")

    def test_login_returns_tokens_and_user_profile(self) -> None:
        response = self.client.post(
            reverse("auth-login"), {"email": "staff@clinic.test", "password": PASSWORD}
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "staff@clinic.test")
        self.assertEqual(response.data["user"]["clinic"], self.clinic.pk)

    def test_login_never_returns_password_field(self) -> None:
        response = self.client.post(
            reverse("auth-login"), {"email": "staff@clinic.test", "password": PASSWORD}
        )

        self.assertNotIn("password", response.data["user"])

    def test_wrong_password_is_rejected_with_generic_message(self) -> None:
        response = self.client.post(
            reverse("auth-login"), {"email": "staff@clinic.test", "password": "wrong-password"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("staff@clinic.test", str(response.data))

    def test_inactive_user_cannot_login(self) -> None:
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("auth-login"), {"email": "staff@clinic.test", "password": PASSWORD}
        )

        self.assertEqual(response.status_code, 400)

    def test_me_requires_authentication(self) -> None:
        self.assertEqual(self.client.get(reverse("auth-me")).status_code, 401)

    def test_me_returns_current_user(self) -> None:
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("auth-me"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["role"], UserRole.STAFF)


class BranchScopingApiTests(ClinicTestDataMixin, APITestCase):
    """ข้อมูลของสาขาหนึ่งต้องไม่รั่วไปยังผู้ใช้ของอีกสาขา"""

    def setUp(self) -> None:
        self.monday = next_monday()

        self.bangkok_clinic = self.create_clinic(code="BKK", name="สาขากรุงเทพ")
        self.chiangmai_clinic = self.create_clinic(code="CNX", name="สาขาเชียงใหม่")

        self.service = self.create_service(duration_minutes=30)
        self.bangkok_staff = self.create_user(
            clinic=self.bangkok_clinic, email="bkk-staff@clinic.test"
        )
        self.super_admin = self.create_user(
            clinic=None, email="root@clinic.test", role=UserRole.SUPER_ADMIN
        )

        self.bangkok_appointment = self._create_appointment(
            self.bangkok_clinic, prefix="bkk", phone="0812345678"
        )
        self.chiangmai_appointment = self._create_appointment(
            self.chiangmai_clinic, prefix="cnx", phone="0898765432"
        )

    def _create_appointment(self, clinic, *, prefix: str, phone: str) -> Appointment:
        doctor = self.create_doctor(clinic=clinic, email=f"{prefix}-doctor@clinic.test")
        patient = self.create_patient(
            clinic=clinic, phone=phone, patient_code=f"{clinic.code}-000001"
        )
        start = bangkok_datetime(self.monday, 10)
        return Appointment.objects.create(
            patient=patient,
            doctor=doctor,
            service_type=self.service,
            clinic=clinic,
            scheduled_start=start,
            scheduled_end=start + timedelta(minutes=30),
        )

    def test_staff_sees_only_their_own_branch_appointments(self) -> None:
        self.client.force_authenticate(self.bangkok_staff)

        response = self.client.get(reverse("appointment-list"))

        returned_ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(returned_ids, {self.bangkok_appointment.pk})

    def test_staff_cannot_read_other_branch_appointment_directly(self) -> None:
        self.client.force_authenticate(self.bangkok_staff)

        response = self.client.get(
            reverse("appointment-detail", args=[self.chiangmai_appointment.pk])
        )

        self.assertEqual(response.status_code, 404)

    def test_super_admin_sees_every_branch(self) -> None:
        self.client.force_authenticate(self.super_admin)

        response = self.client.get(reverse("appointment-list"))

        returned_ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(
            returned_ids, {self.bangkok_appointment.pk, self.chiangmai_appointment.pk}
        )

    def test_super_admin_can_filter_to_a_single_branch(self) -> None:
        self.client.force_authenticate(self.super_admin)

        response = self.client.get(
            reverse("appointment-list"), {"clinic_id": self.chiangmai_clinic.pk}
        )

        returned_ids = {row["id"] for row in response.data["results"]}
        self.assertEqual(returned_ids, {self.chiangmai_appointment.pk})

    def test_clinic_list_is_scoped_for_staff(self) -> None:
        self.client.force_authenticate(self.bangkok_staff)

        response = self.client.get(reverse("clinic-list"))

        returned_codes = {row["code"] for row in response.data["results"]}
        self.assertEqual(returned_codes, {"BKK"})

    def test_staff_cannot_create_clinic(self) -> None:
        self.client.force_authenticate(self.bangkok_staff)

        response = self.client.post(
            reverse("clinic-list"),
            {
                "name": "สาขาใหม่",
                "code": "NEW",
                "opening_time": "09:00",
                "closing_time": "18:00",
            },
        )

        self.assertEqual(response.status_code, 403)


class SuperAdminBranchSelectionTests(ClinicTestDataMixin, APITestCase):
    """
    Super Admin ไม่ได้สังกัดสาขา จึงต้องเลือกสาขาที่จะทำงานด้วยทุกครั้ง

    endpoint ที่ "สร้าง/อ่านข้อมูลของสาขาใดสาขาหนึ่ง" ต้องรับ clinic_id ได้
    และต้องบอกให้ชัดเมื่อไม่ได้ระบุมา (ไม่ใช่เงียบ ๆ ไปหยิบสาขาแรกมาใช้)
    """

    def setUp(self) -> None:
        self.bangkok_clinic = self.create_clinic(code="BKK", name="สาขากรุงเทพ")
        self.chiangmai_clinic = self.create_clinic(code="CNX", name="สาขาเชียงใหม่")
        self.super_admin = self.create_user(
            clinic=None, email="root@clinic.test", role=UserRole.SUPER_ADMIN
        )
        self.client.force_authenticate(self.super_admin)

    def test_queue_requires_clinic_id(self) -> None:
        response = self.client.get(reverse("queue-today"))

        self.assertEqual(response.status_code, 400)
        self.assertIn("clinic_id", response.data)

    def test_queue_returns_selected_branch(self) -> None:
        response = self.client.get(reverse("queue-today"), {"clinic_id": self.chiangmai_clinic.pk})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["clinic_id"], self.chiangmai_clinic.pk)

    def test_creating_patient_requires_clinic_id(self) -> None:
        response = self.client.post(
            reverse("patient-list"),
            {"first_name": "สมหญิง", "last_name": "ใจดี", "phone": "0812345678"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("clinic_id", response.data)

    def test_creating_patient_uses_the_selected_branch(self) -> None:
        """คนไข้ที่ Super Admin ลงทะเบียน ต้องสังกัดสาขาที่เลือก ไม่ใช่สาขาแรกในระบบ"""
        response = self.client.post(
            reverse("patient-list"),
            {
                "first_name": "สมหญิง",
                "last_name": "ใจดี",
                "phone": "0812345678",
                "clinic_id": self.chiangmai_clinic.pk,
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["home_clinic"], self.chiangmai_clinic.pk)
        self.assertTrue(response.data["patient_code"].startswith("CNX-"))
