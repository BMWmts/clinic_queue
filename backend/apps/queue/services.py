"""
Business logic ของหน้าจอคิวหน้างาน

ห่อการทำงานที่หน้าเคาน์เตอร์ใช้บ่อย (ดูคิววันนี้, รับ walk-in, เปลี่ยนสถานะ, เลื่อนคิว)
ไว้ในที่เดียว โดยยืมกฎการจอง/กันคิวชนทั้งหมดมาจาก apps.scheduling.services
— ห้ามมีทางลัดที่ข้ามการตรวจ slot ว่างเด็ดขาด
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from django.db.models import Count, Q, QuerySet

from apps.clinics.models import Clinic
from apps.common.timezone_utils import local_date_of, local_day_bounds
from apps.doctors.models import Doctor
from apps.patients.models import Patient
from apps.patients.services import PatientRegistrationService
from apps.queue.realtime import QueueEvent
from apps.scheduling.broadcast import broadcast_appointment_event
from apps.scheduling.models import Appointment, AppointmentStatus
from apps.scheduling.services import AppointmentBookingService
from apps.services.models import ServiceType
from django.utils import timezone

logger = logging.getLogger(__name__)


class QueueService:
    """งานหน้างานของสาขาหนึ่ง"""

    def __init__(self, clinic: Clinic, performed_by: Any = None) -> None:
        self.clinic = clinic
        self.performed_by = performed_by
        self.booking = AppointmentBookingService(clinic=clinic, performed_by=performed_by)

    # ------------------------------------------------------------------
    # อ่านคิว
    # ------------------------------------------------------------------
    def queue_for_date(
        self, target_date: date | None = None, doctor_id: int | None = None
    ) -> QuerySet[Appointment]:
        """คิวของวันนั้นทั้งหมด เรียงตามเวลานัด (รวมคิวที่ยกเลิก/ไม่มา เพื่อให้เห็นภาพครบ)"""
        target_date = target_date or local_date_of(timezone.now(), self.clinic.timezone)
        day_start, day_end = local_day_bounds(target_date, self.clinic.timezone)

        queryset = (
            Appointment.objects.select_related("patient", "doctor", "service_type")
            .for_clinic_day(self.clinic, day_start, day_end)
            .order_by("scheduled_start")
        )
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)
        return queryset

    def queue_summary(self, target_date: date | None = None, doctor_id: int | None = None) -> dict[str, int]:
        """
        นับจำนวนคิวแยกตามสถานะ — ใช้แสดงการ์ดสรุปด้านบนหน้าจอคิว

        ใช้ aggregate ครั้งเดียวแทนการนับใน Python เพื่อไม่ให้โหลดข้อมูลเกินจำเป็น
        """
        counters = {
            status_value: Count("id", filter=Q(status=status_value))
            for status_value, _ in AppointmentStatus.choices
        }
        summary = self.queue_for_date(target_date, doctor_id).aggregate(
            total=Count("id"), **counters
        )
        return {key: value or 0 for key, value in summary.items()}

    # ------------------------------------------------------------------
    # เขียน
    # ------------------------------------------------------------------
    def add_walk_in(
        self,
        *,
        service_type: ServiceType,
        patient: Patient | None = None,
        new_patient_data: dict[str, Any] | None = None,
        doctor: Doctor | None = None,
        note: str = "",
        preferred_start: datetime | None = None,
    ) -> Appointment:
        """
        รับคิว walk-in — ได้เฉพาะเมื่อมี slot ว่างจริงเท่านั้น

        ถ้าคนไข้ยังไม่มีในระบบ จะลงทะเบียนให้ก่อน (จับคู่ด้วยเบอร์โทรเพื่อไม่ให้ซ้ำ)
        """
        if patient is None:
            patient = self._resolve_walk_in_patient(new_patient_data or {})

        appointment = self.booking.book_walk_in(
            patient=patient,
            service_type=service_type,
            doctor=doctor,
            note=note,
            preferred_start=preferred_start,
        )
        broadcast_appointment_event(appointment, QueueEvent.APPOINTMENT_CREATED)
        return appointment

    def change_status(
        self, appointment: Appointment, new_status: str, cancelled_reason: str = ""
    ) -> Appointment:
        """เปลี่ยนสถานะคิวแล้วแจ้งทุกหน้าจอในสาขาให้อัปเดตทันที"""
        if new_status == AppointmentStatus.CANCELLED:
            appointment = self.booking.cancel(appointment, reason=cancelled_reason)
        else:
            appointment = self.booking.change_status(appointment, new_status)

        broadcast_appointment_event(appointment, QueueEvent.APPOINTMENT_STATUS_CHANGED)
        return appointment

    def reschedule(
        self, appointment: Appointment, *, new_start: datetime, new_doctor: Doctor | None = None
    ) -> Appointment:
        """เลื่อน/สลับเวลาคิว (ใช้กับการลากวางบนหน้าจอ)"""
        appointment = self.booking.reschedule(
            appointment, new_start=new_start, new_doctor=new_doctor
        )
        broadcast_appointment_event(appointment, QueueEvent.APPOINTMENT_RESCHEDULED)
        return appointment

    # ------------------------------------------------------------------
    def _resolve_walk_in_patient(self, new_patient_data: dict[str, Any]) -> Patient:
        """
        หาคนไข้เดิมจากเบอร์โทร ถ้าไม่มีจึงสร้างใหม่

        ป้องกันการมีคนไข้ซ้ำหลาย record เมื่อลูกค้าประจำเดินเข้ามาแบบไม่ได้นัด
        """
        registration = PatientRegistrationService(
            clinic=self.clinic, created_by=self.performed_by
        )
        phone = new_patient_data.get("phone", "")

        existing = registration.find_existing_by_phone(phone).filter(
            first_name=new_patient_data.get("first_name", "")
        ).first()
        if existing is not None:
            return existing

        return registration.create_patient(**new_patient_data)
