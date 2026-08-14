"""
โครงสร้างข้อมูลสำหรับคำนวณช่วงเวลา (pure logic ไม่ผูกกับ Django/DB)

หัวใจของระบบคือการหา "ช่วงเวลาว่างจริง" ของแพทย์ ซึ่งคือ
    เวลาทำงานตามตาราง  −  ช่วงที่ถูกบล็อก  −  ช่วงที่มีคิวจองแล้ว

การแยก logic ส่วนนี้ออกมาเป็น class อิสระทำให้ทดสอบได้โดยไม่ต้องมีฐานข้อมูล
และนำไปใช้ซ้ำได้ทั้งตอนคำนวณ slot ว่างและตอน validate การจอง

หมายเหตุสำคัญ: ทุกช่วงเวลาถือเป็นแบบ half-open `[start, end)`
คิวที่จบเวลา 10:00 กับคิวที่เริ่ม 10:00 จึง "ไม่ชนกัน"
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True, order=True)
class TimeInterval:
    """ช่วงเวลาหนึ่งช่วง แบบ half-open [start, end)"""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ValueError("เวลาเริ่มต้องน้อยกว่าเวลาสิ้นสุดเสมอ")

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    @property
    def duration_minutes(self) -> int:
        return int(self.duration.total_seconds() // 60)

    def overlaps_with(self, other: "TimeInterval") -> bool:
        """ช่วงเวลาสองช่วงซ้อนทับกันหรือไม่ (ชนขอบพอดีไม่ถือว่าซ้อน)"""
        return self.start < other.end and other.start < self.end

    def contains(self, other: "TimeInterval") -> bool:
        """ช่วงเวลานี้ครอบคลุมอีกช่วงทั้งหมดหรือไม่"""
        return self.start <= other.start and other.end <= self.end

    def subtract(self, other: "TimeInterval") -> list["TimeInterval"]:
        """
        ตัดช่วง `other` ออกจากช่วงนี้

        ผลลัพธ์อาจเป็น 0 ช่วง (ถูกกินหมด), 1 ช่วง (ตัดหัวหรือท้าย)
        หรือ 2 ช่วง (ถูกเจาะตรงกลาง เช่น พักเที่ยงคั่นเวลาทำงาน)
        """
        if not self.overlaps_with(other):
            return [self]

        remaining: list[TimeInterval] = []
        if self.start < other.start:
            remaining.append(TimeInterval(self.start, other.start))
        if other.end < self.end:
            remaining.append(TimeInterval(other.end, self.end))
        return remaining

    def clamped_to(self, boundary: "TimeInterval") -> "TimeInterval | None":
        """ตัดช่วงนี้ให้อยู่ภายในขอบเขตที่กำหนด (คืน None ถ้าอยู่นอกขอบเขตทั้งหมด)"""
        start = max(self.start, boundary.start)
        end = min(self.end, boundary.end)
        if start >= end:
            return None
        return TimeInterval(start, end)


class IntervalSet:
    """
    กลุ่มของช่วงเวลาที่ไม่ซ้อนทับกัน เรียงจากเวลาน้อยไปมาก

    ใช้แทน "เวลาว่างของแพทย์ในหนึ่งวัน" ซึ่งอาจมีหลายช่วง
    (เช่น เช้า 09:00–12:00 และ บ่าย 13:00–17:00)
    """

    def __init__(self, intervals: list[TimeInterval] | None = None) -> None:
        self._intervals: list[TimeInterval] = self._merge(intervals or [])

    @staticmethod
    def _merge(intervals: list[TimeInterval]) -> list[TimeInterval]:
        """รวมช่วงที่ซ้อนทับหรือต่อกันพอดีให้เป็นช่วงเดียว"""
        if not intervals:
            return []

        merged: list[TimeInterval] = []
        for interval in sorted(intervals):
            if merged and interval.start <= merged[-1].end:
                previous = merged[-1]
                merged[-1] = TimeInterval(previous.start, max(previous.end, interval.end))
            else:
                merged.append(interval)
        return merged

    def subtract(self, intervals: list[TimeInterval]) -> "IntervalSet":
        """ตัดหลายช่วงออกจากกลุ่มนี้ คืนกลุ่มใหม่ (immutable style)"""
        remaining = list(self._intervals)
        for blocked in intervals:
            next_remaining: list[TimeInterval] = []
            for interval in remaining:
                next_remaining.extend(interval.subtract(blocked))
            remaining = next_remaining
        return IntervalSet(remaining)

    def clamped_to(self, boundary: TimeInterval) -> "IntervalSet":
        """จำกัดทุกช่วงให้อยู่ภายในขอบเขตที่กำหนด (เช่น เวลาเปิด-ปิดคลินิก)"""
        clamped = [
            clamped_interval
            for interval in self._intervals
            if (clamped_interval := interval.clamped_to(boundary)) is not None
        ]
        return IntervalSet(clamped)

    def contains_interval(self, candidate: TimeInterval) -> bool:
        """ช่วงเวลาที่ขอมานั้นอยู่ในเวลาว่างทั้งหมดหรือไม่"""
        return any(interval.contains(candidate) for interval in self._intervals)

    def total_minutes(self) -> int:
        return sum(interval.duration_minutes for interval in self._intervals)

    def to_list(self) -> list[TimeInterval]:
        return list(self._intervals)

    def __iter__(self):
        return iter(self._intervals)

    def __len__(self) -> int:
        return len(self._intervals)

    def __bool__(self) -> bool:
        return bool(self._intervals)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        parts = ", ".join(
            f"{interval.start.isoformat()}~{interval.end.isoformat()}"
            for interval in self._intervals
        )
        return f"IntervalSet([{parts}])"


def generate_slot_starts(
    free_time: IntervalSet,
    duration_minutes: int,
    step_minutes: int,
    not_before: datetime | None = None,
) -> list[TimeInterval]:
    """
    สร้างรายการ slot ที่จองได้จริงจากเวลาว่าง

    เดินทีละ `step_minutes` (ความละเอียดของตาราง เช่น ทุก 15 นาที) จากต้นแต่ละช่วงว่าง
    และรับเฉพาะ slot ที่ยาวครบ `duration_minutes` โดยไม่ล้นออกนอกช่วงว่างนั้น

    `not_before` ใช้กรณีจองของ "วันนี้" เพื่อไม่ให้เสนอเวลาที่ผ่านไปแล้ว
    """
    if duration_minutes <= 0 or step_minutes <= 0:
        raise ValueError("duration และ step ต้องเป็นจำนวนนาทีที่มากกว่า 0")

    duration = timedelta(minutes=duration_minutes)
    step = timedelta(minutes=step_minutes)

    slots: list[TimeInterval] = []
    for free_interval in free_time:
        slot_start = free_interval.start
        while slot_start + duration <= free_interval.end:
            if not_before is None or slot_start >= not_before:
                slots.append(TimeInterval(slot_start, slot_start + duration))
            slot_start += step
    return slots
