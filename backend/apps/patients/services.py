"""
Business logic ของฐานข้อมูลคนไข้ — สร้างรหัสคนไข้ และค้นหา

แยกออกจาก view เพื่อให้หน้าจอ walk-in (apps.queue) เรียกใช้ตัวเดียวกันได้
"""
from __future__ import annotations

import logging
import re
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Max, Q, QuerySet
from django.db.models.functions import Substr

from apps.clinics.models import Clinic
from apps.patients.models import Patient

logger = logging.getLogger(__name__)

MAX_PATIENT_CODE_ATTEMPTS = 5


class PatientCodeGenerator:
    """
    สร้างรหัสคนไข้รูปแบบ `<รหัสสาขา>-<ลำดับ 6 หลัก>` เช่น BKK-000123

    ลำดับนับแยกตามสาขาเพื่อให้พนักงานอ่านแล้วรู้ทันทีว่าเป็นคนไข้ที่ลงทะเบียนที่ไหน
    การชนกันของลำดับจัดการด้วย unique constraint ระดับ DB + retry
    (ไม่ใช้ตารางนับแยกเพื่อลดจุดที่ต้อง lock)
    """

    SEQUENCE_LENGTH = 6

    def __init__(self, clinic: Clinic) -> None:
        self.clinic = clinic

    def next_code(self) -> str:
        prefix = f"{self.clinic.code}-"
        latest_sequence = (
            Patient.objects.filter(patient_code__startswith=prefix)
            .annotate(sequence_part=Substr("patient_code", len(prefix) + 1))
            .aggregate(highest=Max("sequence_part"))
            .get("highest")
        )
        next_number = (int(latest_sequence) if latest_sequence and latest_sequence.isdigit() else 0) + 1
        return f"{prefix}{next_number:0{self.SEQUENCE_LENGTH}d}"


class PatientRegistrationService:
    """สร้าง/ค้นหาคนไข้โดยใช้เบอร์โทรเป็นตัวจับคู่ข้อมูลเดิม"""

    def __init__(self, clinic: Clinic, created_by: Any = None) -> None:
        self.clinic = clinic
        self.created_by = created_by

    def create_patient(self, **fields: Any) -> Patient:
        """
        สร้างคนไข้ใหม่พร้อมรหัสคนไข้ที่ไม่ซ้ำ

        retry เมื่อชนกับรหัสที่เพิ่งถูกใช้โดย transaction อื่น (race condition ตอนลงทะเบียนพร้อมกัน)
        """
        fields.setdefault("home_clinic", self.clinic)
        generator = PatientCodeGenerator(fields["home_clinic"])

        for attempt in range(MAX_PATIENT_CODE_ATTEMPTS):
            try:
                with transaction.atomic():
                    patient = Patient(
                        patient_code=generator.next_code(),
                        created_by=self.created_by,
                        **fields,
                    )
                    patient.full_clean()
                    patient.save()
                    return patient
            except IntegrityError:
                if attempt == MAX_PATIENT_CODE_ATTEMPTS - 1:
                    raise
                logger.warning("รหัสคนไข้ชนกัน กำลังสร้างใหม่ (ครั้งที่ %s)", attempt + 2)

        raise IntegrityError("ไม่สามารถสร้างรหัสคนไข้ที่ไม่ซ้ำได้")

    def find_existing_by_phone(self, phone: str) -> QuerySet[Patient]:
        """หาคนไข้เดิมจากเบอร์โทร (ข้ามสาขา) — ใช้ตอน walk-in เพื่อไม่สร้าง record ซ้ำ"""
        return Patient.objects.filter(phone=phone, is_active=True).select_related("home_clinic")


class PatientSearchService:
    """
    ค้นหาคนไข้จากเบอร์โทร / ชื่อ / รหัสคนไข้

    ค้นข้ามสาขาโดยตั้งใจ (ตามข้อกำหนด): ลูกค้าคนเดียวกันเดินเข้าสาขาไหนก็เจอประวัติเดิม
    """

    PHONE_PATTERN = re.compile(r"^\d{3,10}$")
    CODE_PATTERN = re.compile(r"^[A-Za-z0-9]{2,20}-?\d*$")

    def search(self, raw_query: str, limit: int = 20) -> QuerySet[Patient]:
        query = (raw_query or "").strip()
        if len(query) < 2:
            return Patient.objects.none()

        return (
            Patient.objects.filter(self._build_filter(query), is_active=True)
            .select_related("home_clinic")
            .order_by("first_name", "last_name")[:limit]
        )

    def _build_filter(self, query: str) -> Q:
        """
        เลือกวิธีค้นตามรูปแบบของคำค้น

        ตัวเลขล้วน → ค้นเบอร์โทรแบบขึ้นต้น (ใช้ index ได้)
        มีขีดกลาง/ตัวอักษร+ตัวเลข → น่าจะเป็นรหัสคนไข้
        นอกนั้น → ค้นจากชื่อ-นามสกุล
        """
        if self.PHONE_PATTERN.match(query):
            return Q(phone__startswith=query)

        if "-" in query and self.CODE_PATTERN.match(query):
            return Q(patient_code__istartswith=query)

        return (
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(patient_code__istartswith=query)
        )
