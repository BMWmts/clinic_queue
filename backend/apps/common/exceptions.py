"""
Exception ของชั้น business logic + ตัวแปลงเป็น HTTP response ของ DRF

Service class จะ raise exception เหล่านี้แทนการคืนค่า error code ดิบ ๆ
ทำให้ view ไม่ต้องรู้รายละเอียดของ business rule และข้อความ error
ที่ส่งกลับไปหน้าบ้านมีรูปแบบเดียวกันทั้งระบบ:

    {"error": {"code": "slot_unavailable", "message": "..."}}
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """ข้อผิดพลาดเชิงธุรกิจที่ตั้งใจให้ผู้ใช้เห็น (ไม่ใช่ bug ของระบบ)"""

    code: str = "domain_error"
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            payload["details"] = self.details
        return payload


class SlotUnavailableError(DomainError):
    """ไม่มีช่วงเวลาว่างจริงตามตารางแพทย์ — ห้าม overbook เด็ดขาด"""

    code = "slot_unavailable"
    status_code = status.HTTP_409_CONFLICT


class BookingConflictError(DomainError):
    """เวลาที่ขอจองชนกับคิวที่มีอยู่แล้ว"""

    code = "booking_conflict"
    status_code = status.HTTP_409_CONFLICT


class InvalidStatusTransitionError(DomainError):
    """เปลี่ยนสถานะคิวข้ามขั้นตอนที่ระบบไม่อนุญาต"""

    code = "invalid_status_transition"
    status_code = status.HTTP_409_CONFLICT


class BranchAccessDeniedError(DomainError):
    """พยายามเข้าถึงข้อมูลข้ามสาขาโดยไม่มีสิทธิ์"""

    code = "branch_access_denied"
    status_code = status.HTTP_403_FORBIDDEN


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Exception handler กลางของ DRF

    - DomainError → แปลงเป็น response ตาม status ที่ประกาศไว้ใน exception นั้น
    - Django ValidationError ที่หลุดมาจาก model.full_clean() → 400
    - ที่เหลือปล่อยให้ DRF จัดการตามปกติ
    """
    if isinstance(exc, DomainError):
        logger.info("Domain error: %s (%s)", exc.code, exc.message)
        return Response({"error": exc.to_payload()}, status=exc.status_code)

    if isinstance(exc, DjangoValidationError):
        return Response(
            {"error": {"code": "validation_error", "message": "ข้อมูลไม่ถูกต้อง",
                       "details": exc.message_dict if hasattr(exc, "message_dict") else exc.messages}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return drf_exception_handler(exc, context)
