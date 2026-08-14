"""
Authentication middleware สำหรับ WebSocket (Django Channels)

Browser ส่ง Authorization header ใน WebSocket handshake ไม่ได้ จึงรับ access token
ผ่าน query string `?token=` แทน — token เป็น access token อายุสั้น (นาที) และ
ไม่ถูกเขียนลง log ที่ไหน (ดู `_extract_token` ที่ไม่ log ค่าที่อ่านได้)
"""
from __future__ import annotations

import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser

logger = logging.getLogger(__name__)


@database_sync_to_async
def _get_user_from_token(raw_token: str):
    """แปลง access token เป็น User (คืน AnonymousUser ถ้า token ไม่ถูกต้อง/หมดอายุ)"""
    from rest_framework_simplejwt.exceptions import TokenError
    from rest_framework_simplejwt.tokens import AccessToken

    user_model = get_user_model()
    try:
        token = AccessToken(raw_token)
        return user_model.objects.select_related("clinic").get(
            pk=token["user_id"], is_active=True
        )
    except (TokenError, KeyError, user_model.DoesNotExist):
        logger.info("ปฏิเสธการเชื่อมต่อ WebSocket: token ไม่ถูกต้องหรือหมดอายุ")
        return AnonymousUser()


def _extract_token(scope: dict) -> str | None:
    """ดึง token จาก query string โดยไม่ log ค่า token"""
    query_string = scope.get("query_string", b"").decode()
    tokens = parse_qs(query_string).get("token", [])
    return tokens[0] if tokens else None


class JWTAuthMiddleware(BaseMiddleware):
    """ใส่ `scope["user"]` จาก JWT ก่อนส่งต่อให้ consumer"""

    async def __call__(self, scope: dict, receive, send):
        raw_token = _extract_token(scope)
        scope["user"] = await _get_user_from_token(raw_token) if raw_token else AnonymousUser()
        return await super().__call__(scope, receive, send)
