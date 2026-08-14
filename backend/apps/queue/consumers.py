"""
WebSocket consumer ของหน้าจอคิว

หน้าจอหน้างานเชื่อมต่อมาที่ `ws://<host>/ws/queue/<clinic_id>/?token=<access_token>`
แล้วรอรับเหตุการณ์ เช่น มีคิวใหม่ / เปลี่ยนสถานะ / เลื่อนเวลา
"""
from __future__ import annotations

import logging
from typing import Any

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.queue.realtime import QueueBroadcaster

logger = logging.getLogger(__name__)


class QueueConsumer(AsyncJsonWebsocketConsumer):
    """รับ-ส่งอัปเดตคิวของสาขาหนึ่ง (อ่านอย่างเดียว — การแก้ไขทำผ่าน REST API)"""

    async def connect(self) -> None:
        user = self.scope.get("user")
        clinic_id = int(self.scope["url_route"]["kwargs"]["clinic_id"])

        if not (user and user.is_authenticated):
            await self.close(code=4401)  # ไม่ได้ยืนยันตัวตน
            return

        # กันการแอบฟังคิวของสาขาอื่น (Super Admin ดูได้ทุกสาขา)
        if not user.can_access_all_branches and user.clinic_id != clinic_id:
            await self.close(code=4403)  # ไม่มีสิทธิ์เข้าถึงสาขานี้
            return

        self.clinic_id = clinic_id
        self.group_name = QueueBroadcaster.group_name(clinic_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected", "payload": {"clinic_id": clinic_id}})

    async def disconnect(self, code: int) -> None:
        group_name = getattr(self, "group_name", None)
        if group_name:
            await self.channel_layer.group_discard(group_name, self.channel_name)

    async def receive_json(self, content: dict[str, Any], **kwargs: Any) -> None:
        """รองรับเฉพาะ ping เพื่อ keep-alive — ไม่รับคำสั่งแก้ไขข้อมูลทาง WebSocket"""
        if content.get("action") == "ping":
            await self.send_json({"event": "pong", "payload": {}})

    async def queue_event(self, message: dict[str, Any]) -> None:
        """ตัวรับ event จาก channel layer (type = "queue.event")"""
        await self.send_json({"event": message["event"], "payload": message["payload"]})
