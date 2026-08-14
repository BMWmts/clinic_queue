from django.contrib import admin

from apps.doctors.models import Doctor, DoctorSchedule, TimeBlock


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ["display_name", "clinic", "specialties", "is_active"]
    list_filter = ["clinic", "is_active"]
    search_fields = ["display_name", "user__email"]


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ["doctor", "day_of_week", "start_time", "end_time", "is_active"]
    list_filter = ["clinic", "day_of_week", "is_active"]


@admin.register(TimeBlock)
class TimeBlockAdmin(admin.ModelAdmin):
    list_display = ["doctor", "start_datetime", "end_datetime", "reason", "is_recurring"]
    list_filter = ["clinic", "reason", "is_recurring"]
