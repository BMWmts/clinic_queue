"""
Business logic ของการแจ้งเตือนคนไข้ทาง SMS

หน้าที่หลักสองอย่าง:
1) หานัดหมายที่ถึงเวลาต้องเตือน แล้วสร้าง SMSLog (สถานะรอส่ง)
2) ส่งข้อความจริงผ่าน provider ของสาขา แล้วบันทึกผลลง log เดิม
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.common.timezone_utils import to_local
from apps.notifications.models import SmsKind, SMSLog, SmsStatus
from apps.notifications.providers import (
    BaseSmsProvider,
    SmsConfigurationError,
    SmsProviderFactory,
)
from apps.scheduling.models import Appointment, AppointmentStatus

logger = logging.getLogger(__name__)

#: ความกว้างของหน้าต่างที่ถือว่า "ถึงเวลาเตือน" — ต้องกว้างกว่ารอบของ Celery beat
#: เล็กน้อย เพื่อไม่ให้มีนัดหลุดการเตือนหากงานรันช้ากว่ากำหนดเล็กน้อย
REMINDER_WINDOW = timedelta(hours=1, minutes=5)


class AppointmentReminderService:
    """สร้างและส่งข้อความเตือนนัดหมายล่วงหน้า"""

    def __init__(self, hours_before: int | None = None) -> None:
        self.hours_before = hours_before or settings.SMS_REMINDER_HOURS_BEFORE

    # ------------------------------------------------------------------
    def find_due_appointments(self, now: datetime | None = None):
        """
        นัดหมายที่ควรถูกเตือนตอนนี้

        เงื่อนไข: ยังไม่ถูกยกเลิก/ไม่มา และเวลานัดอยู่ในหน้าต่าง
        [now + hours_before, now + hours_before + REMINDER_WINDOW)
        """
        now = now or timezone.now()
        window_start = now + timedelta(hours=self.hours_before)
        window_end = window_start + REMINDER_WINDOW

        return (
            Appointment.objects.filter(
                scheduled_start__gte=window_start,
                scheduled_start__lt=window_end,
                status__in=[AppointmentStatus.BOOKED, AppointmentStatus.CONFIRMED],
            )
            .select_related("patient", "doctor", "service_type", "clinic")
            .exclude(
                # ข้ามนัดที่มี log ค้างอยู่แล้ว (รอส่ง/ส่งแล้ว) เพื่อไม่ส่งซ้ำ
                sms_logs__kind=SmsKind.APPOINTMENT_REMINDER,
                sms_logs__status__in=[SmsStatus.PENDING, SmsStatus.SENT],
            )
        )

    def create_reminder_log(self, appointment: Appointment) -> SMSLog | None:
        """
        สร้างบันทึกการส่งสถานะ "รอส่ง"

        unique constraint ระดับ DB เป็นตัวกันซ้ำอีกชั้น หากมีงานสองตัวรันพร้อมกัน
        (คืน None เมื่อมีบันทึกอยู่แล้ว)
        """
        try:
            with transaction.atomic():
                return SMSLog.objects.create(
                    clinic=appointment.clinic,
                    patient=appointment.patient,
                    appointment=appointment,
                    kind=SmsKind.APPOINTMENT_REMINDER,
                    message=self.build_message(appointment),
                )
        except IntegrityError:
            logger.info("มีบันทึกการเตือนของนัด #%s อยู่แล้ว ข้ามการสร้างซ้ำ", appointment.pk)
            return None

    def build_message(self, appointment: Appointment) -> str:
        """
        ข้อความแจ้งเตือนภาษาไทย

        ไม่ใส่ข้อมูลอ่อนไหวเกินจำเป็น (ไม่มีรหัสคนไข้/รายละเอียดการรักษา)
        """
        clinic = appointment.clinic
        local_start = to_local(appointment.scheduled_start, clinic.timezone)
        doctor_part = f" กับ{appointment.doctor.display_name}" if appointment.doctor else ""

        return (
            f"แจ้งเตือนนัดหมาย: คุณ{appointment.patient.first_name} "
            f"มีนัด {appointment.service_type.name}{doctor_part} "
            f"วันที่ {local_start:%d/%m/%Y} เวลา {local_start:%H:%M} น. "
            f"ที่ {clinic.name} สอบถามเพิ่มเติม {clinic.phone or '-'}"
        )

    # ------------------------------------------------------------------
    def send(self, sms_log: SMSLog, provider: BaseSmsProvider | None = None) -> bool:
        """ส่งข้อความของ log นี้ผ่าน provider ของสาขา แล้วบันทึกผลลัพธ์"""
        if sms_log.status == SmsStatus.SENT:
            return True

        try:
            provider = provider or SmsProviderFactory.for_clinic(sms_log.clinic)
        except SmsConfigurationError as exc:
            sms_log.mark_failed(provider="", error_message=str(exc))
            logger.error("ตั้งค่า SMS provider ของสาขา %s ไม่ถูกต้อง", sms_log.clinic_id)
            return False

        result = provider.send(sms_log.patient.phone, sms_log.message)
        if result.success:
            sms_log.mark_sent(result.provider, result.provider_message_id)
            return True

        sms_log.mark_failed(result.provider, result.error_message)
        return False
