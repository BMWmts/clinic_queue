from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    verbose_name = "โครงสร้างพื้นฐานที่ใช้ร่วมกัน"
