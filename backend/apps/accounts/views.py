"""
Endpoint ของระบบ auth และการจัดการบัญชีผู้ใช้

Backend คืน access/refresh token เป็น JSON ส่วนการเก็บ refresh token ลง
httpOnly cookie เป็นหน้าที่ของ Next.js route handler ฝั่ง frontend
(ดู frontend/app/api/auth/) เพื่อไม่ให้ JavaScript ในเบราว์เซอร์แตะ token ได้
"""
from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from apps.accounts.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from apps.common.mixins import BranchScopedQuerySetMixin
from apps.common.permissions import IsBranchManager


def build_token_payload(user: User) -> dict[str, Any]:
    """สร้าง access/refresh token คู่กับข้อมูลผู้ใช้สำหรับ frontend"""
    refresh = RefreshToken.for_user(user)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data,
    }


class LoginView(APIView):
    """POST /api/auth/login/ — เข้าสู่ระบบด้วยอีเมล + รหัสผ่าน"""

    permission_classes = [AllowAny]
    authentication_classes: list = []
    throttle_scope = "login"  # rate limit กันการเดารหัสผ่าน (ดู settings)

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user: User = serializer.validated_data["user"]
        return Response(build_token_payload(user), status=status.HTTP_200_OK)


class RefreshView(APIView):
    """POST /api/auth/refresh/ — ขอ access token ใหม่จาก refresh token"""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request: Request) -> Response:
        raw_refresh = request.data.get("refresh")
        if not raw_refresh:
            return Response(
                {"error": {"code": "refresh_required", "message": "ไม่พบ refresh token"}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            old_refresh = RefreshToken(raw_refresh)
            user = User.objects.get(pk=old_refresh["user_id"], is_active=True)
            # ROTATE_REFRESH_TOKENS: ออก refresh ใบใหม่แล้วยกเลิกใบเก่าทันที
            # เพื่อไม่ให้ token ที่รั่วไปถูกใช้ซ้ำได้
            old_refresh.blacklist()
            new_refresh = RefreshToken.for_user(user)
            payload: dict[str, Any] = {
                "access": str(new_refresh.access_token),
                "refresh": str(new_refresh),
            }
        except (TokenError, User.DoesNotExist):
            return Response(
                {"error": {"code": "invalid_refresh", "message": "เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่"}},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return Response(payload, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """POST /api/auth/logout/ — ยกเลิก refresh token ปัจจุบัน (blacklist)"""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        raw_refresh = request.data.get("refresh")
        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                # token หมดอายุ/ถูกยกเลิกไปแล้ว ถือว่า logout สำเร็จเช่นกัน
                pass
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET /api/auth/me/ — ข้อมูลผู้ใช้ที่ login อยู่ (frontend ใช้ตัดสินใจแสดงเมนูตาม role)"""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ — เปลี่ยนรหัสผ่านของตัวเอง"""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=ChangePasswordSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserViewSet(BranchScopedQuerySetMixin, viewsets.ModelViewSet):
    """
    จัดการบัญชีผู้ใช้ในสาขา (เฉพาะผู้จัดการสาขาขึ้นไป)

    Super Admin เห็นผู้ใช้ทุกสาขา ส่วน Admin เห็นเฉพาะสาขาตัวเอง
    ผ่าน BranchScopedQuerySetMixin
    """

    queryset = User.objects.select_related("clinic").all()
    permission_classes = [IsBranchManager]
    filterset_fields: list[str] = []

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return UserWriteSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        role = self.request.query_params.get("role")
        if role:
            queryset = queryset.filter(role=role)
        return queryset

    def perform_create(self, serializer) -> None:
        # User ไม่ใช่ AuditableModel — เติมเฉพาะสาขา และตรวจสิทธิ์ข้ามสาขา
        clinic = serializer.validated_data.get("clinic")
        if serializer.validated_data.get("role") != User.Role.SUPER_ADMIN:
            clinic = self.resolve_clinic_for_write(clinic)
        serializer.save(clinic=clinic)

    def perform_update(self, serializer) -> None:
        clinic = serializer.validated_data.get("clinic", serializer.instance.clinic)
        if serializer.instance.role != User.Role.SUPER_ADMIN and clinic is not None:
            clinic = self.resolve_clinic_for_write(clinic)
        serializer.save(clinic=clinic)
