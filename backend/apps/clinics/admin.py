from django.contrib import admin

from apps.clinics.models import Clinic


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "opening_time", "closing_time", "timezone", "is_active"]
    list_filter = ["is_active", "sms_provider"]
    search_fields = ["name", "code"]
