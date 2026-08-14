"""Endpoint จัดการประเภทบริการ (แคตตาล็อกกลาง ใช้ร่วมกันทุกสาขา)"""
from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import viewsets

from apps.common.permissions import IsBranchManagerOrReadOnly
from apps.services.models import ServiceType
from apps.services.serializers import ServiceTypeSerializer


class ServiceTypeViewSet(viewsets.ModelViewSet):
    """
    CRUD ประเภทบริการ

    เจ้าหน้าที่/แพทย์อ่านได้ (ต้องใช้ตอนจองคิว) แต่แก้ไขได้เฉพาะผู้จัดการสาขาขึ้นไป
    """

    queryset = ServiceType.objects.all()
    serializer_class = ServiceTypeSerializer
    permission_classes = [IsBranchManagerOrReadOnly]

    def get_queryset(self) -> QuerySet[ServiceType]:
        queryset = super().get_queryset()

        # หน้าจอจองคิวเรียกด้วย ?is_active=true เพื่อไม่ให้เลือกบริการที่ปิดใช้งานแล้ว
        is_active = self.request.query_params.get("is_active")
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() in {"1", "true", "yes"})

        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        search_term = self.request.query_params.get("q")
        if search_term:
            queryset = queryset.filter(name__icontains=search_term)

        return queryset
