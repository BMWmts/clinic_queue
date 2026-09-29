"""
เทสต์ Isolation ของการแก้ไขคิวที่มีอยู่แล้ว (เปลี่ยนสถานะ / ยกเลิก / เลื่อนเวลา)

สถานการณ์จริง: พนักงานสองคนเปิดหน้าคิวเดียวกัน คนหนึ่งกด "ยกเลิก" อีกคนกด "เช็คอิน"
หรือ "เลื่อนเวลา" เกือบพร้อมกัน instance ที่ view ส่งเข้า service จึงอาจเก่ากว่าค่าใน DB

แบ่งเป็นสองชุด:
- StaleInstanceTests — จำลองด้วย instance เก่าใน memory (รันได้ทั้ง sqlite และ PostgreSQL)
- RowLockConcurrencyTests — สองเธรดแย่งแถวเดียวกันจริง ต้องใช้ row lock ของ PostgreSQL
"""
from __future__ import annotations

import threading
import unittest
from typing import Callable

from django.db import connection, transaction
from django.test import TestCase, TransactionTestCase

from apps.common.exceptions import BookingConflictError, InvalidStatusTransitionError
from apps.scheduling.models import Appointment, AppointmentStatus
from apps.scheduling.services import AppointmentBookingService
from apps.scheduling.tests.factories import (
    ClinicTestDataMixin,
    bangkok_datetime,
    next_monday,
)


class ExistingAppointmentMixin(ClinicTestDataMixin):
    """เตรียมคิว 10:00 วันจันทร์หน้า หนึ่งคิว สำหรับทุกเทสต์ในไฟล์นี้"""

    def setUp(self) -> None:
        self.clinic = self.create_clinic()
        self.doctor = self.create_doctor(clinic=self.clinic)
        self.service = self.create_service(duration_minutes=30)
        self.patient = self.create_patient(clinic=self.clinic)
        self.monday = next_monday()
        self.booking = AppointmentBookingService(clinic=self.clinic)
        self.appointment = self.booking.book(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            scheduled_start=bangkok_datetime(self.monday, 10),
        )

    def load_copy(self) -> Appointment:
        """instance แยกของคิวเดิม — แทนหน้าจอของพนักงานอีกคนที่โหลดไว้ก่อน"""
        return Appointment.objects.get(pk=self.appointment.pk)


class StaleInstanceTests(ExistingAppointmentMixin, TestCase):
    def test_status_change_is_validated_against_latest_committed_status(self) -> None:
        stale_copy = self.load_copy()
        self.booking.cancel(self.appointment, reason="ลูกค้าโทรมายกเลิก")

        # cancelled → checked_in ไม่อยู่ใน state machine ต้องถูกปฏิเสธ
        # แม้ instance เก่าจะยังคิดว่าสถานะเป็น booked อยู่
        with self.assertRaises(InvalidStatusTransitionError):
            self.booking.change_status(stale_copy, AppointmentStatus.CHECKED_IN)

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)
        self.assertIsNone(self.appointment.checked_in_at)

    def test_cancel_is_validated_against_latest_committed_status(self) -> None:
        stale_copy = self.load_copy()
        for status_value in [
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_PROGRESS,
            AppointmentStatus.COMPLETED,
        ]:
            self.booking.change_status(self.appointment, status_value)

        with self.assertRaises(InvalidStatusTransitionError):
            self.booking.cancel(stale_copy, reason="กดจากหน้าจอเก่า")

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.COMPLETED)
        self.assertEqual(self.appointment.cancelled_reason, "")

    def test_cancelled_appointment_cannot_be_rescheduled_through_stale_instance(self) -> None:
        stale_copy = self.load_copy()
        self.booking.cancel(self.appointment)

        with self.assertRaises(BookingConflictError):
            self.booking.reschedule(stale_copy, new_start=bangkok_datetime(self.monday, 14))

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.scheduled_start, bangkok_datetime(self.monday, 10))

    def test_status_change_updates_the_callers_instance(self) -> None:
        """view ใช้ instance เดิมสร้าง response ต่อ จึงต้องเห็นค่าที่เพิ่งบันทึก"""
        stale_copy = self.load_copy()
        self.booking.change_status(self.appointment, AppointmentStatus.CONFIRMED)

        self.booking.change_status(stale_copy, AppointmentStatus.CHECKED_IN)

        self.assertEqual(stale_copy.status, AppointmentStatus.CHECKED_IN)
        self.assertIsNotNone(stale_copy.checked_in_at)


