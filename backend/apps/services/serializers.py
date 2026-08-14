"""Serializer ของประเภทบริการ"""
from rest_framework import serializers

from apps.services.models import ServiceType


class ServiceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceType
        fields = [
            "id",
            "name",
            "category",
            "description",
            "duration_minutes",
            "price",
            "requires_doctor",
            "is_active",
        ]
        read_only_fields = ["id"]
