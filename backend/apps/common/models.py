"""Abstract base model ที่ใช้ซ้ำทุก app (audit trail ตาม non-functional requirement)"""
from __future__ import annotations

from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """เก็บเวลาสร้าง/แก้ไขล่าสุดของทุก record สำคัญ"""

    created_at = models.DateTimeField("สร้างเมื่อ", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("แก้ไขล่าสุดเมื่อ", auto_now=True)

    class Meta:
        abstract = True


class AuditableModel(TimeStampedModel):
    """
    เพิ่ม `created_by` เพื่อให้ trace ได้ว่าใครเป็นคนสร้าง record

    ใช้ SET_NULL เพื่อไม่ให้ประวัติคิวหายไปเมื่อผู้ใช้ถูกลบออกจากระบบ
    """

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="สร้างโดย",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
    )

    class Meta:
        abstract = True
