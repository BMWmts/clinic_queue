"""Serializer ของระบบ auth และการจัดการบัญชีผู้ใช้"""
from __future__ import annotations

from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User
from apps.common.roles import UserRole


class UserSerializer(serializers.ModelSerializer):
    """ข้อมูลผู้ใช้สำหรับแสดงผล (ไม่มี field อ่อนไหว เช่น password)"""

    role_display = serializers.CharField(source="get_role_display", read_only=True)
    clinic_name = serializers.CharField(source="clinic.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "role",
            "role_display",
            "clinic",
            "clinic_name",
            "is_active",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]


class UserWriteSerializer(serializers.ModelSerializer):
    """สร้าง/แก้ไขบัญชีผู้ใช้ — จัดการรหัสผ่านแบบ write-only เสมอ"""

    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = User
        fields = ["id", "email", "full_name", "phone", "role", "clinic", "is_active", "password"]

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        request_user = self.context["request"].user
        target_role = attrs.get("role") or getattr(self.instance, "role", UserRole.STAFF)

        # ผู้จัดการสาขาสร้าง/แก้บัญชีระดับ Super Admin ไม่ได้ (ป้องกัน privilege escalation)
        if target_role == UserRole.SUPER_ADMIN and not request_user.can_access_all_branches:
            raise serializers.ValidationError(
                {"role": "เฉพาะผู้ดูแลระบบสูงสุดเท่านั้นที่กำหนดบทบาท super_admin ได้"}
            )

        if target_role != UserRole.SUPER_ADMIN:
            clinic = attrs.get("clinic") or getattr(self.instance, "clinic", None)
            if clinic is None and not request_user.can_access_all_branches:
                # ผู้ใช้ทั่วไปไม่ต้องส่ง clinic มา — view จะเติมสาขาของตัวเองให้
                attrs["clinic"] = request_user.clinic
            elif clinic is None:
                raise serializers.ValidationError({"clinic": "ต้องระบุสาขาสำหรับบทบาทนี้"})

        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({"password": "ต้องกำหนดรหัสผ่านตอนสร้างบัญชีใหม่"})

        return attrs

    def create(self, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password")
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        password = validated_data.pop("password", None)
        for field_name, value in validated_data.items():
            setattr(instance, field_name, value)
        if password:
            instance.set_password(password)
        instance.full_clean(exclude=["password"])
        instance.save()
        return instance


class LoginSerializer(serializers.Serializer):
    """ตรวจสอบ email/password แล้วคืน user ที่ผ่านการยืนยันตัวตน"""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"].lower().strip(),
            password=attrs["password"],
        )
        # ข้อความ error เดียวกันทุกกรณี เพื่อไม่ให้ผู้โจมตีแยกได้ว่าอีเมลมีอยู่จริงหรือไม่
        if user is None or not user.is_active:
            raise serializers.ValidationError({"detail": "อีเมลหรือรหัสผ่านไม่ถูกต้อง"})

        attrs["user"] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """เปลี่ยนรหัสผ่านของตัวเอง — ต้องยืนยันรหัสผ่านเดิมก่อนเสมอ"""

    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)

    def validate_current_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("รหัสผ่านเดิมไม่ถูกต้อง")
        return value

    def validate_new_password(self, value: str) -> str:
        validate_password(value, user=self.context["request"].user)
        return value

    def save(self, **kwargs: Any) -> User:
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
