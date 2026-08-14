"""
Endpoint จัดการแพทย์ ตารางออกตรวจ และช่วงเวลาที่ถูกบล็อก

ทุก ViewSet ใช้ BranchScopedQuerySetMixin จึงเห็นเฉพาะข้อมูลสาขาตัวเองโดยอัตโนมัติ
"""
from __future__ import annotations

from datetime import date

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.branch import resolve_request_clinic
from apps.common.mixins import BranchScopedQuerySetMixin
from apps.common.permissions import IsBranchManagerOrReadOnly
from apps.doctors.models import Doctor, DoctorSchedule, TimeBlock
from apps.doctors.serializers import (
    DoctorCreateSerializer,
    DoctorScheduleSerializer,
    DoctorSerializer,
    TimeBlockSerializer,
)
from apps.doctors.services import DoctorAvailabilityService, DoctorRegistrationService


def parse_date_param(raw_value: str | None, field_name: str = "date") -> date:
    """แปลงพารามิเตอร์วันที่แบบ YYYY-MM-DD (ค่าเริ่มต้นคือวันนี้)"""
    from rest_framework.exceptions import ValidationError

    if not raw_value:
        return date.today()
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValidationError({field_name: "รูปแบบวันที่ต้องเป็น YYYY-MM-DD"}) from exc


class DoctorViewSet(BranchScopedQuerySetMixin, viewsets.ModelViewSet):
    """CRUD แพทย์ในสาขา"""

    queryset = Doctor.objects.select_related("user", "clinic").all()
    serializer_class = DoctorSerializer
    permission_classes = [IsBranchManagerOrReadOnly]

    def get_queryset(self) -> QuerySet[Doctor]:
        queryset = super().get_queryset()
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() in {"1", "true", "yes"})
        return queryset

    @extend_schema(request=DoctorCreateSerializer, responses={201: DoctorSerializer})
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        POST /api/doctors/ — รับแพทย์ใหม่เข้าทำงาน

        สร้างบัญชีผู้ใช้ (role=doctor) และโปรไฟล์แพทย์ให้พร้อมกันในคำสั่งเดียว
        หลังจากนี้ต้องเพิ่มตารางออกตรวจด้วย มิฉะนั้นระบบจะยังจองคิวให้แพทย์คนนี้ไม่ได้
        """
        clinic = resolve_request_clinic(request)
        serializer = DoctorCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        registration = DoctorRegistrationService(clinic=clinic, created_by=request.user)
        doctor = registration.create_doctor(**serializer.validated_data)

        return Response(DoctorSerializer(doctor).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        parameters=[OpenApiParameter("date", str, description="วันที่ต้องการดู (YYYY-MM-DD)")],
        responses={200: dict},
    )
    @action(detail=True, methods=["get"], url_path="availability")
    def availability(self, request: Request, pk: str | None = None) -> Response:
        """
        GET /api/doctors/{id}/availability/?date=YYYY-MM-DD

        คืนเวลาทำงานและเวลาที่ถูกบล็อกของวันนั้น — หน้าปฏิทินใช้วาดพื้นหลังตาราง
        (ยังไม่หักคิวที่จองแล้ว ส่วนนั้นดูที่ /api/scheduling/available-slots/)
        """
        doctor = self.get_object()
        target_date = parse_date_param(request.query_params.get("date"))
        availability = DoctorAvailabilityService(doctor)

        return Response(
            {
                "doctor_id": doctor.id,
                "date": target_date.isoformat(),
                "timezone": doctor.clinic.timezone,
                "working_intervals": [
                    {"start": interval.start.isoformat(), "end": interval.end.isoformat()}
                    for interval in availability.working_intervals_on(target_date)
                ],
                "blocked_intervals": [
                    {"start": interval.start.isoformat(), "end": interval.end.isoformat()}
                    for interval in availability.blocked_intervals_on(target_date)
                ],
            }
        )


class DoctorDerivedClinicMixin:
    """
    สำหรับข้อมูลที่ "สาขาต้องตามแพทย์" (ตารางออกตรวจ / ช่วงเวลาที่ถูกบล็อก)

    ตรวจก่อนเสมอว่าแพทย์ที่ระบุอยู่ในขอบเขตสาขาที่ผู้ใช้จัดการได้
    เพื่อกันการสร้างตารางให้แพทย์ของสาขาอื่น
    """

    def doctors_in_scope(self) -> QuerySet[Doctor]:
        doctors = Doctor.objects.select_related("clinic")
        user = self.request.user  # type: ignore[attr-defined]
        if user.can_access_all_branches:
            return doctors
        return doctors.filter(clinic_id=user.clinic_id)

    def perform_create(self, serializer) -> None:
        doctor = get_object_or_404(
            self.doctors_in_scope(), pk=serializer.validated_data["doctor"].pk
        )
        serializer.save(clinic=doctor.clinic)

    def perform_update(self, serializer) -> None:
        doctor = serializer.validated_data.get("doctor", serializer.instance.doctor)
        doctor = get_object_or_404(self.doctors_in_scope(), pk=doctor.pk)
        serializer.save(clinic=doctor.clinic)


class DoctorScheduleViewSet(DoctorDerivedClinicMixin, BranchScopedQuerySetMixin, viewsets.ModelViewSet):
    """CRUD ตารางออกตรวจประจำสัปดาห์"""

    queryset = DoctorSchedule.objects.select_related("doctor", "clinic").all()
    serializer_class = DoctorScheduleSerializer
    permission_classes = [IsBranchManagerOrReadOnly]

    def get_queryset(self) -> QuerySet[DoctorSchedule]:
        queryset = super().get_queryset()
        doctor_id = self.request.query_params.get("doctor_id")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset


class TimeBlockViewSet(DoctorDerivedClinicMixin, BranchScopedQuerySetMixin, viewsets.ModelViewSet):
    """CRUD ช่วงเวลาที่ถูกบล็อก"""

    queryset = TimeBlock.objects.select_related("doctor", "clinic").all()
    serializer_class = TimeBlockSerializer
    permission_classes = [IsBranchManagerOrReadOnly]

    def get_queryset(self) -> QuerySet[TimeBlock]:
        queryset = super().get_queryset()
        doctor_id = self.request.query_params.get("doctor_id")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        date_from = self.request.query_params.get("date_from")
        if date_from:
            queryset = queryset.filter(end_datetime__date__gte=parse_date_param(date_from, "date_from"))

        date_to = self.request.query_params.get("date_to")
        if date_to:
            queryset = queryset.filter(start_datetime__date__lte=parse_date_param(date_to, "date_to"))

        return queryset
