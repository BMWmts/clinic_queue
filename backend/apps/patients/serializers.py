"""Serializer ของคนไข้และโน้ต"""
from __future__ import annotations

from rest_framework import serializers

from apps.patients.models import Patient, PatientNote


class PatientSerializer(serializers.ModelSerializer):
    """ข้อมูลคนไข้สำหรับแสดงผลและแก้ไข (patient_code ระบบสร้างให้ ห้ามแก้)"""

    full_name = serializers.CharField(read_only=True)
    home_clinic_name = serializers.CharField(source="home_clinic.name", read_only=True)
    pinned_notes = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "patient_code",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "date_of_birth",
            "gender",
            "home_clinic",
            "home_clinic_name",
            "is_active",
            "pinned_notes",
            "created_at",
        ]
        read_only_fields = ["id", "patient_code", "home_clinic", "created_at"]

    def get_pinned_notes(self, patient: Patient) -> list[str]:
        """โน้ตที่ปักหมุดไว้ (เช่น ประวัติแพ้ยา) เพื่อให้หน้าคิวเตือนเจ้าหน้าที่ทันที"""
        return [note.note_text for note in patient.notes.filter(is_pinned=True)[:5]]


class PatientNoteSerializer(serializers.ModelSerializer):
    """โน้ตของคนไข้ — ผู้บันทึกและเวลามาจาก backend เสมอ"""

    created_by_name = serializers.CharField(source="created_by.full_name", read_only=True, default=None)

    class Meta:
        model = PatientNote
        fields = [
            "id",
            "patient",
            "appointment",
            "note_text",
            "is_pinned",
            "created_by_name",
            "created_at",
        ]
        read_only_fields = ["id", "patient", "created_by_name", "created_at"]

    def validate_note_text(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("ข้อความโน้ตต้องไม่ว่าง")
        return cleaned
