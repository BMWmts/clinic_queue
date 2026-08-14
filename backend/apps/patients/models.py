"""
ฐานข้อมูลคนไข้

คนไข้หนึ่งคนใช้ record เดียวทั้งเครือ (ค้นหา/จองข้ามสาขาได้) โดยมี `home_clinic`
บอกสาขาที่ลงทะเบียนครั้งแรก และใช้ "เบอร์โทร" เป็นตัวจับคู่ข้อมูลเดิม
เพื่อไม่ให้เกิด record ซ้ำเมื่อลูกค้าเดินเข้าอีกสาขาหนึ่ง
"""
from __future__ import annotations

from django.core.validators import RegexValidator
from django.db import models

from apps.common.models import AuditableModel

phone_validator = RegexValidator(
    regex=r"^0\d{8,9}$",
    message="เบอร์โทรต้องเป็นตัวเลข 9-10 หลักและขึ้นต้นด้วย 0 (เช่น 0812345678)",
)


class Gender(models.TextChoices):
    FEMALE = "female", "หญิง"
    MALE = "male", "ชาย"
    OTHER = "other", "อื่น ๆ"
    UNSPECIFIED = "unspecified", "ไม่ระบุ"


class Patient(AuditableModel):
    """ข้อมูลคนไข้/ลูกค้า"""

    patient_code = models.CharField(
        "รหัสคนไข้", max_length=20, unique=True, db_index=True,
        help_text="ระบบสร้างให้อัตโนมัติ เช่น BKK-000123",
    )
    first_name = models.CharField("ชื่อ", max_length=100)
    last_name = models.CharField("นามสกุล", max_length=100, blank=True)
    phone = models.CharField(
        "เบอร์โทร", max_length=10, db_index=True, validators=[phone_validator]
    )
    date_of_birth = models.DateField("วันเกิด", null=True, blank=True)
    gender = models.CharField(
        "เพศ", max_length=15, choices=Gender.choices, default=Gender.UNSPECIFIED
    )

    home_clinic = models.ForeignKey(
        "clinics.Clinic",
        verbose_name="สาขาที่ลงทะเบียน",
        on_delete=models.PROTECT,
        related_name="registered_patients",
    )
    is_active = models.BooleanField("เปิดใช้งาน", default=True)

    class Meta:
        verbose_name = "คนไข้"
        verbose_name_plural = "คนไข้"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone"]),
            models.Index(fields=["last_name", "first_name"]),
        ]
        constraints = [
            # เบอร์โทรเดียวกัน + ชื่อเดียวกัน ถือเป็นคนเดียวกัน กันการสร้างซ้ำจากคนละสาขา
            models.UniqueConstraint(
                fields=["phone", "first_name", "last_name"],
                name="patient_unique_phone_and_name",
            )
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.patient_code})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def masked_phone(self) -> str:
        """
        เบอร์โทรแบบปิดบังบางส่วน — ใช้ในทุกที่ที่ไม่จำเป็นต้องเห็นเบอร์เต็ม
        (เช่น log การส่ง SMS) ตามข้อกำหนดเรื่องข้อมูลอ่อนไหว
        """
        if len(self.phone) < 4:
            return "***"
        return f"{self.phone[:3]}xxx{self.phone[-3:]}"


class PatientNote(AuditableModel):
    """
    โน้ตสะสมของคนไข้ (เช่น "แพ้ยาชา", "ขอหมอคนเดิม")

    ผูกกับ appointment ได้ถ้าโน้ตเกิดจากการมาครั้งนั้น ๆ แต่ไม่บังคับ
    """

    patient = models.ForeignKey(
        Patient, verbose_name="คนไข้", on_delete=models.CASCADE, related_name="notes"
    )
    appointment = models.ForeignKey(
        "scheduling.Appointment",
        verbose_name="การนัดหมายที่เกี่ยวข้อง",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notes",
    )
    note_text = models.TextField("บันทึก")
    is_pinned = models.BooleanField(
        "ปักหมุด", default=False,
        help_text="โน้ตสำคัญที่ต้องเห็นทุกครั้งที่เปิดคิวคนไข้ เช่น ประวัติแพ้ยา",
    )

    class Meta:
        verbose_name = "โน้ตคนไข้"
        verbose_name_plural = "โน้ตคนไข้"
        ordering = ["-is_pinned", "-created_at"]
        indexes = [models.Index(fields=["patient", "-created_at"])]

    def __str__(self) -> str:
        return f"โน้ตของ {self.patient.patient_code}"
