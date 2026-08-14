"""
เทสต์การจองคิว — เน้นกฎ "ห้าม overbook เด็ดขาด" และการกันคิวชน

ทุกเคสที่ควรถูกปฏิเสธต้อง raise SlotUnavailableError โดยไม่มีการบันทึกคิวลงฐานข้อมูล
"""
from __future__ import annotations

from datetime import time, timedelta

from django.test import TestCase

from apps.common.exceptions import (
    InvalidStatusTransitionError,
    SlotUnavailableError,
)
from apps.scheduling.models import Appointment, AppointmentSource, AppointmentStatus
from apps.scheduling.services import AppointmentBookingService
from apps.scheduling.tests.factories import (
    ClinicTestDataMixin,
    bangkok_datetime,
    next_monday,
)


class AppointmentBookingTests(ClinicTestDataMixin, TestCase):
    def setUp(self) -> None:
        self.clinic = self.create_clinic()
        self.doctor = self.create_doctor(clinic=self.clinic)
        self.service = self.create_service(duration_minutes=30)
        self.patient = self.create_patient(clinic=self.clinic)
        self.staff = self.create_user(clinic=self.clinic, email="staff@clinic.test")
        self.monday = next_monday()
        self.booking = AppointmentBookingService(clinic=self.clinic, performed_by=self.staff)

    def book_at(self, hour: int, minute: int = 0) -> Appointment:
        return self.booking.book(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            scheduled_start=bangkok_datetime(self.monday, hour, minute),
        )

    # ------------------------------------------------------------------
    def test_booking_computes_end_time_from_service_duration(self) -> None:
        appointment = self.book_at(10)

        self.assertEqual(appointment.scheduled_start, bangkok_datetime(self.monday, 10))
        self.assertEqual(appointment.scheduled_end, bangkok_datetime(self.monday, 10, 30))
        self.assertEqual(appointment.status, AppointmentStatus.BOOKED)
        self.assertEqual(appointment.source, AppointmentSource.STAFF_CREATED)
        self.assertEqual(appointment.created_by, self.staff)

    def test_exact_duplicate_time_is_rejected(self) -> None:
        self.book_at(10)

        with self.assertRaises(SlotUnavailableError):
            self.book_at(10)

        self.assertEqual(Appointment.objects.count(), 1)

    def test_partial_overlap_is_rejected(self) -> None:
        self.book_at(10)

        with self.assertRaises(SlotUnavailableError):
            self.book_at(10, 15)

        self.assertEqual(Appointment.objects.count(), 1)

    def test_back_to_back_booking_is_allowed(self) -> None:
        """คิวที่จบ 10:30 กับคิวที่เริ่ม 10:30 ไม่ถือว่าชนกัน"""
        self.book_at(10)
        appointment = self.book_at(10, 30)

        self.assertEqual(Appointment.objects.count(), 2)
        self.assertEqual(appointment.scheduled_start, bangkok_datetime(self.monday, 10, 30))

    def test_booking_outside_doctor_schedule_is_rejected(self) -> None:
        with self.assertRaises(SlotUnavailableError):
            self.book_at(18)  # แพทย์ออกตรวจถึง 17:00

    def test_booking_inside_time_block_is_rejected(self) -> None:
        self.create_time_block(
            doctor=self.doctor,
            start=bangkok_datetime(self.monday, 12),
            end=bangkok_datetime(self.monday, 13),
        )

        with self.assertRaises(SlotUnavailableError):
            self.book_at(12)

    def test_booking_that_would_run_past_closing_is_rejected(self) -> None:
        long_service = self.create_service(name="คอร์สใหญ่", duration_minutes=90)

        with self.assertRaises(SlotUnavailableError):
            self.booking.book(
                patient=self.patient,
                service_type=long_service,
                doctor=self.doctor,
                scheduled_start=bangkok_datetime(self.monday, 16),  # จบ 17:30 เกินตารางแพทย์
            )

    def test_cancelled_appointment_releases_the_slot_for_someone_else(self) -> None:
        appointment = self.book_at(10)
        self.booking.cancel(appointment, reason="คนไข้ติดธุระ")

        replacement = self.book_at(10)

        self.assertEqual(replacement.status, AppointmentStatus.BOOKED)
        self.assertEqual(Appointment.objects.occupying().count(), 1)

    def test_another_doctor_can_be_booked_at_the_same_time(self) -> None:
        """คิวชนกันเป็นเรื่องของแพทย์รายคน — แพทย์อีกท่านยังรับเวลาเดียวกันได้"""
        other_doctor = self.create_doctor(
            clinic=self.clinic, email="doctor2@clinic.test", display_name="นพ. สอง"
        )
        self.book_at(10)

        appointment = self.booking.book(
            patient=self.patient,
            service_type=self.service,
            doctor=other_doctor,
            scheduled_start=bangkok_datetime(self.monday, 10),
        )

        self.assertEqual(appointment.doctor, other_doctor)


