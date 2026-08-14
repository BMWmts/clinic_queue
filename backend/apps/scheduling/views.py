"""
Endpoint การนัดหมาย และการค้นหาช่วงเวลาว่าง

view ทำหน้าที่แค่ "แปลง request → เรียก service → แปลงผลลัพธ์เป็น response"
ส่วนกฎธุรกิจทั้งหมดอยู่ใน apps/scheduling/services.py
"""
from __future__ import annotations

from datetime import date

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.clinics.models import Clinic
from apps.common.branch import resolve_request_clinic
from apps.common.mixins import BranchScopedQuerySetMixin
from apps.common.permissions import CanOperateQueue
from apps.common.timezone_utils import to_local
from apps.doctors.models import Doctor
from apps.doctors.views import parse_date_param
from apps.queue.realtime import QueueEvent
from apps.scheduling.broadcast import broadcast_appointment_event
from apps.scheduling.models import Appointment
from apps.scheduling.serializers import (
    AppointmentCreateSerializer,
    AppointmentSerializer,
    AvailableSlotSerializer,
)
from apps.scheduling.services import AppointmentBookingService, SlotAvailabilityService
from apps.services.models import ServiceType


class AppointmentViewSet(BranchScopedQuerySetMixin, viewsets.ModelViewSet):
    """
    รายการ/สร้างการนัดหมาย

    การเปลี่ยนสถานะและการเลื่อนคิวอยู่ที่ /api/queue/ เพราะเป็นงานหน้างาน
    """

    queryset = Appointment.objects.select_related(
        "patient", "doctor", "service_type", "clinic"
    ).all()
    serializer_class = AppointmentSerializer
    permission_classes = [CanOperateQueue]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self) -> QuerySet[Appointment]:
        queryset = super().get_queryset()
        params = self.request.query_params

        if doctor_id := params.get("doctor_id"):
            queryset = queryset.filter(doctor_id=doctor_id)
        if patient_id := params.get("patient_id"):
            queryset = queryset.filter(patient_id=patient_id)
        if status_filter := params.get("status"):
            queryset = queryset.filter(status__in=status_filter.split(","))
        if date_from := params.get("date_from"):
            queryset = queryset.filter(
                scheduled_end__date__gte=parse_date_param(date_from, "date_from")
            )
        if date_to := params.get("date_to"):
            queryset = queryset.filter(
                scheduled_start__date__lte=parse_date_param(date_to, "date_to")
            )

        # แพทย์เห็นเฉพาะคิวของตัวเอง (นอกเหนือจากการ scope ตามสาขา)
        user = self.request.user
        if user.is_doctor:
            queryset = queryset.filter(doctor__user_id=user.pk)

        return queryset

    @extend_schema(request=AppointmentCreateSerializer, responses={201: AppointmentSerializer})
    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        POST /api/scheduling/appointments/ — สร้างการจอง

        ระบบตรวจเวลาว่างจริงที่ backend เสมอ ถ้าเวลาชนหรือไม่มี slot ว่าง
        จะตอบ 409 พร้อมรหัส `slot_unavailable` / `booking_conflict`
        """
        clinic = resolve_request_clinic(request)
        serializer = AppointmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        booking = AppointmentBookingService(clinic=clinic, performed_by=request.user)
        appointment = booking.book(
            patient=serializer.validated_data["patient"],
            service_type=serializer.validated_data["service_type"],
            scheduled_start=serializer.validated_data["scheduled_start"],
            doctor=serializer.validated_data.get("doctor"),
            note=serializer.validated_data.get("note", ""),
        )

        broadcast_appointment_event(appointment, QueueEvent.APPOINTMENT_CREATED)
        return Response(
            AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED
        )


class AvailableSlotsView(APIView):
    """
    GET /api/scheduling/available-slots/?doctor_id=&service_id=&date=

    คืนช่วงเวลาที่จองได้จริง หลังหักเวลาที่ถูกบล็อกและคิวที่จองแล้วออก
    หน้าจอจองคิวเรียก endpoint นี้เพื่อแสดงเฉพาะเวลาที่กดได้
    """

    permission_classes = [CanOperateQueue]

    @extend_schema(
        parameters=[
            OpenApiParameter("service_id", int, required=True, description="รหัสประเภทบริการ"),
            OpenApiParameter("doctor_id", int, description="รหัสแพทย์ (บังคับถ้าบริการต้องมีแพทย์)"),
            OpenApiParameter("date", str, description="วันที่ต้องการจอง (YYYY-MM-DD)"),
        ],
        responses={200: AvailableSlotSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        clinic = resolve_request_clinic(request)
        service_type = self._get_service_type(request)
        doctor = self._get_doctor(request, clinic)
        target_date: date = parse_date_param(request.query_params.get("date"))

        availability = SlotAvailabilityService(clinic, service_type, doctor)
        slots = availability.available_slots(target_date)

        return Response(
            {
                "clinic_id": clinic.pk,
                "timezone": clinic.timezone,
                "date": target_date.isoformat(),
                "service_id": service_type.pk,
                "duration_minutes": service_type.duration_minutes,
                "doctor_id": doctor.pk if doctor else None,
                # แปลงเป็นเวลาท้องถิ่นของสาขาก่อนส่งออก เพื่อให้ค่าที่ frontend ได้รับ
                # อ่านแล้วตรงกับเวลาบนนาฬิกาหน้าร้าน (ค่าที่แทนช่วงเวลาเดียวกันเสมอ)
                "slots": [
                    {
                        "start": to_local(slot.start, clinic.timezone).isoformat(),
                        "end": to_local(slot.end, clinic.timezone).isoformat(),
                    }
                    for slot in slots
                ],
            }
        )

    @staticmethod
    def _get_service_type(request: Request) -> ServiceType:
        service_id = request.query_params.get("service_id")
        if not service_id:
            raise ValidationError({"service_id": "ต้องระบุบริการที่ต้องการจอง"})
        return get_object_or_404(ServiceType, pk=service_id, is_active=True)

    @staticmethod
    def _get_doctor(request: Request, clinic: Clinic) -> Doctor | None:
        doctor_id = request.query_params.get("doctor_id")
        if not doctor_id:
            return None
        # จำกัดให้เลือกได้เฉพาะแพทย์ในสาขาเดียวกัน กันการดูตารางข้ามสาขา
        return get_object_or_404(Doctor, pk=doctor_id, clinic=clinic, is_active=True)
