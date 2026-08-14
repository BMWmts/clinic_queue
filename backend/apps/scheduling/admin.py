from django.contrib import admin

from apps.scheduling.models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "clinic",
        "scheduled_start",
        "doctor",
        "service_type",
        "status",
        "source",
    ]
    list_filter = ["clinic", "status", "source", "doctor"]
    search_fields = ["patient__patient_code", "patient__first_name", "patient__last_name"]
    date_hierarchy = "scheduled_start"
    autocomplete_fields = ["patient"]
