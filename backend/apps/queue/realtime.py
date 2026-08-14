"""
ส่งอัปเดตคิวแบบเรียลไทม์ผ่าน WebSocket (Django Channels)

แต่ละสาขามี channel group ของตัวเอง (`queue_updates_{clinic_id}`) เพื่อไม่ให้
ข้อมูลคิวข้ามสาขาไปถึงหน้าจอที่ไม่มีสิทธิ์เห็น

การ broadcast ล้มเหลว (เช่น Redis ล่ม) ต้องไม่ทำให้การจองคิวล้มเหลวตามไปด้วย
จึงจับ exception ไว้ทั้งหมดและบันทึกเป็น log — frontend ยัง fallback ไป polling ได้
"""
from __future__ import annotations

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction

logger = logging.getLogger(__name__)


class QueueEvent:
    """ชนิดเหตุการณ์ที่ส่งให้หน้าจอคิว"""

    APPOINTMENT_CREATED = "appointment_created"
    APPOINTMENT_UPDATED = "appointment_updated"
    APPOINTMENT_STATUS_CHANGED = "appointment_status_changed"
    APPOINTMENT_RESCHEDULED = "appointment_rescheduled"


class QueueBroadcaster:
    """ตัวกลางสำหรับส่งเหตุการณ์คิวไปยังหน้าจอทุกเครื่องของสาขานั้น"""

    GROUP_TEMPLATE = "queue_updates_{clinic_id}"

    @classmethod
    def group_name(cls, clinic_id: int) -> str:
        return cls.GROUP_TEMPLATE.format(clinic_id=clinic_id)

    @classmethod
    def broadcast(cls, clinic_id: int, event_type: str, payload: dict[str, Any]) -> None:
        """
        ส่งเหตุการณ์หลังจาก transaction commit แล้วเท่านั้น

        ถ้าส่งก่อน commit หน้าจออาจ fetch ข้อมูลกลับมาไม่เจอคิวที่เพิ่งสร้าง
        """
        transaction.on_commit(lambda: cls._send_now(clinic_id, event_type, payload))

    @classmethod
    def _send_now(cls, clinic_id: int, event_type: str, payload: dict[str, Any]) -> None:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return

        try:
            async_to_sync(channel_layer.group_send)(
                cls.group_name(clinic_id),
                {"type": "queue.event", "event": event_type, "payload": payload},
            )
        except Exception:  # noqa: BLE001 - realtime เป็นฟีเจอร์เสริม ห้ามล้มงานหลัก
            logger.exception("ส่งอัปเดตคิวแบบเรียลไทม์ไม่สำเร็จ (สาขา %s)", clinic_id)
