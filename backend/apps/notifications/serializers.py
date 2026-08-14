"""Serializer ของบันทึกการส่ง SMS"""
from rest_framework import serializers

from apps.notifications.models import SMSLog


class SMSLogSerializer(serializers.ModelSerializer):
    """
    แสดงบันทึกการส่ง — เบอร์โทรถูกปิดบังบางส่วนตามข้อกำหนดเรื่องข้อมูลอ่อนไหว
    """

    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    masked_phone = serializers.CharField(source="patient.masked_phone", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = SMSLog
        fields = [
            "id",
            "clinic",
            "patient",
            "patient_name",
            "masked_phone",
            "appointment",
            "kind",
            "kind_display",
            "message",
            "status",
            "status_display",
            "provider",
            "error_message",
            "sent_at",
            "created_at",
        ]
        read_only_fields = fields
