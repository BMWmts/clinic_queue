"""Serializer ของแพทย์ ตารางออกตรวจ และช่วงเวลาที่ถูกบล็อก"""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.common.roles import UserRole
from apps.common.serializers import ModelCleanValidationMixin
from apps.doctors.models import Doctor, DoctorSchedule, TimeBlock


class DoctorSerializer(ModelCleanValidationMixin, serializers.ModelSerializer):
    """ข้อมูลแพทย์ — clinic ถูกกำหนดโดย backend จากผู้ใช้ที่ login (ดู ViewSet)"""

    email = serializers.EmailField(source="user.email", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True)

    class Meta:
        model = Doctor
        fields = [
            "id",
            "user",
            "email",
            "clinic",
            "clinic_name",
            "display_name",
            "specialties",
            "color",
            "is_active",
        ]
        read_only_fields = ["id"]
        # ผู้ใช้ทั่วไปไม่ต้องส่ง clinic (ระบบเติมสาขาของตัวเองให้)
        # Super Admin ที่ดูแลหลายสาขาจึงจะระบุ clinic มาเอง
        extra_kwargs = {"clinic": {"required": False}}

    def validate_user(self, value: Any) -> Any:
        if value.role != UserRole.DOCTOR:
            raise serializers.ValidationError("บัญชีผู้ใช้ที่เลือกต้องมีบทบาทเป็นแพทย์")
        return value


class DoctorCreateSerializer(serializers.Serializer):
    """
    รับแพทย์ใหม่เข้าทำงาน — รับข้อมูลบัญชีและโปรไฟล์มาพร้อมกันในคำขอเดียว

    ไม่ใช้ ModelSerializer เพราะข้อมูลชุดนี้กระจายอยู่สองตาราง (User + Doctor)
    การประกอบร่างทั้งสองอยู่ใน DoctorRegistrationService
    """

    email = serializers.EmailField()
    full_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.RegexField(
        r"^0\d{8,9}$", max_length=10, required=False, allow_blank=True, default=""
    )

    display_name = serializers.CharField(max_length=150)
    specialties = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    color = serializers.RegexField(
        r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$", required=False, default="#2563eb"
    )

    def validate_email(self, value: str) -> str:
        normalized_email = value.lower().strip()
        if get_user_model().objects.filter(email=normalized_email).exists():
            raise serializers.ValidationError("อีเมลนี้ถูกใช้งานแล้วในระบบ")
        return normalized_email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value


class DoctorScheduleSerializer(ModelCleanValidationMixin, serializers.ModelSerializer):
    """ตารางออกตรวจประจำสัปดาห์"""

    day_of_week_display = serializers.CharField(source="get_day_of_week_display", read_only=True)
    doctor_name = serializers.CharField(source="doctor.display_name", read_only=True)

    class Meta:
        model = DoctorSchedule
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "clinic",
            "day_of_week",
            "day_of_week_display",
            "start_time",
            "end_time",
            "is_active",
        ]
        read_only_fields = ["id", "clinic"]


class TimeBlockSerializer(ModelCleanValidationMixin, serializers.ModelSerializer):
    """ช่วงเวลาที่แพทย์ไม่รับคิว (พักเที่ยง/ลา/เคสด่วน)"""

    reason_display = serializers.CharField(source="get_reason_display", read_only=True)
    doctor_name = serializers.CharField(source="doctor.display_name", read_only=True)

    class Meta:
        model = TimeBlock
        fields = [
            "id",
            "doctor",
            "doctor_name",
            "clinic",
            "start_datetime",
            "end_datetime",
            "reason",
            "reason_display",
            "note",
            "is_recurring",
            "recurrence",
            "recurrence_end_date",
        ]
        read_only_fields = ["id", "clinic"]