class WalkInBookingTests(ClinicTestDataMixin, TestCase):
    """คิว walk-in ต้องอยู่ภายใต้กฎเดียวกับการจองล่วงหน้า — ห้ามยัดคิวเกิน"""

    def setUp(self) -> None:
        # เปิดทำการช่วงสั้น ๆ เพื่อให้เต็มคิวได้ในเทสต์
        self.clinic = self.create_clinic(opening_time=time(9, 0), closing_time=time(10, 0))
        self.doctor = self.create_doctor(
            clinic=self.clinic, weekly_hours=[(0, time(9, 0), time(10, 0))]
        )
        self.service = self.create_service(duration_minutes=30)
        self.patient = self.create_patient(clinic=self.clinic)
        self.monday = next_monday()
        self.booking = AppointmentBookingService(clinic=self.clinic)

    def test_walk_in_takes_the_earliest_free_slot(self) -> None:
        appointment = self.booking.book_walk_in(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            preferred_start=bangkok_datetime(self.monday, 9),
        )

        self.assertEqual(appointment.scheduled_start, bangkok_datetime(self.monday, 9))
        self.assertEqual(appointment.source, AppointmentSource.WALK_IN)

    def test_walk_in_moves_to_next_slot_when_earlier_one_is_taken(self) -> None:
        self.booking.book(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            scheduled_start=bangkok_datetime(self.monday, 9),
        )

        appointment = self.booking.book_walk_in(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            preferred_start=bangkok_datetime(self.monday, 9),
        )

        self.assertEqual(appointment.scheduled_start, bangkok_datetime(self.monday, 9, 30))

    def test_walk_in_is_rejected_when_the_day_is_full(self) -> None:
        """เคสสำคัญ: ไม่มี slot ว่างจริง → ต้องปฏิเสธ ไม่ใช่แทรกคิวเกิน capacity"""
        for hour, minute in [(9, 0), (9, 30)]:
            self.booking.book(
                patient=self.patient,
                service_type=self.service,
                doctor=self.doctor,
                scheduled_start=bangkok_datetime(self.monday, hour, minute),
            )

        with self.assertRaises(SlotUnavailableError):
            self.booking.book_walk_in(
                patient=self.patient,
                service_type=self.service,
                doctor=self.doctor,
                preferred_start=bangkok_datetime(self.monday, 9),
            )

        self.assertEqual(Appointment.objects.count(), 2)


class RescheduleAndStatusTests(ClinicTestDataMixin, TestCase):
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

    def test_reschedule_to_free_time_succeeds(self) -> None:
        self.booking.reschedule(
            self.appointment, new_start=bangkok_datetime(self.monday, 14)
        )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.scheduled_start, bangkok_datetime(self.monday, 14))
        self.assertEqual(self.appointment.scheduled_end, bangkok_datetime(self.monday, 14, 30))

    def test_reschedule_onto_another_appointment_is_rejected(self) -> None:
        self.booking.book(
            patient=self.patient,
            service_type=self.service,
            doctor=self.doctor,
            scheduled_start=bangkok_datetime(self.monday, 14),
        )

        with self.assertRaises(SlotUnavailableError):
            self.booking.reschedule(
                self.appointment, new_start=bangkok_datetime(self.monday, 14)
            )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.scheduled_start, bangkok_datetime(self.monday, 10))

    def test_reschedule_to_slightly_shifted_time_ignores_itself(self) -> None:
        """เลื่อนคิวไปทับช่วงเวลาเดิมของตัวเองได้ (ไม่ถือว่าชนกับตัวเอง)"""
        self.booking.reschedule(
            self.appointment, new_start=bangkok_datetime(self.monday, 10, 15)
        )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.scheduled_start, bangkok_datetime(self.monday, 10, 15))

    def test_reschedule_to_another_doctor(self) -> None:
        other_doctor = self.create_doctor(
            clinic=self.clinic, email="doctor2@clinic.test", display_name="นพ. สอง"
        )

        self.booking.reschedule(
            self.appointment,
            new_start=bangkok_datetime(self.monday, 10),
            new_doctor=other_doctor,
        )

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.doctor, other_doctor)

    def test_status_flow_records_timestamps(self) -> None:
        self.booking.change_status(self.appointment, AppointmentStatus.CHECKED_IN)
        self.assertIsNotNone(self.appointment.checked_in_at)

        self.booking.change_status(self.appointment, AppointmentStatus.IN_PROGRESS)
        self.assertIsNotNone(self.appointment.started_at)

        self.booking.change_status(self.appointment, AppointmentStatus.COMPLETED)
        self.assertIsNotNone(self.appointment.completed_at)
        self.assertIsNotNone(self.appointment.waiting_minutes)

    def test_invalid_status_jump_is_rejected(self) -> None:
        with self.assertRaises(InvalidStatusTransitionError):
            self.booking.change_status(self.appointment, AppointmentStatus.COMPLETED)

    def test_completed_appointment_cannot_be_rescheduled(self) -> None:
        for status_value in [
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_PROGRESS,
            AppointmentStatus.COMPLETED,
        ]:
            self.booking.change_status(self.appointment, status_value)

        with self.assertRaises(Exception):
            self.booking.reschedule(
                self.appointment, new_start=bangkok_datetime(self.monday, 15)
            )

    def test_cancelled_appointment_keeps_reason(self) -> None:
        self.booking.cancel(self.appointment, reason="ฝนตกหนัก มาไม่ได้")

        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.CANCELLED)
        self.assertEqual(self.appointment.cancelled_reason, "ฝนตกหนัก มาไม่ได้")
