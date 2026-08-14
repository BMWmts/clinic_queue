"""
Celery task ของการแจ้งเตือน SMS

`queue_appointment_reminders` ถูกเรียกตามรอบโดย Celery beat (ทุกชั่วโมง)
แล้วแตกงานส่งจริงเป็น task ย่อยรายข้อความ เพื่อให้ข้อความหนึ่งที่ล้มเหลว
ไม่ทำให้ทั้งรอบล้มตาม และ retry เฉพาะใบที่มีปัญหาได้
"""
from __future__ import annotations

import logging

from celery import shared_task

from apps.notifications.models import SMSLog
from apps.notifications.services import AppointmentReminderService

logger = logging.getLogger(__name__)


@shared_task(name="apps.notifications.tasks.queue_appointment_reminders")
def queue_appointment_reminders() -> int:
    """สร้างบันทึกการเตือนสำหรับนัดที่ถึงเวลา แล้วสั่งส่งทีละใบ — คืนจำนวนที่สร้าง"""
    reminder_service = AppointmentReminderService()
    created_count = 0

    for appointment in reminder_service.find_due_appointments():
        sms_log = reminder_service.create_reminder_log(appointment)
        if sms_log is None:
            continue
        send_sms.delay(sms_log.pk)
        created_count += 1

    logger.info("จัดคิวแจ้งเตือนนัดหมายจำนวน %s ข้อความ", created_count)
    return created_count


@shared_task(
    name="apps.notifications.tasks.send_sms",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # ลองใหม่ทุก 5 นาที เผื่อ gateway ขัดข้องชั่วคราว
)
def send_sms(self, sms_log_id: int) -> bool:
    """ส่งข้อความหนึ่งใบตามบันทึกที่สร้างไว้"""
    sms_log = SMSLog.objects.select_related("clinic", "patient").filter(pk=sms_log_id).first()
    if sms_log is None:
        logger.warning("ไม่พบบันทึก SMS #%s (อาจถูกลบไปแล้ว)", sms_log_id)
        return False

    sent = AppointmentReminderService().send(sms_log)
    if not sent and self.request.retries < self.max_retries:
        raise self.retry(exc=RuntimeError("ส่ง SMS ไม่สำเร็จ กำลังลองใหม่"))
    return sent
