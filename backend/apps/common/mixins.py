"""
Mixin ที่ใช้ซ้ำใน ViewSet — โดยเฉพาะการจำกัดข้อมูลตามสาขา (multi-branch)

กฎเหล็กของระบบ: Admin/Staff/Doctor เห็นเฉพาะข้อมูลสาขาตัวเอง
มีเพียง Super Admin เท่านั้นที่ query ข้ามสาขาได้ การรวม logic นี้ไว้ที่เดียว
ทำให้ไม่มี endpoint ไหนหลุดการ filter ไปโดยไม่ตั้งใจ
"""
from __future__ import annotations

from typing import Any

from django.apps import apps
from django.db.models import QuerySet
from rest_framework.serializers import BaseSerializer

from apps.common.exceptions import BranchAccessDeniedError


class BranchScopedQuerySetMixin:
    """
    จำกัด queryset ให้เหลือเฉพาะสาขาของผู้ใช้ที่ login อยู่

    ตั้งค่า `clinic_lookup` ได้ถ้า model เชื่อมกับ Clinic ผ่าน path อื่น
    (เช่น `doctor__clinic` สำหรับ DoctorSchedule ที่ไม่มี FK ตรง)
    """

    clinic_lookup: str = "clinic"

    def get_queryset(self) -> QuerySet:
        queryset = super().get_queryset()  # type: ignore[misc]
        user = self.request.user  # type: ignore[attr-defined]

        if user.can_access_all_branches:
            # Super Admin เลือกดูเฉพาะสาขาที่สนใจได้ด้วย ?clinic_id=
            requested_clinic_id = self.request.query_params.get("clinic_id")  # type: ignore[attr-defined]
            if requested_clinic_id:
                return queryset.filter(**{f"{self.clinic_lookup}_id": requested_clinic_id})
            return queryset

        if user.clinic_id is None:
            # ผู้ใช้ที่ยังไม่ได้ผูกสาขา ไม่ควรเห็นข้อมูลใด ๆ
            return queryset.none()

        return queryset.filter(**{f"{self.clinic_lookup}_id": user.clinic_id})

    def resolve_clinic_for_write(self, requested_clinic: Any = None):
        """
        หา Clinic ที่จะใช้ตอนสร้าง/แก้ไขข้อมูล และตรวจสิทธิ์ข้ามสาขา

        - ผู้ใช้ทั่วไป: บังคับใช้สาขาของตัวเองเสมอ (ส่ง clinic อื่นมา = ปฏิเสธ)
        - Super Admin: ต้องระบุสาขามาให้ชัดเจน
        """
        user = self.request.user  # type: ignore[attr-defined]

        if user.can_access_all_branches:
            if requested_clinic is None:
                raise BranchAccessDeniedError("ต้องระบุสาขา (clinic) สำหรับผู้ดูแลระบบสูงสุด")
            return requested_clinic

        if user.clinic_id is None:
            raise BranchAccessDeniedError("บัญชีของคุณยังไม่ได้ผูกกับสาขาใด")

        if requested_clinic is not None and requested_clinic.pk != user.clinic_id:
            raise BranchAccessDeniedError("ไม่มีสิทธิ์สร้างหรือแก้ไขข้อมูลของสาขาอื่น")

        clinic_model = apps.get_model("clinics", "Clinic")
        return clinic_model.objects.get(pk=user.clinic_id)

    def perform_create(self, serializer: BaseSerializer) -> None:
        """ผูก clinic และ created_by ให้อัตโนมัติ โดยไม่เชื่อค่าที่ client ส่งมา"""
        model = serializer.Meta.model  # type: ignore[attr-defined]
        field_names = {field.name for field in model._meta.get_fields()}
        extra_fields: dict[str, Any] = {}

        if "clinic" in field_names:
            extra_fields["clinic"] = self.resolve_clinic_for_write(
                serializer.validated_data.get("clinic")
            )
        if "created_by" in field_names:
            extra_fields["created_by"] = self.request.user  # type: ignore[attr-defined]

        serializer.save(**extra_fields)
