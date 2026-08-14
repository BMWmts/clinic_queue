from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.accounts.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """หน้า admin สำหรับตั้งค่าบัญชีเริ่มต้น (งานประจำวันใช้หน้าเว็บของระบบแทน)"""

    ordering = ["email"]
    list_display = ["email", "full_name", "role", "clinic", "is_active"]
    list_filter = ["role", "clinic", "is_active"]
    search_fields = ["email", "full_name"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("ข้อมูลส่วนตัว", {"fields": ("full_name", "phone")}),
        ("สิทธิ์การใช้งาน", {"fields": ("role", "clinic", "is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "clinic", "password1", "password2"),
            },
        ),
    )
