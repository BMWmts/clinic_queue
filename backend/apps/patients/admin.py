from django.contrib import admin

from apps.patients.models import Patient, PatientNote


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ["patient_code", "full_name", "masked_phone", "home_clinic", "is_active"]
    list_filter = ["home_clinic", "gender", "is_active"]
    # ค้นด้วยเบอร์เต็มได้ แต่รายการที่แสดงใช้เบอร์แบบปิดบัง
    search_fields = ["patient_code", "first_name", "last_name", "phone"]


@admin.register(PatientNote)
class PatientNoteAdmin(admin.ModelAdmin):
    list_display = ["patient", "is_pinned", "created_by", "created_at"]
    list_filter = ["is_pinned"]
