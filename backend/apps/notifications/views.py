"""Endpoint ตรวจสอบประวัติการส่ง SMS (อ่านอย่างเดียว)"""
from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import viewsets

from apps.common.mixins import BranchScopedQuerySetMixin
from apps.common.permissions import IsBranchManager
from apps.notifications.models import SMSLog
from apps.notifications.serializers import SMSLogSerializer


class SMSLogViewSet(BranchScopedQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    """
    ดูประวัติการส่ง SMS ของสาขา

    เป็น read-only เพราะการส่งจริงถูกสั่งโดยระบบ (Celery) เท่านั้น
    """

    queryset = SMSLog.objects.select_related("patient", "clinic").all()
    serializer_class = SMSLogSerializer
    permission_classes = [IsBranchManager]

    def get_queryset(self) -> QuerySet[SMSLog]:
        queryset = super().get_queryset()

        if status_filter := self.request.query_params.get("status"):
            queryset = queryset.filter(status=status_filter)
        if appointment_id := self.request.query_params.get("appointment_id"):
            queryset = queryset.filter(appointment_id=appointment_id)

        return queryset
