"""Serializer ของหน้าจอคิวหน้างาน"""
from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.doctors.models import Doctor
from apps.patients.models import Gender, Patient
from apps.services.models import ServiceType


class NewWalkInPatientSerializer(serializers.Serializer):
    """ข้อมูลคนไข้ใหม่ที่กรอกหน้าเคาน์เตอร์ (กรณียังไม่มีในระบบ)"""

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    phone = serializers.RegexField(r"^0\d{8,9}$", max_length=10)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(
        choices=Gender.choices, required=False, default=Gender.UNSPECIFIED
    )


class WalkInCreateSerializer(serializers.Serializer):
    """
    รับคิว walk-in

    ระบุคนไข้ได้สองแบบ: `patient` (คนไข้เดิม) หรือ `new_patient` (ลงทะเบียนใหม่)
    ต้องเลือกอย่างใดอย่างหนึ่งเท่านั้น
    """

    patient = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.filter(is_active=True), required=False, allow_null=True
    )
    new_patient = NewWalkInPatientSerializer(required=False)
    service_type = serializers.PrimaryKeyRelatedField(
        queryset=ServiceType.objects.filter(is_active=True)
    )
    doctor = serializers.PrimaryKeyRelatedField(
        queryset=Doctor.objects.filter(is_active=True), required=False, allow_null=True
    )
    note = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    preferred_start = serializers.DateTimeField(
        required=False, allow_null=True,
        help_text="เวลาที่อยากได้เร็วที่สุด (เว้นว่าง = เริ่มหาจากตอนนี้)",
    )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        has_existing_patient = attrs.get("patient") is not None
        has_new_patient = attrs.get("new_patient") is not None

        if has_existing_patient == has_new_patient:
            raise serializers.ValidationError(
                {"patient": "ต้องระบุคนไข้เดิม (patient) หรือข้อมูลคนไข้ใหม่ (new_patient) อย่างใดอย่างหนึ่ง"}
            )

        service_type: ServiceType = attrs["service_type"]
        doctor: Doctor | None = attrs.get("doctor")
        if service_type.requires_doctor and doctor is None:
            raise serializers.ValidationError({"doctor": "บริการนี้ต้องเลือกแพทย์"})
        if not service_type.requires_doctor and doctor is not None:
            raise serializers.ValidationError(
                {"doctor": "บริการนี้ไม่ต้องใช้แพทย์ กรุณาไม่ระบุแพทย์"}
            )

        return attrs


class QueueSummarySerializer(serializers.Serializer):
    """สรุปจำนวนคิวแยกตามสถานะ (ใช้กับการ์ดด้านบนหน้าจอคิว)"""

    total = serializers.IntegerField()
    booked = serializers.IntegerField()
    confirmed = serializers.IntegerField()
    checked_in = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    completed = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    no_show = serializers.IntegerField()
