from django.apps import AppConfig


class QueueConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.queue"
    label = "clinic_queue"  # เลี่ยงชื่อ label ที่ชนกับคำสงวน/แอปอื่นในอนาคต
    verbose_name = "หน้าจอคิวหน้างาน"
