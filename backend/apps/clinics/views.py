"""
Endpoint จัดการสาขา

Super Admin: จัดการได้ทุกสาขา
role อื่น: เห็นได้เฉพาะสาขาตัวเองและอ่านอย่างเดียว (ใช้แสดงเวลาทำการบนหน้าจอ)
"""
from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.clinics.models import Clinic
from apps.clinics.serializers import ClinicSerializer


class ClinicAccessPermission(BasePermission):
    """แก้ไขสาขาได้เฉพาะ Super Admin — role อื่นอ่านได้อย่างเดียว"""

    message = "เฉพาะผู้ดูแลระบบสูงสุดเท่านั้นที่จัดการข้อมูลสาขาได้"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False
        return user.can_access_all_branches or request.method in SAFE_METHODS


class ClinicViewSet(viewsets.ModelViewSet):
    """CRUD สาขา (branch)"""

    queryset = Clinic.objects.all()
    serializer_class = ClinicSerializer
    permission_classes = [ClinicAccessPermission]

    def get_queryset(self) -> QuerySet[Clinic]:
        """
        Clinic เป็น "ตัวสาขา" เอง จึง scope ด้วย pk ตรง ๆ
        ไม่ใช้ BranchScopedQuerySetMixin ที่ filter ผ่าน FK ชื่อ clinic
        """
        queryset = super().get_queryset()
        user = self.request.user
        if user.can_access_all_branches:
            return queryset
        if user.clinic_id is None:
            return queryset.none()
        return queryset.filter(pk=user.clinic_id)
