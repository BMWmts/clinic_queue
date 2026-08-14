"""
Endpoint รายงาน (เฉพาะผู้จัดการสาขาขึ้นไป)

    GET /api/reports/summary/?period=daily|monthly&date_from=&date_to=
    GET /api/reports/no-show-rate/?date_from=&date_to=&doctor_id=
"""
from __future__ import annotations

from datetime import date, timedelta

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clinics.models import Clinic
from apps.common.permissions import IsBranchManager
from apps.doctors.views import parse_date_param
from apps.reports.services import AppointmentReportService, ReportPeriod

#: ช่วงเวลาสูงสุดที่ยอมให้ query ครั้งเดียว (กัน query หนักเกินไปโดยไม่ตั้งใจ)
MAX_REPORT_RANGE_DAYS = 366


class BaseReportView(APIView):
    """งานร่วมของทุกรายงาน: ตรวจสิทธิ์, หาสาขา, และอ่านช่วงวันที่"""

    permission_classes = [IsBranchManager]

    def get_report_service(self, request: Request) -> AppointmentReportService:
        """
        Super Admin ดูรวมทุกสาขาได้ (ไม่ส่ง clinic_id) หรือเจาะดูสาขาเดียวก็ได้
        role อื่นถูกล็อกไว้ที่สาขาตัวเองเสมอ
        """
        user = request.user

        if user.can_access_all_branches:
            clinic_id = request.query_params.get("clinic_id")
            if not clinic_id:
                return AppointmentReportService(clinic=None)
            clinic = Clinic.objects.filter(pk=clinic_id).first()
            if clinic is None:
                raise ValidationError({"clinic_id": "ไม่พบสาขาที่ระบุ"})
            return AppointmentReportService(clinic=clinic)

        if user.clinic_id is None:
            raise ValidationError({"clinic": "บัญชีของคุณยังไม่ได้ผูกกับสาขาใด"})
        return AppointmentReportService(clinic=user.clinic)

    def get_period(self, request: Request) -> ReportPeriod:
        """ค่าเริ่มต้น: ย้อนหลัง 30 วันจนถึงวันนี้"""
        today = date.today()
        date_from = parse_date_param(
            request.query_params.get("date_from") or (today - timedelta(days=30)).isoformat(),
            "date_from",
        )
        date_to = parse_date_param(
            request.query_params.get("date_to") or today.isoformat(), "date_to"
        )

        if date_from > date_to:
            raise ValidationError({"date_from": "วันเริ่มต้นต้องไม่หลังวันสิ้นสุด"})
        if (date_to - date_from).days > MAX_REPORT_RANGE_DAYS:
            raise ValidationError(
                {"date_to": f"ดูรายงานได้ครั้งละไม่เกิน {MAX_REPORT_RANGE_DAYS} วัน"}
            )
        return ReportPeriod(date_from=date_from, date_to=date_to)


class SummaryReportView(BaseReportView):
    """สรุปยอดจอง + ช่วงเวลาที่คนแน่น (peak time heatmap)"""

    @extend_schema(
        parameters=[
            OpenApiParameter("period", str, description="daily | monthly (ค่าเริ่มต้น daily)"),
            OpenApiParameter("date_from", str, description="YYYY-MM-DD"),
            OpenApiParameter("date_to", str, description="YYYY-MM-DD"),
            OpenApiParameter("doctor_id", int, description="กรองเฉพาะแพทย์คนเดียว"),
        ],
        responses={200: dict},
    )
    def get(self, request: Request) -> Response:
        report_service = self.get_report_service(request)
        period = self.get_period(request)

        group_by = request.query_params.get("period", "daily")
        if group_by not in {"daily", "monthly"}:
            raise ValidationError({"period": "ต้องเป็น daily หรือ monthly เท่านั้น"})

        doctor_id = request.query_params.get("doctor_id")
        return Response(
            report_service.summary(
                period, group_by=group_by, doctor_id=int(doctor_id) if doctor_id else None
            )
        )


class NoShowRateReportView(BaseReportView):
    """อัตราการผิดนัด แยกตามแพทย์"""

    @extend_schema(
        parameters=[
            OpenApiParameter("date_from", str, description="YYYY-MM-DD"),
            OpenApiParameter("date_to", str, description="YYYY-MM-DD"),
            OpenApiParameter("doctor_id", int, description="กรองเฉพาะแพทย์คนเดียว"),
        ],
        responses={200: dict},
    )
    def get(self, request: Request) -> Response:
        report_service = self.get_report_service(request)
        period = self.get_period(request)
        doctor_id = request.query_params.get("doctor_id")

        return Response(
            report_service.no_show_rate(period, doctor_id=int(doctor_id) if doctor_id else None)
        )
