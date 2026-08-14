"""
หา "สาขาที่ request กำลังทำงานด้วย"

เป็นของกลางที่หลายแอปต้องใช้ (scheduling, queue, patients) เพราะทุกครั้งที่มีการ
สร้างหรือแก้ข้อมูลที่ผูกกับสาขา ต้องตอบคำถามเดียวกันว่า "สาขาไหน"

Super Admin ไม่ได้สังกัดสาขาใดสาขาหนึ่ง (`user.clinic` เป็น None) จึงต้องระบุ
`clinic_id` มาด้วยเสมอ ส่วน role อื่นถูกล็อกไว้ที่สาขาตัวเองโดยไม่สนใจค่าที่ส่งมา
"""
from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from apps.clinics.models import Clinic
from apps.common.exceptions import BranchAccessDeniedError


def resolve_request_clinic(request: Request) -> Clinic:
    """
    คืนสาขาที่ request นี้ทำงานด้วย

    ผู้ใช้ทั่วไป = สาขาของตัวเองเสมอ
    Super Admin = ต้องระบุ `clinic_id` (รับได้ทั้งจาก query string และ body)
    """
    user = request.user

    if user.can_access_all_branches:
        clinic_id = request.query_params.get("clinic_id") or request.data.get("clinic_id")
        if not clinic_id:
            raise ValidationError({"clinic_id": "ผู้ดูแลระบบสูงสุดต้องระบุสาขาที่ต้องการทำงานด้วย"})
        return get_object_or_404(Clinic, pk=clinic_id)

    if user.clinic_id is None:
        raise BranchAccessDeniedError("บัญชีของคุณยังไม่ได้ผูกกับสาขาใด")
    return user.clinic
