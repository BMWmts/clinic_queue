"""
เทสต์การคำนวณ slot ว่าง — หัวใจของระบบ

ครอบคลุมทั้งบริการที่ต้องมีแพทย์ (จำกัดด้วยตารางออกตรวจ) และบริการที่ไม่ต้องมีแพทย์
(จำกัดด้วยเพดานจำนวนเคสพร้อมกันของสาขา)
"""
from __future__ import annotations

from datetime import time, timedelta

from django.test import TestCase

from apps.scheduling.models import Appointment, AppointmentStatus
from apps.scheduling.services import SlotAvailabilityService
from apps.scheduling.tests.factories import (
    ClinicTestDataMixin,
    bangkok_datetime,
    next_monday,
)


class DoctorSlotAvailabilityTests(ClinicTestDataMixin, TestCase):
    """บริการที่ต้องมีแพทย์"""

    def setUp(self) -> None:
        self.clinic = self.create_clinic()
        self.doctor = self.create_doctor(clinic=self.clinic)
        self.service = self.create_service(duration_minutes=30)
        self.patient = self.create_patient(clinic=self.clinic)
        self.monday = next_monday()
        self.availability = SlotAvailabilityService(self.clinic, self.service, self.doctor)

    def book(self, hour: int, minute: int = 0, *, status: str = AppointmentStatus.BOOKED) -> Appointment:
        """สร้างคิวตรง ๆ ในฐานข้อมูล เพื่อจัดสถานการณ์ให้เทสต์ (ไม่ผ่าน service)"""
        start = bangkok_datetime(self.monday, hour, minute)
        return Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            service_type=self.service,
            clinic=self.clinic,
            scheduled_start=start,
            scheduled_end=start + timedelta(minutes=self.service.duration_minutes),
            status=status,
        )

    def test_slots_start_and_end_within_doctor_schedule(self) -> None:
        slots = self.availability.available_slots(self.monday)

        self.assertEqual(slots[0].start, bangkok_datetime(self.monday, 9))
        self.assertEqual(slots[-1].end, bangkok_datetime(self.monday, 17))

    def test_slots_are_spaced_by_clinic_slot_interval(self) -> None:
        slots = self.availability.available_slots(self.monday)

        gap = slots[1].start - slots[0].start
        self.assertEqual(gap, timedelta(minutes=self.clinic.slot_interval_minutes))

    def test_no_slots_on_day_without_schedule(self) -> None:
        """แพทย์ออกตรวจเฉพาะวันจันทร์ — วันอังคารต้องไม่มี slot"""
        tuesday = self.monday + timedelta(days=1)
        self.assertEqual(self.availability.available_slots(tuesday), [])

    def test_clinic_opening_hours_clamp_doctor_schedule(self) -> None:
        """ต่อให้แพทย์ตั้งตารางกว้างกว่าเวลาทำการ ระบบต้องไม่เสนอเวลานอกเวลาเปิด"""
        clinic = self.create_clinic(code="LATE", opening_time=time(10, 0), closing_time=time(12, 0))
        doctor = self.create_doctor(
            clinic=clinic,
            email="wide@clinic.test",
            weekly_hours=[(0, time(7, 0), time(22, 0))],
        )

        slots = SlotAvailabilityService(clinic, self.service, doctor).available_slots(self.monday)

        self.assertEqual(slots[0].start, bangkok_datetime(self.monday, 10))
        self.assertEqual(slots[-1].end, bangkok_datetime(self.monday, 12))

    def test_time_block_removes_overlapping_slots(self) -> None:
        self.create_time_block(
            doctor=self.doctor,
            start=bangkok_datetime(self.monday, 12),
            end=bangkok_datetime(self.monday, 13),
        )

        slots = self.availability.available_slots(self.monday)

        lunch_start = bangkok_datetime(self.monday, 12)
        lunch_end = bangkok_datetime(self.monday, 13)
        self.assertFalse(
            any(slot.start < lunch_end and slot.end > lunch_start for slot in slots),
            "ต้องไม่มี slot ใดคาบเกี่ยวกับช่วงพักเที่ยง",
        )

    def test_recurring_daily_time_block_applies_to_later_dates(self) -> None:
        """พักเที่ยงแบบซ้ำทุกวันต้องมีผลกับวันจันทร์ถัดไปด้วย"""
        self.create_doctor(
            clinic=self.clinic,
            email="second@clinic.test",
            weekly_hours=[(0, time(9, 0), time(17, 0))],
        )
        self.create_time_block(
            doctor=self.doctor,
            start=bangkok_datetime(self.monday, 12),
            end=bangkok_datetime(self.monday, 13),
            is_recurring=True,
            recurrence="daily",
        )

        next_week_monday = self.monday + timedelta(days=7)
        slots = self.availability.available_slots(next_week_monday)

        lunch_start = bangkok_datetime(next_week_monday, 12)
        self.assertFalse(any(slot.start == lunch_start for slot in slots))

    def test_booked_appointment_removes_its_slot(self) -> None:
        self.book(10)

        slots = self.availability.available_slots(self.monday)

        self.assertNotIn(bangkok_datetime(self.monday, 10), [slot.start for slot in slots])

    def test_cancelled_appointment_frees_the_slot(self) -> None:
        """คิวที่ถูกยกเลิกต้องคืนเวลาให้ตารางทันที"""
        appointment = self.book(10)
        appointment.status = AppointmentStatus.CANCELLED
        appointment.save(update_fields=["status"])

        slots = self.availability.available_slots(self.monday)

        self.assertIn(bangkok_datetime(self.monday, 10), [slot.start for slot in slots])

    def test_no_show_appointment_frees_the_slot(self) -> None:
        appointment = self.book(10)
        appointment.status = AppointmentStatus.NO_SHOW
        appointment.save(update_fields=["status"])

        slots = self.availability.available_slots(self.monday)

        self.assertIn(bangkok_datetime(self.monday, 10), [slot.start for slot in slots])

    def test_long_service_cannot_fit_at_the_end_of_the_day(self) -> None:
        long_service = self.create_service(name="ดริปผิวคอร์สใหญ่", duration_minutes=120)

        slots = SlotAvailabilityService(self.clinic, long_service, self.doctor).available_slots(
            self.monday
        )

        self.assertEqual(slots[-1].start, bangkok_datetime(self.monday, 15))
        self.assertEqual(slots[-1].end, bangkok_datetime(self.monday, 17))

    def test_past_date_has_no_slots(self) -> None:
        from datetime import date

        past_monday = self.monday - timedelta(days=28)
        if past_monday >= date.today():
            self.skipTest("ต้องเป็นวันในอดีตเท่านั้น")

        self.assertEqual(self.availability.available_slots(past_monday), [])

    def test_is_slot_available_matches_generated_slots(self) -> None:
        """slot ที่ระบบเสนอ ต้องผ่านการตรวจ is_slot_available ทุกตัว (ผลลัพธ์ต้องสอดคล้องกัน)"""
        self.book(10)

        slots = self.availability.available_slots(self.monday)

        self.assertTrue(all(self.availability.is_slot_available(slot) for slot in slots))

    def test_is_slot_available_rejects_time_outside_schedule(self) -> None:
        from apps.common.time_intervals import TimeInterval

        after_hours = TimeInterval(
            bangkok_datetime(self.monday, 18), bangkok_datetime(self.monday, 18, 30)
        )
        self.assertFalse(self.availability.is_slot_available(after_hours))

    def test_find_next_available_slot_skips_booked_time(self) -> None:
        self.book(9)

        slot = self.availability.find_next_available_slot(bangkok_datetime(self.monday, 9))

        self.assertIsNotNone(slot)
        self.assertEqual(slot.start, bangkok_datetime(self.monday, 9, 30))

    def test_inactive_doctor_has_no_slots(self) -> None:
        self.doctor.is_active = False
        self.doctor.save(update_fields=["is_active"])

        self.assertEqual(self.availability.available_slots(self.monday), [])


