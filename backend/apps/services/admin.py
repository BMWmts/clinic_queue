from django.contrib import admin

from apps.services.models import ServiceType


@admin.register(ServiceType)
class ServiceTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "category", "duration_minutes", "price", "requires_doctor", "is_active"]
    list_filter = ["category", "requires_doctor", "is_active"]
    search_fields = ["name"]