@unittest.skipUnless(
    connection.vendor == "postgresql",
    "ต้องใช้ row lock (SELECT ... FOR UPDATE) ของ PostgreSQL — sqlite ไม่มีการล็อกระดับแถว",
)
class RowLockConcurrencyTests(ExistingAppointmentMixin, TransactionTestCase):
    """
    ลำดับเหตุการณ์ที่บังคับให้เกิดขึ้นในทุกเทสต์:

        เธรดหลัก (พนักงาน A)             เธรดรอง (พนักงาน B, instance เก่า)
        BEGIN + ล็อกแถวคิว
                                         เรียก service → ต้อง "รอ" ล็อก
        ยกเลิกคิว + COMMIT
                                         ได้ล็อก → เห็นสถานะ cancelled → ถูกปฏิเสธ
    """

    #: เวลาที่ถือว่า "เธรดรองติดล็อกอยู่จริง" ถ้ายังไม่จบภายในเวลานี้
    BLOCK_CHECK_SECONDS = 0.5
    #: เพดานเวลารอเธรดรองหลังปล่อยล็อก กันเทสต์ค้างถ้ามีบั๊ก
    FINISH_TIMEOUT_SECONDS = 10

    def run_while_row_is_locked_then_cancelled(
        self, competing_action: Callable[[Appointment], object]
    ) -> BaseException | None:
        """
        ล็อกแถวคิวในเธรดหลัก, ให้เธรดรองรัน `competing_action` กับ instance เก่า,
        แล้วยกเลิกคิวและ commit — คืน exception ที่เธรดรองได้รับ (หรือ None ถ้าสำเร็จ)
        """
        stale_copy = self.load_copy()
        outcome: dict[str, BaseException | None] = {"error": None}

        def competing_staff() -> None:
            try:
                competing_action(stale_copy)
            except BaseException as exc:  # ส่งผลกลับให้เธรดหลักตรวจ
                outcome["error"] = exc
            finally:
                connection.close()  # แต่ละเธรดมี connection ของตัวเอง

        worker = threading.Thread(target=competing_staff)
        with transaction.atomic():
            Appointment.objects.select_for_update().get(pk=self.appointment.pk)
            worker.start()
            worker.join(self.BLOCK_CHECK_SECONDS)
            self.assertTrue(worker.is_alive(), "เธรดรองควรรอล็อกของแถวคิว ไม่ใช่ทำงานผ่านไปเลย")

            Appointment.objects.filter(pk=self.appointment.pk).update(
                status=AppointmentStatus.CANCELLED
            )

        worker.join(self.FINISH_TIMEOUT_SECONDS)
        self.assertFalse(worker.is_alive(), "เธรดรองค้าง — ล็อกไม่ถูกปล่อยหลัง commit")
        return outcome["error"]

    def test_concurrent_check_in_waits_for_cancel_and_is_rejected(self) -> None:
        error = self.run_while_row_is_locked_then_cancelled(
            lambda stale: self.booking.change_status(stale, AppointmentStatus.CHECKED_IN)
        )

        self.assertIsInstance(error, InvalidStatusTransitionError)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)
        self.assertIsNone(self.appointment.checked_in_at)

    def test_concurrent_reschedule_waits_for_cancel_and_is_rejected(self) -> None:
        error = self.run_while_row_is_locked_then_cancelled(
            lambda stale: self.booking.reschedule(
                stale, new_start=bangkok_datetime(self.monday, 14)
            )
        )

        self.assertIsInstance(error, BookingConflictError)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)
        self.assertEqual(self.appointment.scheduled_start, bangkok_datetime(self.monday, 10))
