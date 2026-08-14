"""
Endpoint ของหน้าจอคิวหน้างาน

    GET   /api/queue/today/                        คิววันนี้ (หรือวันที่ระบุ)
    POST  /api/queue/walk-in/                      รับคิว walk-in (ต้องมี slot ว่างจริง)
    PATCH /api/queue/appointments/{id}/status/     เปลี่ยนสถานะ
    PATCH /api/queue/appointments/{id}/reschedule/ เลื่อน/สลับเวลา
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.branch import resolve_request_clinic
from apps.common.permissions import CanOperateQueue
from apps.doctors.views import parse_date_param
from apps.queue.permissions import CanUpdateAppointmentStatus
from apps.queue.serializers import QueueSummarySerializer, WalkInCreateSerializer
from apps.queue.services import QueueService
from apps.scheduling.models import Appointment
from apps.scheduling.serializers import (
    AppointmentRescheduleSerializer,
    AppointmentSerializer,
    AppointmentStatusUpdateSerializer,
)


class QueueServiceMixin:
    """สร้าง QueueService ของสาขาที่ผู้ใช้กำลังทำงานด้วย (ใช้ซ้ำทุก view ในไฟล์นี้)"""

    def get_queue_service(self, request: Request) -> QueueService:
        clinic = resolve_request_clinic(request)
        return QueueService(clinic=clinic, performed_by=request.user)


class TodayQueueView(QueueServiceMixin, APIView):
    """GET /api/queue/today/?clinic_id=&doctor_id=&date= — คิวของวันนั้นพร้อมสรุปจำนวน"""

    permission_classes = [CanOperateQueue]

    @extend_schema(
        parameters=[
            OpenApiParameter("doctor_id", int, description="กรองเฉพาะแพทย์คนเดียว"),
            OpenApiParameter("date", str, description="วันที่ (YYYY-MM-DD) ค่าเริ่มต้นคือวันนี้"),
        ],
        responses={200: AppointmentSerializer(many=True)},
    )
    def get(self, request: Request) -> Response:
        queue_service = self.get_queue_service(request)
        target_date = parse_date_param(request.query_params.get("date"))
        doctor_id = request.query_params.get("doctor_id")

        # แพทย์ที่ login เข้ามาเองให้เห็นเฉพาะคิวของตัวเอง
        if request.user.is_doctor:
            doctor_profile = getattr(request.user, "doctor_profile", None)
            doctor_id = doctor_profile.pk if doctor_profile else None

        appointments = queue_service.queue_for_date(target_date, doctor_id)
        summary = queue_service.queue_summary(target_date, doctor_id)

        return Response(
            {
                "clinic_id": queue_service.clinic.pk,
                "date": target_date.isoformat(),
                "timezone": queue_service.clinic.timezone,
                "summary": QueueSummarySerializer(summary).data,
                "appointments": AppointmentSerializer(appointments, many=True).data,
            }
        )


class WalkInView(QueueServiceMixin, APIView):
    """
    POST /api/queue/walk-in/ — เพิ่มคิว walk-in

    ระบบจะหา slot ว่างที่เร็วที่สุดของวันนี้ให้ ถ้าไม่มีเลยจะตอบ 409 (`slot_unavailable`)
    เจ้าหน้าที่ต้องเลือกแพทย์ท่านอื่นหรือนัดวันอื่นแทน — ไม่มีการยัดคิวเกิน
    """

    permission_classes = [CanOperateQueue]

    @extend_schema(request=WalkInCreateSerializer, responses={201: AppointmentSerializer})
    def post(self, request: Request) -> Response:
        queue_service = self.get_queue_service(request)
        serializer = WalkInCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        appointment = queue_service.add_walk_in(
            service_type=data["service_type"],
            patient=data.get("patient"),
            new_patient_data=data.get("new_patient"),
            doctor=data.get("doctor"),
            note=data.get("note", ""),
            preferred_start=data.get("preferred_start"),
        )
        return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


class AppointmentQueueActionView(QueueServiceMixin, APIView):
    """
    Base ของ action ที่ทำกับคิวใบเดียว

    รวมการดึงคิวตามสิทธิ์ (สาขาของผู้ใช้) ไว้ที่เดียว เพื่อไม่ให้แต่ละ view
    ลืมตรวจว่าคิวนั้นอยู่สาขาเดียวกับผู้ใช้หรือไม่
    """

    def get_appointment(self, request: Request, appointment_id: int) -> Appointment:
        queryset = Appointment.objects.select_related(
            "patient", "doctor", "service_type", "clinic"
        )
        if not request.user.can_access_all_branches:
            queryset = queryset.filter(clinic_id=request.user.clinic_id)

        appointment = get_object_or_404(queryset, pk=appointment_id)
        self.check_object_permissions(request, appointment)
        return appointment


class AppointmentStatusUpdateView(AppointmentQueueActionView):
    """PATCH /api/queue/appointments/{id}/status/ — เปลี่ยนสถานะคิว"""

    permission_classes = [CanUpdateAppointmentStatus]

    @extend_schema(
        request=AppointmentStatusUpdateSerializer, responses={200: AppointmentSerializer}
    )
    def patch(self, request: Request, appointment_id: int) -> Response:
        appointment = self.get_appointment(request, appointment_id)
        serializer = AppointmentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queue_service = QueueService(clinic=appointment.clinic, performed_by=request.user)
        appointment = queue_service.change_status(
            appointment,
            serializer.validated_data["status"],
            cancelled_reason=serializer.validated_data.get("cancelled_reason", ""),
        )
        return Response(AppointmentSerializer(appointment).data)


class AppointmentRescheduleView(AppointmentQueueActionView):
    """PATCH /api/queue/appointments/{id}/reschedule/ — เลื่อน/สลับเวลาคิว"""

    permission_classes = [CanOperateQueue]

    @extend_schema(request=AppointmentRescheduleSerializer, responses={200: AppointmentSerializer})
    def patch(self, request: Request, appointment_id: int) -> Response:
        appointment = self.get_appointment(request, appointment_id)
        serializer = AppointmentRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        queue_service = QueueService(clinic=appointment.clinic, performed_by=request.user)
        appointment = queue_service.reschedule(
            appointment,
            new_start=serializer.validated_data["scheduled_start"],
            new_doctor=serializer.validated_data.get("doctor"),
        )
        return Response(AppointmentSerializer(appointment).data)
