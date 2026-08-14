"""Celery application สำหรับงาน background (ส่ง SMS แจ้งเตือนนัดหมาย)"""
from __future__ import annotations

import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

celery_app = Celery("clinic")
celery_app.config_from_object("django.conf:settings", namespace="CELERY")
celery_app.autodiscover_tasks()

# ตรวจนัดหมายที่ถึงเวลาต้องเตือนทุกชั่วโมง — ตัว task เองจะเลือกเฉพาะนัดที่อยู่ในช่วง
# reminder window และยังไม่เคยส่ง (idempotent) จึงรันถี่ได้โดยไม่ส่งซ้ำ
celery_app.conf.beat_schedule = {
    "queue-appointment-reminders-hourly": {
        "task": "apps.notifications.tasks.queue_appointment_reminders",
        "schedule": crontab(minute=0),
    },
}
