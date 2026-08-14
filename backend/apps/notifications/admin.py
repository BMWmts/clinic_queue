from django.contrib import admin

from apps.notifications.models import SMSLog


@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ["id", "clinic", "patient", "kind", "status", "sent_at"]
    list_filter = ["clinic", "status", "kind"]
    readonly_fields = ["created_at", "updated_at", "sent_at"]
