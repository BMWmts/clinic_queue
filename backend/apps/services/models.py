"""
ประเภทบริการของคลินิก (เช่น ฉีดโบลดริ้วรอย, ดริปผิว)

เป็นแคตตาล็อกกลางที่ใช้ร่วมกันทุกสาขา เพื่อให้คนไข้ที่ย้ายสาขาได้รับบริการ
ชื่อเดียวกันและรายงานรวมข้ามสาขาเทียบกันได้

`duration_minutes` เป็นตัวกำหนดความยาวของคิว — ระบบใช้ค่านี้คำนวณ
`scheduled_end` ของ Appointment เสมอ ไม่ให้ผู้ใช้กรอกเองเพื่อกันคิวเหลื่อม
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.models import TimeStampedModel


class ServiceType(TimeStampedModel):
    """บริการหนึ่งรายการพร้อมระยะเวลามาตรฐาน"""

    name = models.CharField("ชื่อบริการ", max_length=150, unique=True)
    category = models.CharField("หมวดหมู่", max_length=80, blank=True, db_index=True)
    description = models.TextField("รายละเอียด", blank=True)

    duration_minutes = models.PositiveSmallIntegerField(
        "ระยะเวลาที่ใช้ (นาที)",
        validators=[MinValueValidator(5), MaxValueValidator(600)],
    )
    price = models.DecimalField(
        "ราคา (บาท)", max_digits=10, decimal_places=2, default=Decimal("0.00"),
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    requires_doctor = models.BooleanField(
        "ต้องมีแพทย์", default=True,
        help_text="ถ้าไม่ต้องใช้แพทย์ ระบบจะจำกัดคิวด้วยเพดานของสาขาแทนตารางแพทย์",
    )
    is_active = models.BooleanField("เปิดให้จอง", default=True)

    class Meta:
        verbose_name = "ประเภทบริการ"
        verbose_name_plural = "ประเภทบริการ"
        ordering = ["category", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.duration_minutes} นาที)"