class CapacityBasedSlotAvailabilityTests(ClinicTestDataMixin, TestCase):
    """บริการที่ไม่ต้องมีแพทย์ — จำกัดด้วยเพดานจำนวนเคสพร้อมกันของสาขา"""

    def setUp(self) -> None:
        self.clinic = self.create_clinic(non_doctor_service_capacity=1)
        self.service = self.create_service(
            name="ดริปวิตามิน", duration_minutes=60, requires_doctor=False
        )
        self.patient = self.create_patient(clinic=self.clinic)
        self.monday = next_monday()
        self.availability = SlotAvailabilityService(self.clinic, self.service)

    def book_without_doctor(self, hour: int) -> Appointment:
        start = bangkok_datetime(self.monday, hour)
        return Appointment.objects.create(
            patient=self.patient,
            doctor=None,
            service_type=self.service,
            clinic=self.clinic,
            scheduled_start=start,
            scheduled_end=start + timedelta(minutes=self.service.duration_minutes),
        )

    def test_slots_span_clinic_opening_hours(self) -> None:
        slots = self.availability.available_slots(self.monday)

        self.assertEqual(slots[0].start, bangkok_datetime(self.monday, 9))
        self.assertEqual(slots[-1].end, bangkok_datetime(self.monday, 18))

    def test_full_capacity_removes_overlapping_slots(self) -> None:
        self.book_without_doctor(10)

        slots = self.availability.available_slots(self.monday)

        self.assertFalse(
            any(
                slot.start < bangkok_datetime(self.monday, 11)
                and slot.end > bangkok_datetime(self.monday, 10)
                for slot in slots
            )
        )

    def test_higher_capacity_still_allows_overlapping_slot(self) -> None:
        self.clinic.non_doctor_service_capacity = 2
        self.clinic.save(update_fields=["non_doctor_service_capacity"])
        self.book_without_doctor(10)

        slots = self.availability.available_slots(self.monday)

        self.assertIn(bangkok_datetime(self.monday, 10), [slot.start for slot in slots])
