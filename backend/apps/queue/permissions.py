"""Permission เฉพาะของงานหน้าคิว"""
from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.common.roles import QUEUE_OPERATION_ROLES, UserRole
from apps.scheduling.models import Appointment


class CanUpdateAppointmentStatus(BasePermission):
    """
    เปลี่ยนสถานะคิวได้: เจ้าหน้าที่/ผู้จัดการ/Super Admin (ทุกคิวในสาขา)
    และแพทย์ — เฉพาะคิวของตัวเองเท่านั้น (อัปเดตสถานะคนไข้ที่กำลังตรวจ)
    """

    message = "คุณไม่มีสิทธิ์เปลี่ยนสถานะของคิวนี้"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return user.role in QUEUE_OPERATION_ROLES or user.role == UserRole.DOCTOR

    def has_object_permission(self, request: Request, view: APIView, obj: Appointment) -> bool:
        user = request.user
        if user.role in QUEUE_OPERATION_ROLES:
            return True
        # แพทย์: แตะได้เฉพาะคิวที่ตัวเองเป็นผู้ตรวจ
        return obj.doctor is not None and obj.doctor.user_id == user.pk
