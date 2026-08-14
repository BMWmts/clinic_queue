"""
ตัวช่วยส่งเหตุการณ์ของคิวไปยังหน้าจอเรียลไทม์

แยกเป็นไฟล์เล็ก ๆ เพื่อให้ทั้ง scheduling (จองคิว) และ queue (หน้างาน)
เรียกใช้ตัวเดียวกัน โดยไม่เกิด import วนกันระหว่างสองแอป
"""
from __future__ import annotations

from apps.queue.realtime import QueueBroadcaster
from apps.scheduling.models import Appointment


def broadcast_appointment_event(appointment: Appointment, event_type: str) -> None:
    """ส่งข้อมูลคิว (รูปแบบเดียวกับ REST API) ให้ทุกหน้าจอของสาขานั้น"""
    from apps.scheduling.serializers import AppointmentSerializer

    QueueBroadcaster.broadcast(
        clinic_id=appointment.clinic_id,
        event_type=event_type,
        payload=AppointmentSerializer(appointment).data,
    )
