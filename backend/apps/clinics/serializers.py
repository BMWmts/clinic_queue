"""Serializer ของสาขา"""
from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rest_framework import serializers

from apps.clinics.models import Clinic


class ClinicSerializer(serializers.ModelSerializer):
    """ข้อมูลสาขา — ไม่มี secret ของ SMS gateway (credential อยู่ใน environment variable)"""

    class Meta:
        model = Clinic
        fields = [
            "id",
            "name",
            "code",
            "address",
            "phone",
            "opening_time",
            "closing_time",
            "timezone",
            "slot_interval_minutes",
            "non_doctor_service_capacity",
            "sms_provider",
            "sms_sender_name",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_timezone(self, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise serializers.ValidationError("ชื่อโซนเวลาไม่ถูกต้อง เช่น Asia/Bangkok") from exc
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        opening_time = attrs.get("opening_time") or getattr(self.instance, "opening_time", None)
        closing_time = attrs.get("closing_time") or getattr(self.instance, "closing_time", None)
        if opening_time and closing_time and opening_time >= closing_time:
            raise serializers.ValidationError({"closing_time": "เวลาปิดต้องหลังเวลาเปิด"})
        return attrs
