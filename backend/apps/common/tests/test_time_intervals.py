"""
Unit test ของ logic ช่วงเวลา — เป็นฐานของการคำนวณ slot ว่างทั้งระบบ
ทดสอบแบบ pure logic ไม่แตะฐานข้อมูล
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from apps.common.time_intervals import (
    IntervalSet,
    TimeInterval,
    generate_slot_starts,
)

BANGKOK = ZoneInfo("Asia/Bangkok")


def at(hour: int, minute: int = 0) -> datetime:
    """ตัวช่วยอ่านง่าย: เวลาในวันที่ 1 ม.ค. 2026 ตามเวลาไทย"""
    return datetime(2026, 1, 1, hour, minute, tzinfo=BANGKOK)


class TimeIntervalTests(SimpleTestCase):
    def test_start_must_be_before_end(self) -> None:
        with self.assertRaises(ValueError):
            TimeInterval(at(10), at(10))

    def test_touching_intervals_do_not_overlap(self) -> None:
        first = TimeInterval(at(9), at(10))
        second = TimeInterval(at(10), at(11))
        self.assertFalse(first.overlaps_with(second))
        self.assertFalse(second.overlaps_with(first))

    def test_partial_overlap_detected_from_both_sides(self) -> None:
        first = TimeInterval(at(9), at(10))
        second = TimeInterval(at(9, 30), at(10, 30))
        self.assertTrue(first.overlaps_with(second))
        self.assertTrue(second.overlaps_with(first))

    def test_subtract_middle_splits_into_two(self) -> None:
        working_hours = TimeInterval(at(9), at(17))
        lunch_break = TimeInterval(at(12), at(13))

        remaining = working_hours.subtract(lunch_break)

        self.assertEqual(
            remaining,
            [TimeInterval(at(9), at(12)), TimeInterval(at(13), at(17))],
        )

    def test_subtract_covering_interval_returns_nothing(self) -> None:
        self.assertEqual(TimeInterval(at(9), at(10)).subtract(TimeInterval(at(8), at(11))), [])

    def test_subtract_non_overlapping_keeps_original(self) -> None:
        working_hours = TimeInterval(at(9), at(12))
        self.assertEqual(
            working_hours.subtract(TimeInterval(at(13), at(14))), [working_hours]
        )


class IntervalSetTests(SimpleTestCase):
    def test_overlapping_intervals_are_merged(self) -> None:
        interval_set = IntervalSet(
            [TimeInterval(at(9), at(11)), TimeInterval(at(10), at(12))]
        )
        self.assertEqual(interval_set.to_list(), [TimeInterval(at(9), at(12))])

    def test_adjacent_intervals_are_merged(self) -> None:
        interval_set = IntervalSet(
            [TimeInterval(at(9), at(10)), TimeInterval(at(10), at(11))]
        )
        self.assertEqual(interval_set.to_list(), [TimeInterval(at(9), at(11))])

    def test_subtract_booked_appointments(self) -> None:
        working_hours = IntervalSet([TimeInterval(at(9), at(12))])

        free_time = working_hours.subtract(
            [TimeInterval(at(9, 30), at(10)), TimeInterval(at(11), at(11, 30))]
        )

        self.assertEqual(
            free_time.to_list(),
            [
                TimeInterval(at(9), at(9, 30)),
                TimeInterval(at(10), at(11)),
                TimeInterval(at(11, 30), at(12)),
            ],
        )

    def test_clamped_to_clinic_opening_hours(self) -> None:
        doctor_hours = IntervalSet([TimeInterval(at(7), at(21))])

        clamped = doctor_hours.clamped_to(TimeInterval(at(9), at(18)))

        self.assertEqual(clamped.to_list(), [TimeInterval(at(9), at(18))])

    def test_contains_interval(self) -> None:
        free_time = IntervalSet([TimeInterval(at(9), at(12))])
        self.assertTrue(free_time.contains_interval(TimeInterval(at(10), at(11))))
        self.assertFalse(free_time.contains_interval(TimeInterval(at(11, 30), at(12, 30))))


class GenerateSlotStartsTests(SimpleTestCase):
    def test_slots_respect_duration_and_step(self) -> None:
        free_time = IntervalSet([TimeInterval(at(9), at(10))])

        slots = generate_slot_starts(free_time, duration_minutes=30, step_minutes=15)

        self.assertEqual(
            slots,
            [
                TimeInterval(at(9), at(9, 30)),
                TimeInterval(at(9, 15), at(9, 45)),
                TimeInterval(at(9, 30), at(10)),
            ],
        )

    def test_slot_never_overflows_free_interval(self) -> None:
        free_time = IntervalSet([TimeInterval(at(9), at(9, 40))])

        slots = generate_slot_starts(free_time, duration_minutes=30, step_minutes=15)

        self.assertEqual(slots, [TimeInterval(at(9), at(9, 30))])
        self.assertTrue(all(slot.end <= at(9, 40) for slot in slots))

    def test_not_before_filters_past_slots(self) -> None:
        free_time = IntervalSet([TimeInterval(at(9), at(11))])

        slots = generate_slot_starts(
            free_time, duration_minutes=60, step_minutes=60, not_before=at(10)
        )

        self.assertEqual(slots, [TimeInterval(at(10), at(11))])

    def test_service_longer_than_free_time_returns_no_slot(self) -> None:
        free_time = IntervalSet([TimeInterval(at(9), at(9, 30))])
        self.assertEqual(
            generate_slot_starts(free_time, duration_minutes=45, step_minutes=15), []
        )

    def test_zero_duration_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generate_slot_starts(IntervalSet([]), duration_minutes=0, step_minutes=15)

    def test_slots_across_lunch_break_are_split(self) -> None:
        working_hours = IntervalSet([TimeInterval(at(9), at(14))])
        free_time = working_hours.subtract([TimeInterval(at(12), at(13))])

        slots = generate_slot_starts(free_time, duration_minutes=60, step_minutes=60)

        self.assertEqual(
            slots,
            [
                TimeInterval(at(9), at(10)),
                TimeInterval(at(10), at(11)),
                TimeInterval(at(11), at(12)),
                TimeInterval(at(13), at(14)),
            ],
        )
        self.assertTrue(
            all(not slot.overlaps_with(TimeInterval(at(12), at(13))) for slot in slots)
        )

    def test_utc_and_local_time_describe_the_same_slot(self) -> None:
        """เวลาเดียวกันคนละ timezone ต้องถือเป็นช่วงเดียวกัน (DB เก็บ UTC)"""
        local_interval = TimeInterval(at(9), at(10))
        utc_interval = TimeInterval(
            at(9).astimezone(ZoneInfo("UTC")), at(9).astimezone(ZoneInfo("UTC")) + timedelta(hours=1)
        )
        self.assertTrue(local_interval.overlaps_with(utc_interval))
        self.assertTrue(local_interval.contains(utc_interval))
