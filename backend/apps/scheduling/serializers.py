"""Serializer ของการนัดหมาย"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from rest_framework import serializers

from apps.doctors.models import Doctor
from apps.patients.models import Patient
from apps.scheduling.models import Appointment, AppointmentStatus
from apps.services.models import ServiceType


class AppointmentSerializer(serializers.ModelSerializer):
    """
    ข้อมูลคิวสำหรับแสดงผล

    แนบชื่อ/ข้อมูลย่อของ relation มาด้วย เพื่อให้หน้าคิวและปฏิทินไม่ต้องยิง API ซ้ำหลายรอบ
    """

    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    patient_code = serializers.CharField(source="patient.patient_code", read_only=True)
    patient_phone = serializers.CharField(source="patient.phone", read_only=True)
    doctor_name = serializers.CharField(source="doctor.display_name", read_only=True, default=None)
    doctor_color = serializers.CharField(source="doctor.color", read_only=True, default=None)
    service_name = serializers.CharField(source="service_type.name", read_only=True)
    duration_minutes = serializers.IntegerField(
        source="service_type.duration_minutes", read_only=True
    )
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    source_display = serializers.CharField(source="get_source_display", read_only=True)
    waiting_minutes = serializers.IntegerField(read_only=True)
    allowed_next_statuses = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient",
            "patient_name",
            "patient_code",
            "patient_phone",
            "doctor",
            "doctor_name",
            "doctor_color",
            "service_type",
            "service_name",
            "duration_minutes",
            "clinic",
            "scheduled_start",
            "scheduled_end",
            "status",
            "status_display",
            "allowed_next_statuses",
            "source",
            "source_display",
            "note",
            "checked_in_at",
            "started_at",
            "completed_at",
            "waiting_minutes",
            "created_at",
        ]
        read_only_fields = fields

    def get_allowed_next_statuses(self, appointment: Appointment) -> list[str]:
        """สถานะถัดไปที่กดได้จริง — frontend ใช้ตัดสินใจว่าจะแสดงปุ่มไหน"""
        from apps.scheduling.models import ALLOWED_STATUS_TRANSITIONS

        return list(ALLOWED_STATUS_TRANSITIONS.get(appointment.status, ()))


class AppointmentCreateSerializer(serializers.Serializer):
    """
    ข้อมูลที่ใช้สร้างคิว

    ไม่รับ `scheduled_end` และ `clinic` จาก client — ระบบคำนวณ/กำหนดเองทั้งคู่
    เพื่อไม่ให้ frontend กำหนดความยาวคิวหรือข้ามสาขาได้
    """

    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.filter(is_active=True))
    service_type = serializers.PrimaryKeyRelatedField(
        queryset=ServiceType.objects.filter(is_active=True)
    )
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.filter(is_active=True), required=False, allow_null=True
    )
    scheduled_start = serializers.DateTimeField()
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        service_type: ServiceType = attrs["service_type"]
        doctor: Doctor | None = attrs.get("doctor")

        if service_type.requires_doctor and doctor is None:
            raise serializers.ValidationError({"doctor": "บริการนี้ต้องเลือกแพทย์"})
        if not service_type.requires_doctor and doctor is not None:
            # ป้องกันการผูกแพทย์กับคิวที่ระบบไม่ได้กันเวลาแพทย์ไว้ให้
            raise serializers.ValidationError(
                {"doctor": "บริการนี้ไม่ต้องใช้แพทย์ กรุณาไม่ระบุแพทย์"}
            )

        return attrs

    def validate_scheduled_start(self, value: datetime) -> datetime:
        if value.second or value.microsecond:
            # ปัดให้ลงตัวระดับนาที เพื่อให้เทียบกับ slot ที่ระบบเสนอได้ตรง ๆ
            value = value.replace(second=0, microsecond=0)
        return value


class AppointmentRescheduleSerializer(serializers.Serializer):
    """เลื่อนเวลา/เปลี่ยนแพทย์ของคิวเดิม"""

    scheduled_start = serializers.DateTimeField()
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.filter(is_active=True), required=False, allow_null=True
    )

    def validate_scheduled_start(self, value: datetime) -> datetime:
        return value.replace(second=0, microsecond=0)


class AppointmentStatusUpdateSerializer(serializers.Serializer):
    """เปลี่ยนสถานะคิว (รอพบแพทย์ → กำลังรักษา → เสร็จสิ้น / ไม่มา)"""

    status = serializers.ChoiceField(choices=AppointmentStatus.choices)
    cancelled_reason = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )


class AvailableSlotSerializer(serializers.Serializer):
    """หนึ่ง slot ว่างที่ระบบเสนอให้"""

    start = serializers.DateTimeField()
    end = serializers.DateTimeField()
