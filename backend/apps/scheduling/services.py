"""
หัวใจของระบบ: การคำนวณเวลาว่างจริง และการจองคิวที่ห้าม overbook

แบ่งเป็นสอง service ตามความรับผิดชอบ
    SlotAvailabilityService  — "ว่างเมื่อไรบ้าง" (อ่านอย่างเดียว)
    AppointmentBookingService — "จอง/เลื่อน/ยกเลิก" (เขียน + ตรวจกฎ)

กติกาที่ห้ามละเมิดเด็ดขาด (ข้อกำหนดข้อ 4.7 และ 11):
    ทุกการสร้าง/แก้ไขคิว ต้องผ่าน `SlotAvailabilityService.is_slot_available()`
    ถ้าไม่มีเวลาว่างจริง ต้อง reject ไม่มีข้อยกเว้น รวมถึงคิว walk-in
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Iterable

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.clinics.models import Clinic
from apps.common.exceptions import BookingConflictError, SlotUnavailableError
from apps.common.time_intervals import IntervalSet, TimeInterval, generate_slot_starts
from apps.common.timezone_utils import local_date_of, local_day_bounds
from apps.doctors.models import Doctor
from apps.doctors.services import DoctorAvailabilityService
from apps.patients.models import Patient
from apps.scheduling.models import Appointment, AppointmentSource, AppointmentStatus
from apps.services.models import ServiceType

logger = logging.getLogger(__name__)

#: จำนวนวันสูงสุดที่ยอมให้ไล่หา slot ว่างถัดไป (กันการวนหาไม่รู้จบเมื่อไม่มีตารางแพทย์)
MAX_SEARCH_DAYS = 30


class SlotAvailabilityService:
    """
    คำนวณช่วงเวลาที่จองได้จริงของบริการหนึ่งในวันหนึ่ง

    มีสองโหมดตามชนิดบริการ:
    1) บริการที่ต้องมีแพทย์ — เวลาว่าง = ตารางออกตรวจ − เวลาที่ถูกบล็อก − คิวที่จองแล้ว
    2) บริการที่ไม่ต้องมีแพทย์ — จำกัดด้วยเพดานจำนวนเคสพร้อมกันของสาขา
       (เช่น มีเตียงดริป 3 เตียง → รับพร้อมกันได้ 3 คิว)
    """

    def __init__(
        self,
        clinic: Clinic,
        service_type: ServiceType,
        doctor: Doctor | None = None,
    ) -> None:
        if service_type.requires_doctor and doctor is None:
            raise SlotUnavailableError("บริการนี้ต้องเลือกแพทย์ก่อนจึงจะดูเวลาว่างได้")
        if doctor is not None and doctor.clinic_id != clinic.pk:
            raise SlotUnavailableError("แพทย์ที่เลือกไม่ได้อยู่ในสาขานี้")

        self.clinic = clinic
        self.service_type = service_type
        self.doctor = doctor
        self.timezone_name: str = clinic.timezone

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------
    def available_slots(
        self, target_date: date, include_past: bool = False
    ) -> list[TimeInterval]:
        """
        รายการ slot ที่จองได้จริงของวันนั้น เรียงตามเวลา

        `include_past=False` (ค่าเริ่มต้น) จะไม่เสนอเวลาที่ผ่านไปแล้วของวันนี้
        """
        not_before = None if include_past else self._earliest_bookable_moment(target_date)

        if self.doctor is not None:
            return self._doctor_slots(target_date, not_before)
        return self._capacity_based_slots(target_date, not_before)

    def is_slot_available(
        self, interval: TimeInterval, exclude_appointment_id: int | None = None
    ) -> bool:
        """
        ช่วงเวลาที่ขอมาจองได้จริงหรือไม่

        ใช้ตรวจก่อนบันทึกทุกครั้ง (ทั้งจองใหม่ เลื่อนคิว และ walk-in)
        `exclude_appointment_id` ใช้ตอนเลื่อนคิว เพื่อไม่ให้คิวเดิมนับว่าชนกับตัวเอง
        """
        if not self.clinic.opening_interval_on(
            local_date_of(interval.start, self.timezone_name)
        ).contains(interval):
            return False

        if self.doctor is not None:
            return self._is_doctor_slot_available(interval, exclude_appointment_id)
        return self._is_capacity_slot_available(interval, exclude_appointment_id)

    def find_next_available_slot(
        self, from_moment: datetime, search_days: int = 7
    ) -> TimeInterval | None:
        """
        หา slot ว่างที่เร็วที่สุดนับจากเวลาที่กำหนด (ใช้กับ walk-in)

        ไล่ทีละวันไม่เกิน `search_days` — ถ้าไม่เจอเลยแปลว่าคิวเต็มจริง
        และผู้เรียกต้องปฏิเสธการจอง ไม่ใช่ยัดคิวเพิ่ม
        """
        search_days = min(search_days, MAX_SEARCH_DAYS)
        current_date = local_date_of(from_moment, self.timezone_name)

        for day_offset in range(search_days):
            target_date = current_date + timedelta(days=day_offset)
            for slot in self.available_slots(target_date):
                if slot.start >= from_moment:
                    return slot
        return None

    # ------------------------------------------------------------------
    # โหมดที่ 1: บริการที่ต้องมีแพทย์
    # ------------------------------------------------------------------
    def _doctor_slots(
        self, target_date: date, not_before: datetime | None
    ) -> list[TimeInterval]:
        free_time = self._doctor_free_time(target_date)
        return generate_slot_starts(
            free_time,
            duration_minutes=self.service_type.duration_minutes,
            step_minutes=self.clinic.slot_interval_minutes,
            not_before=not_before,
        )

    def _doctor_free_time(self, target_date: date, exclude_appointment_id: int | None = None) -> IntervalSet:
        """เวลาว่างของแพทย์หลังหักเวลาที่ถูกบล็อกและคิวที่จองไว้แล้ว"""
        assert self.doctor is not None  # ถูกการันตีโดยผู้เรียก

        schedule_free_time = DoctorAvailabilityService(self.doctor).free_intervals_on(target_date)
        booked = self._booked_intervals(
            self._doctor_appointments_on(target_date, exclude_appointment_id)
        )
        return schedule_free_time.subtract(booked)

    def _doctor_appointments_on(
        self, target_date: date, exclude_appointment_id: int | None = None
    ):
        day_start, day_end = local_day_bounds(target_date, self.timezone_name)
        queryset = (
            Appointment.objects.filter(doctor=self.doctor)
            .occupying()
            .overlapping(day_start, day_end)
        )
        if exclude_appointment_id:
            queryset = queryset.exclude(pk=exclude_appointment_id)
        return queryset

    def _is_doctor_slot_available(
        self, interval: TimeInterval, exclude_appointment_id: int | None
    ) -> bool:
        target_date = local_date_of(interval.start, self.timezone_name)
        free_time = self._doctor_free_time(target_date, exclude_appointment_id)
        return free_time.contains_interval(interval)

    # ------------------------------------------------------------------
    # โหมดที่ 2: บริการที่ไม่ต้องมีแพทย์ (จำกัดด้วยเพดานของสาขา)
    # ------------------------------------------------------------------
    def _capacity_based_slots(
        self, target_date: date, not_before: datetime | None
    ) -> list[TimeInterval]:
        opening_hours = IntervalSet([self.clinic.opening_interval_on(target_date)])
        candidate_slots = generate_slot_starts(
            opening_hours,
            duration_minutes=self.service_type.duration_minutes,
            step_minutes=self.clinic.slot_interval_minutes,
            not_before=not_before,
        )
        booked = list(self._capacity_appointments_on(target_date))
        capacity = self.clinic.non_doctor_service_capacity

        return [
            slot
            for slot in candidate_slots
            if self._count_overlaps(slot, booked) < capacity
        ]

    def _capacity_appointments_on(self, target_date: date, exclude_appointment_id: int | None = None):
        """
        คิวของบริการที่ไม่ต้องมีแพทย์ในสาขานี้

        นับรวมทุกบริการที่ไม่ใช้แพทย์ เพราะใช้ทรัพยากรหน้างานชุดเดียวกัน (เตียง/เจ้าหน้าที่)
        """
        day_start, day_end = local_day_bounds(target_date, self.timezone_name)
        queryset = (
            Appointment.objects.filter(clinic=self.clinic, doctor__isnull=True)
            .occupying()
            .overlapping(day_start, day_end)
        )
        if exclude_appointment_id:
            queryset = queryset.exclude(pk=exclude_appointment_id)
        return queryset

    def _is_capacity_slot_available(
        self, interval: TimeInterval, exclude_appointment_id: int | None
    ) -> bool:
        target_date = local_date_of(interval.start, self.timezone_name)
        booked = list(self._capacity_appointments_on(target_date, exclude_appointment_id))
        return self._count_overlaps(interval, booked) < self.clinic.non_doctor_service_capacity

    # ------------------------------------------------------------------
    # helper
    # ------------------------------------------------------------------
    @staticmethod
    def _booked_intervals(appointments: Iterable[Appointment]) -> list[TimeInterval]:
        return [appointment.interval for appointment in appointments]

    @staticmethod
    def _count_overlaps(slot: TimeInterval, appointments: Iterable[Appointment]) -> int:
        return sum(1 for appointment in appointments if appointment.interval.overlaps_with(slot))

    def _earliest_bookable_moment(self, target_date: date) -> datetime | None:
        """
        เวลาเริ่มต้นที่ยังจองได้ของวันนั้น

        วันในอดีต = จองไม่ได้เลย, วันนี้ = จองได้ตั้งแต่ "ตอนนี้" เป็นต้นไป
        """
        now = timezone.now()
        today = local_date_of(now, self.timezone_name)

        if target_date < today:
            # คืนเวลาที่ไกลกว่าทุก slot ของวันนั้น เพื่อให้ผลลัพธ์เป็นรายการว่าง
            return local_day_bounds(target_date, self.timezone_name)[1]
        if target_date == today:
            return now
        return None


class AppointmentBookingService:
    """
    สร้าง/เลื่อน/ยกเลิกคิว พร้อมกันคิวชนและกัน overbook

    การกัน race condition ตอนจองพร้อมกันใช้สองชั้น:
    1) ล็อกแถวของ "ทรัพยากร" ที่ถูกจอง (แพทย์ หรือสาขากรณีบริการที่ไม่ใช้แพทย์)
       ด้วย select_for_update ทำให้การจองของทรัพยากรเดียวกันเข้าคิวทีละราย
    2) exclusion constraint ระดับ PostgreSQL (ดู migration ของ app นี้)
       เป็นตาข่ายรองสุดท้ายไม่ให้คิวซ้อนกันหลุดลงฐานข้อมูลได้เลย
    """

    def __init__(self, clinic: Clinic, performed_by=None) -> None:
        self.clinic = clinic
        self.performed_by = performed_by

    # ------------------------------------------------------------------
    def book(
        self,
        *,
        patient: Patient,
        service_type: ServiceType,
        scheduled_start: datetime,
        doctor: Doctor | None = None,
        source: str = AppointmentSource.STAFF_CREATED,
        note: str = "",
    ) -> Appointment:
        """จองคิวใหม่ — คืน Appointment ที่บันทึกแล้ว หรือ raise ถ้าเวลาไม่ว่างจริง"""
        interval = self._build_interval(service_type, scheduled_start)

        with transaction.atomic():
            self._lock_resource(doctor)
            availability = SlotAvailabilityService(self.clinic, service_type, doctor)

            if not availability.is_slot_available(interval):
                raise SlotUnavailableError(
                    "ช่วงเวลาที่เลือกไม่ว่างแล้ว กรุณาเลือกเวลาอื่นหรือแพทย์ท่านอื่น",
                    details={
                        "requested_start": interval.start.isoformat(),
                        "requested_end": interval.end.isoformat(),
                    },
                )

            appointment = Appointment(
                patient=patient,
                doctor=doctor,
                service_type=service_type,
                clinic=self.clinic,
                scheduled_start=interval.start,
                scheduled_end=interval.end,
                source=source,
                note=note,
                created_by=self.performed_by,
            )
            self._save_guarding_overlap(appointment)

        logger.info(
            "สร้างคิวใหม่ #%s สาขา %s เวลา %s", appointment.pk, self.clinic.code, interval.start
        )
        return appointment

    def book_walk_in(
        self,
        *,
        patient: Patient,
        service_type: ServiceType,
        doctor: Doctor | None = None,
        note: str = "",
        preferred_start: datetime | None = None,
    ) -> Appointment:
        """
        เพิ่มคิว walk-in ให้เร็วที่สุดเท่าที่ "มีเวลาว่างจริง"

        ถ้าไม่มี slot ว่างเลย จะ raise SlotUnavailableError — ห้ามยัดคิวเกิน capacity
        ไม่ว่ากรณีใด (ข้อกำหนดข้อ 5.2/11)
        """
        availability = SlotAvailabilityService(self.clinic, service_type, doctor)
        search_from = preferred_start or timezone.now()

        slot = availability.find_next_available_slot(search_from, search_days=1)
        if slot is None:
            raise SlotUnavailableError(
                "วันนี้ไม่มีช่วงเวลาว่างเหลือแล้ว กรุณาเลือกแพทย์ท่านอื่นหรือนัดเป็นวันอื่น",
                details={"searched_from": search_from.isoformat()},
            )

        return self.book(
            patient=patient,
            service_type=service_type,
            scheduled_start=slot.start,
            doctor=doctor,
            source=AppointmentSource.WALK_IN,
            note=note,
        )

    def reschedule(
        self,
        appointment: Appointment,
        *,
        new_start: datetime,
        new_doctor: Doctor | None = None,
    ) -> Appointment:
        """เลื่อน/สลับเวลาคิว (หน้าจอ drag-and-drop เรียกผ่าน endpoint นี้)"""
        if appointment.status in {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED}:
            raise BookingConflictError("คิวที่เสร็จสิ้นหรือยกเลิกแล้วเลื่อนเวลาไม่ได้")

        doctor = new_doctor if new_doctor is not None else appointment.doctor
        interval = self._build_interval(appointment.service_type, new_start)

        with transaction.atomic():
            self._lock_resource(doctor)
            availability = SlotAvailabilityService(self.clinic, appointment.service_type, doctor)

            if not availability.is_slot_available(interval, exclude_appointment_id=appointment.pk):
                raise SlotUnavailableError(
                    "เลื่อนไปเวลานี้ไม่ได้ เพราะไม่มีช่วงเวลาว่างจริง",
                    details={"requested_start": interval.start.isoformat()},
                )

            appointment.doctor = doctor
            appointment.scheduled_start = interval.start
            appointment.scheduled_end = interval.end
            self._save_guarding_overlap(
                appointment,
                update_fields=["doctor", "scheduled_start", "scheduled_end", "updated_at"],
            )

        logger.info("เลื่อนคิว #%s ไปเป็น %s", appointment.pk, interval.start)
        return appointment

    def change_status(self, appointment: Appointment, new_status: str) -> Appointment:
        """เปลี่ยนสถานะคิวตาม state machine ที่กำหนดไว้ใน model"""
        appointment.apply_status(new_status)
        appointment.save(
            update_fields=[
                "status",
                "checked_in_at",
                "started_at",
                "completed_at",
                "updated_at",
            ]
        )
        return appointment

    def cancel(self, appointment: Appointment, reason: str = "") -> Appointment:
        """ยกเลิกคิว — เวลาที่ว่างคืนจะถูกนำไปเสนอให้คิวอื่นทันที"""
        appointment.apply_status(AppointmentStatus.CANCELLED)
        appointment.cancelled_reason = reason[:255]
        appointment.save(update_fields=["status", "cancelled_reason", "updated_at"])
        return appointment

    # ------------------------------------------------------------------
    @staticmethod
    def _save_guarding_overlap(
        appointment: Appointment, *, update_fields: list[str] | None = None
    ) -> None:
        """
        บันทึกคิว โดยแปลงการปฏิเสธของ exclusion constraint ให้เป็น error ที่ผู้ใช้เข้าใจได้

        ปกติ `is_slot_available()` กรองคิวชนออกไปก่อนแล้ว แต่บน PostgreSQL ยังมี
        exclusion constraint เป็นตาข่ายรองสุดท้าย ถ้าชั้นนั้นทำงาน (เช่นมีโค้ดใหม่ในอนาคต
        เรียก service นี้โดยไม่ได้ล็อกทรัพยากร) เราต้องตอบ 409 ไม่ใช่ 500

        ต้องห่อด้วย `transaction.atomic()` ซ้อนอีกชั้นเพื่อสร้าง savepoint —
        ถ้าจับ IntegrityError โดยไม่มี savepoint transaction ทั้งก้อนจะใช้งานต่อไม่ได้
        """
        try:
            with transaction.atomic():
                appointment.full_clean()
                appointment.save(update_fields=update_fields)
        except IntegrityError as exc:
            raise BookingConflictError(
                "ช่วงเวลานี้เพิ่งถูกจองไปพอดี กรุณาเลือกเวลาอื่น",
                details={"scheduled_start": appointment.scheduled_start.isoformat()},
            ) from exc

    def _build_interval(self, service_type: ServiceType, scheduled_start: datetime) -> TimeInterval:
        """
        คำนวณเวลาสิ้นสุดจากระยะเวลาของบริการเสมอ

        ไม่รับ `scheduled_end` จาก client เพื่อไม่ให้เกิดคิวที่ยาว/สั้นกว่าบริการจริง
        """
        return TimeInterval(
            scheduled_start, scheduled_start + timedelta(minutes=service_type.duration_minutes)
        )

    def _lock_resource(self, doctor: Doctor | None) -> None:
        """
        ล็อกทรัพยากรที่กำลังจะถูกจอง เพื่อให้การจองพร้อมกันเข้าคิวทีละราย

        ต้องเรียกภายใน transaction เท่านั้น — ล็อกจะถูกปล่อยเมื่อ commit/rollback
        """
        if doctor is not None:
            Doctor.objects.select_for_update().get(pk=doctor.pk)
        else:
            Clinic.objects.select_for_update().get(pk=self.clinic.pk)
