"""
รายงานเชิงบริหาร — คำนวณด้วย ORM aggregation ทั้งหมด (ไม่มี raw SQL)

ทุกตัวเลขคำนวณจากตาราง Appointment โดยตรง จึงไม่มีข้อมูลสรุปที่ค้างเก่า
และไม่ต้องมี model แยกสำหรับรายงาน
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.db.models import Avg, Count, DurationField, F, Q, QuerySet, Sum
from django.db.models.functions import (
    ExtractHour,
    ExtractIsoWeekDay,
    TruncDate,
    TruncMonth,
)

from apps.clinics.models import Clinic
from apps.common.timezone_utils import local_day_bounds
from apps.scheduling.models import Appointment, AppointmentStatus


@dataclass(frozen=True)
class ReportPeriod:
    """ช่วงเวลาที่ต้องการดูรายงาน (รวมวันเริ่มและวันสิ้นสุด)"""

    date_from: date
    date_to: date

    def as_datetime_bounds(self, timezone_name: str) -> tuple[Any, Any]:
        """แปลงเป็นขอบเขต datetime ตามเวลาท้องถิ่นของสาขา"""
        start, _ = local_day_bounds(self.date_from, timezone_name)
        _, end = local_day_bounds(self.date_to, timezone_name)
        return start, end


class AppointmentReportService:
    """
    รายงานจากข้อมูลการนัดหมาย

    รับ `clinic=None` ได้สำหรับ Super Admin ที่ต้องการดูภาพรวมทุกสาขา
    (ใช้โซนเวลาของสาขาที่ระบุ หรือ Asia/Bangkok เป็นค่าอ้างอิงกลาง)
    """

    def __init__(self, clinic: Clinic | None = None, timezone_name: str = "Asia/Bangkok") -> None:
        self.clinic = clinic
        self.timezone_name = clinic.timezone if clinic else timezone_name
        self.zone = ZoneInfo(self.timezone_name)

    # ------------------------------------------------------------------
    def base_queryset(self, period: ReportPeriod, doctor_id: int | None = None) -> QuerySet[Appointment]:
        """คิวทั้งหมดในช่วงเวลาที่สนใจ (ยังไม่กรองสถานะ)"""
        start, end = period.as_datetime_bounds(self.timezone_name)
        queryset = Appointment.objects.filter(scheduled_start__gte=start, scheduled_start__lt=end)

        if self.clinic is not None:
            queryset = queryset.filter(clinic=self.clinic)
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset

    def summary(
        self, period: ReportPeriod, group_by: str = "daily", doctor_id: int | None = None
    ) -> dict[str, Any]:
        """
        สรุปยอดจองในช่วงเวลา พร้อม breakdown ตามวัน/เดือน และ heatmap ช่วงเวลาที่คนแน่น
        """
        queryset = self.base_queryset(period, doctor_id)

        return {
            "date_from": period.date_from.isoformat(),
            "date_to": period.date_to.isoformat(),
            "group_by": group_by,
            "timezone": self.timezone_name,
            "totals": self._status_totals(queryset),
            "series": self._time_series(queryset, group_by),
            "peak_hours": self._peak_hour_heatmap(queryset),
            "by_service": self._service_breakdown(queryset),
            "by_doctor": self._doctor_breakdown(queryset),
            "average_waiting_minutes": self._average_waiting_minutes(queryset),
        }

    def no_show_rate(
        self, period: ReportPeriod, doctor_id: int | None = None
    ) -> dict[str, Any]:
        """
        อัตราการผิดนัด = จำนวน no_show / จำนวนคิวที่ถือว่า "ถึงกำหนดแล้ว"

        ตัวหารไม่รวมคิวที่ถูกยกเลิกล่วงหน้า เพราะคนไข้แจ้งล่วงหน้าไม่ถือเป็นการผิดนัด
        """
        queryset = self.base_queryset(period, doctor_id).exclude(
            status=AppointmentStatus.CANCELLED
        )
        aggregates = queryset.aggregate(
            total=Count("id"),
            no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
            completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
        )
        total = aggregates["total"] or 0
        no_show = aggregates["no_show"] or 0

        by_doctor = (
            queryset.values("doctor_id", "doctor__display_name")
            .annotate(
                total=Count("id"),
                no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
            )
            .order_by("-no_show")
        )

        return {
            "date_from": period.date_from.isoformat(),
            "date_to": period.date_to.isoformat(),
            "total_appointments": total,
            "no_show_count": no_show,
            "completed_count": aggregates["completed"] or 0,
            "no_show_rate": round(no_show / total, 4) if total else 0.0,
            "by_doctor": [
                {
                    "doctor_id": row["doctor_id"],
                    "doctor_name": row["doctor__display_name"],
                    "total": row["total"],
                    "no_show": row["no_show"],
                    "no_show_rate": round(row["no_show"] / row["total"], 4) if row["total"] else 0.0,
                }
                for row in by_doctor
            ],
        }

    # ------------------------------------------------------------------
    # ส่วนคำนวณย่อย
    # ------------------------------------------------------------------
    @staticmethod
    def _status_totals(queryset: QuerySet[Appointment]) -> dict[str, int]:
        counters = {
            status_value: Count("id", filter=Q(status=status_value))
            for status_value, _ in AppointmentStatus.choices
        }
        totals = queryset.aggregate(total=Count("id"), **counters)
        return {key: value or 0 for key, value in totals.items()}

    def _time_series(self, queryset: QuerySet[Appointment], group_by: str) -> list[dict[str, Any]]:
        """ยอดจองรายวันหรือรายเดือน สำหรับวาดกราฟเส้น"""
        truncate = TruncMonth if group_by == "monthly" else TruncDate
        rows = (
            queryset.annotate(bucket=truncate("scheduled_start", tzinfo=self.zone))
            .values("bucket")
            .annotate(
                total=Count("id"),
                completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
                cancelled=Count("id", filter=Q(status=AppointmentStatus.CANCELLED)),
                no_show=Count("id", filter=Q(status=AppointmentStatus.NO_SHOW)),
            )
            .order_by("bucket")
        )
        return [
            {
                "bucket": row["bucket"].isoformat() if row["bucket"] else None,
                "total": row["total"],
                "completed": row["completed"],
                "cancelled": row["cancelled"],
                "no_show": row["no_show"],
            }
            for row in rows
        ]

    def _peak_hour_heatmap(self, queryset: QuerySet[Appointment]) -> list[dict[str, int]]:
        """
        จำนวนคิวแยกตาม (วันในสัปดาห์ × ชั่วโมง) — ใช้วาด heatmap ชั่วโมงเร่งด่วน

        ใช้ ExtractIsoWeekDay (จันทร์=1 ... อาทิตย์=7) เพื่อให้อ่านง่ายและตรงกับปฏิทินไทย
        """
        rows = (
            queryset.annotate(
                weekday=ExtractIsoWeekDay("scheduled_start", tzinfo=self.zone),
                hour=ExtractHour("scheduled_start", tzinfo=self.zone),
            )
            .values("weekday", "hour")
            .annotate(total=Count("id"))
            .order_by("weekday", "hour")
        )
        return [
            {"weekday": row["weekday"], "hour": row["hour"], "total": row["total"]}
            for row in rows
        ]

    @staticmethod
    def _service_breakdown(queryset: QuerySet[Appointment]) -> list[dict[str, Any]]:
        rows = (
            queryset.values("service_type_id", "service_type__name")
            .annotate(
                total=Count("id"),
                revenue=Sum(
                    "service_type__price",
                    filter=Q(status=AppointmentStatus.COMPLETED),
                ),
            )
            .order_by("-total")
        )
        return [
            {
                "service_id": row["service_type_id"],
                "service_name": row["service_type__name"],
                "total": row["total"],
                # รายได้นับเฉพาะคิวที่ให้บริการเสร็จแล้ว
                "completed_revenue": float(row["revenue"] or 0),
            }
            for row in rows
        ]

    @staticmethod
    def _doctor_breakdown(queryset: QuerySet[Appointment]) -> list[dict[str, Any]]:
        rows = (
            queryset.filter(doctor__isnull=False)
            .values("doctor_id", "doctor__display_name")
            .annotate(
                total=Count("id"),
                completed=Count("id", filter=Q(status=AppointmentStatus.COMPLETED)),
                booked_minutes=Sum("service_type__duration_minutes"),
            )
            .order_by("-total")
        )
        return [
            {
                "doctor_id": row["doctor_id"],
                "doctor_name": row["doctor__display_name"],
                "total": row["total"],
                "completed": row["completed"],
                "booked_minutes": row["booked_minutes"] or 0,
            }
            for row in rows
        ]

    @staticmethod
    def _average_waiting_minutes(queryset: QuerySet[Appointment]) -> float | None:
        """
        เวลารอเฉลี่ยจริง (เช็คอิน → เริ่มรักษา) เป็นนาที

        คำนวณในฐานข้อมูลด้วยผลต่างของ timestamp เพื่อไม่ต้องดึงทุกแถวมานับใน Python
        """
        result = queryset.filter(
            checked_in_at__isnull=False, started_at__isnull=False
        ).aggregate(
            # ใช้ DurationField เพื่อให้ Django แปลงผลลัพธ์เป็น timedelta ให้เอง
            # (หน่วยของผลต่าง timestamp ต่างกันในแต่ละฐานข้อมูล)
            average=Avg(
                F("started_at") - F("checked_in_at"), output_field=DurationField()
            )
        )
        average: timedelta | None = result["average"]
        if average is None:
            return None
        return round(average.total_seconds() / 60, 1)
