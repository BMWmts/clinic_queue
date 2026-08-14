"""Serializer helper ที่ใช้ร่วมกันทุก app"""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class ModelCleanValidationMixin:
    """
    เรียก `Model.clean()` ตอน validate ของ serializer

    DRF ไม่เรียก `clean()` ของ model ให้อัตโนมัติ ทำให้ business rule ที่เขียนไว้
    ใกล้ข้อมูล (เช่น "เวลาเลิกต้องหลังเวลาเริ่ม", "ตารางห้ามทับกัน") ถูกข้ามไป
    mixin นี้ดึงกฎเดียวกันกลับมาใช้กับ API โดยไม่ต้องเขียน validate ซ้ำสองที่
    """

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        attrs = super().validate(attrs)  # type: ignore[misc]

        model_class = self.Meta.model  # type: ignore[attr-defined]
        instance = self.instance if self.instance is not None else model_class()  # type: ignore[attr-defined]

        # ประกอบค่าที่ส่งเข้ามาลงบน instance ชั่วคราวเพื่อให้ clean() เห็นค่าล่าสุด
        # (กรณี update จะใช้ instance เดิมเป็นฐาน แล้วค่อยทับด้วยค่าที่แก้)
        original_values = {}
        for field_name, value in attrs.items():
            if hasattr(instance, field_name):
                original_values[field_name] = getattr(instance, field_name, None)
                setattr(instance, field_name, value)

        try:
            instance.clean()
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
            raise serializers.ValidationError(detail) from exc
        finally:
            if self.instance is not None:
                # คืนค่าเดิมให้ instance เพื่อไม่ให้ค่าที่ยังไม่ผ่านการบันทึกค้างอยู่
                for field_name, value in original_values.items():
                    setattr(instance, field_name, value)

        return attrs
