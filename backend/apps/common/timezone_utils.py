"""
ตัวช่วยแปลงเวลาระหว่าง UTC (ที่เก็บใน DB) กับเวลาท้องถิ่นของสาขา

ทุก datetime ใน DB เป็น UTC เสมอ แต่ตารางแพทย์และเวลาเปิด-ปิดคลินิก
เป็น "เวลานาฬิกาท้องถิ่น" การคำนวณ slot จึงต้องประกอบวัน+เวลาในโซนของสาขาก่อน
แล้วค่อยแปลงกลับเป็น UTC ไม่เช่นนั้นวันที่คร่อมเที่ยงคืนจะคลาดเคลื่อน
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo


def get_zone(timezone_name: str) -> ZoneInfo:
    return ZoneInfo(timezone_name)


def combine_local(target_date: date, clock_time: time, timezone_name: str) -> datetime:
    """ประกอบวันที่ + เวลานาฬิกาท้องถิ่น ให้เป็น datetime พร้อม timezone ของสาขา"""
    return datetime.combine(target_date, clock_time, tzinfo=get_zone(timezone_name))


def local_day_bounds(target_date: date, timezone_name: str) -> tuple[datetime, datetime]:
    """
    ขอบเขต 00:00 ถึง 24:00 ของวันนั้นตามเวลาท้องถิ่น (คืนค่าเป็น aware datetime)

    ใช้กรอง Appointment ของ "วันนี้" ให้ตรงกับวันตามปฏิทินไทย ไม่ใช่ตาม UTC
    """
    zone = get_zone(timezone_name)
    start = datetime.combine(target_date, time.min, tzinfo=zone)
    end = datetime.combine(target_date + timedelta(days=1), time.min, tzinfo=zone)
    return start, end


def to_local(value: datetime, timezone_name: str) -> datetime:
    """แปลง datetime (aware) ไปเป็นเวลาท้องถิ่นของสาขา"""
    return value.astimezone(get_zone(timezone_name))


def local_date_of(value: datetime, timezone_name: str) -> date:
    """วันที่ตามปฏิทินท้องถิ่นของ datetime ที่ให้มา"""
    return to_local(value, timezone_name).date()
