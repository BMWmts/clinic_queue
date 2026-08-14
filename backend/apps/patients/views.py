"""
Endpoint ฐานข้อมูลคนไข้

หมายเหตุเรื่องขอบเขตข้อมูล: คนไข้ค้นหาข้ามสาขาได้โดยตั้งใจ (ข้อกำหนดข้อ 4.8)
เพราะลูกค้าคนเดียวกันเดินเข้าได้หลายสาขา — จึงไม่ใช้ BranchScopedQuerySetMixin ที่นี่
แต่การ "สร้าง" คนไข้ใหม่ยังผูกกับสาขาของผู้ใช้เสมอผ่าน home_clinic
"""
from __future__ import annotations

from django.db.models import QuerySet
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.branch import resolve_request_clinic
from apps.common.permissions import CanOperateQueue
from apps.patients.models import Patient, PatientNote
from apps.patients.serializers import PatientNoteSerializer, PatientSerializer
from apps.patients.services import PatientRegistrationService, PatientSearchService


class PatientViewSet(viewsets.ModelViewSet):
    """CRUD คนไข้ + ค้นหา + โน้ต + ประวัติการจอง"""

    queryset = Patient.objects.select_related("home_clinic").all()
    serializer_class = PatientSerializer
    permission_classes = [CanOperateQueue]

    def get_queryset(self) -> QuerySet[Patient]:
        queryset = super().get_queryset()

        phone = self.request.query_params.get("phone")
        if phone:
            queryset = queryset.filter(phone=phone)

        home_clinic_id = self.request.query_params.get("home_clinic_id")
        if home_clinic_id:
            queryset = queryset.filter(home_clinic_id=home_clinic_id)

        return queryset

    def perform_create(self, serializer) -> None:
        """
        สร้างคนไข้ใหม่ผ่าน service เพื่อให้ได้รหัสคนไข้ที่ไม่ซ้ำ

        สาขาที่ใช้เป็น `home_clinic` มาจากตัวช่วยกลางตัวเดียวกับที่การจองคิวใช้
        (ผู้ใช้ทั่วไป = สาขาตัวเอง, Super Admin = สาขาที่ระบุมาใน clinic_id)
        """
        user = self.request.user
        clinic = resolve_request_clinic(self.request)

        registration = PatientRegistrationService(clinic=clinic, created_by=user)
        patient = registration.create_patient(**serializer.validated_data)
        serializer.instance = patient

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="เบอร์โทร / ชื่อ / รหัสคนไข้"),
            OpenApiParameter("limit", int, description="จำนวนผลลัพธ์สูงสุด (ค่าเริ่มต้น 20)"),
        ],
        responses={200: PatientSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="search")
    def search(self, request: Request) -> Response:
        """GET /api/patients/search/?q= — ค้นหาคนไข้แบบข้ามสาขา"""
        limit = min(int(request.query_params.get("limit", 20)), 100)
        results = PatientSearchService().search(request.query_params.get("q", ""), limit=limit)
        return Response(PatientSerializer(results, many=True).data)

    @extend_schema(request=PatientNoteSerializer, responses={201: PatientNoteSerializer})
    @action(detail=True, methods=["get", "post"], url_path="notes")
    def notes(self, request: Request, pk: str | None = None) -> Response:
        """
        GET  /api/patients/{id}/notes/ — โน้ตทั้งหมดของคนไข้
        POST /api/patients/{id}/notes/ — เพิ่มโน้ตใหม่
        """
        patient = self.get_object()

        if request.method == "GET":
            notes = patient.notes.select_related("created_by").all()
            return Response(PatientNoteSerializer(notes, many=True).data)

        serializer = PatientNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note: PatientNote = serializer.save(patient=patient, created_by=request.user)
        return Response(PatientNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: dict})
    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request: Request, pk: str | None = None) -> Response:
        """
        GET /api/patients/{id}/history/ — ประวัติการจองทั้งหมดของคนไข้

        import serializer ของ scheduling แบบ lazy เพื่อเลี่ยง circular import
        (scheduling อ้างถึง patients ผ่าน FK อยู่แล้ว)
        """
        from apps.scheduling.serializers import AppointmentSerializer

        patient = self.get_object()
        appointments = (
            patient.appointments.select_related("doctor", "service_type", "clinic")
            .order_by("-scheduled_start")
        )
        return Response(
            {
                "patient": PatientSerializer(patient).data,
                "appointments": AppointmentSerializer(appointments, many=True).data,
            }
        )
