"use client";

/**
 * กล่องเลื่อนคิว — เลือกได้เฉพาะช่วงเวลาที่ backend บอกว่าว่างจริงเท่านั้น
 *
 * หน้าจอไม่คำนวณเวลาว่างเอง เพื่อไม่ให้เกิดกรณีที่หน้าจอคิดว่าว่างแต่จริง ๆ ชนกับคิวอื่น
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, queueApi, schedulingApi } from "@/lib/api";
import { formatTime, isoDateOf } from "@/lib/format";
import { Alert, Button, Field, LoadingRow, Modal, Select, TextInput } from "@/components/ui";
import type { Appointment, AvailableSlot, Doctor } from "@/types/api";

interface RescheduleDialogProps {
  appointment: Appointment;
  doctors: Doctor[];
  /** สาขาที่กำลังทำงานด้วย — จำเป็นสำหรับ Super Admin ที่ไม่ได้สังกัดสาขาใด */
  clinicId: number | null;
  onClose: () => void;
  onRescheduled: (appointment: Appointment) => void;
}

export function RescheduleDialog({
  appointment,
  doctors,
  clinicId,
  onClose,
  onRescheduled,
}: RescheduleDialogProps) {
  const [targetDate, setTargetDate] = useState(isoDateOf(new Date(appointment.scheduled_start)));
  const [doctorId, setDoctorId] = useState<number | null>(appointment.doctor);
  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadSlots = useCallback(async () => {
    setIsLoadingSlots(true);
    setErrorMessage(null);
    try {
      const response = await schedulingApi.availableSlots({
        service_id: appointment.service_type,
        date: targetDate,
        doctor_id: doctorId ?? undefined,
        clinic_id: clinicId ?? undefined,
      });
      setSlots(response.slots);
    } catch (error) {
      setSlots([]);
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดเวลาว่างไม่สำเร็จ");
    } finally {
      setIsLoadingSlots(false);
    }
  }, [appointment.service_type, targetDate, doctorId, clinicId]);

  useEffect(() => {
    void loadSlots();
  }, [loadSlots]);

  const handleSelectSlot = async (slot: AvailableSlot) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const updated = await queueApi.reschedule(appointment.id, slot.start, doctorId);
      onRescheduled(updated);
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "เลื่อนคิวไม่สำเร็จ กรุณาเลือกเวลาอื่น",
      );
      // เวลาที่เพิ่งถูกคนอื่นจองไป — โหลดรายการใหม่ให้ตรงกับความจริง
      void loadSlots();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal title={`เลื่อนคิวของ ${appointment.patient_name}`} onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          คิวเดิม: {formatTime(appointment.scheduled_start)} น. · {appointment.service_name}
        </p>

        {errorMessage && <Alert>{errorMessage}</Alert>}

        <div className="grid grid-cols-2 gap-3">
          <Field label="วันที่">
            <TextInput
              type="date"
              value={targetDate}
              onChange={(event) => setTargetDate(event.target.value)}
            />
          </Field>
          <Field label="แพทย์">
            <Select
              value={doctorId ?? ""}
              onChange={(event) => setDoctorId(event.target.value ? Number(event.target.value) : null)}
            >
              <option value="">ไม่ระบุแพทย์</option>
              {doctors.map((doctor) => (
                <option key={doctor.id} value={doctor.id}>
                  {doctor.display_name}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">เวลาที่ว่างจริง</p>
          {isLoadingSlots ? (
            <LoadingRow label="กำลังคำนวณเวลาว่าง..." />
          ) : slots.length === 0 ? (
            <Alert tone="info">
              ไม่มีช่วงเวลาว่างในวันนี้ กรุณาเลือกวันอื่นหรือแพทย์ท่านอื่น
            </Alert>
          ) : (
            <div className="grid max-h-64 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-4">
              {slots.map((slot) => (
                <Button
                  key={slot.start}
                  variant="secondary"
                  disabled={isSubmitting}
                  onClick={() => void handleSelectSlot(slot)}
                >
                  {formatTime(slot.start)}
                </Button>
              ))}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
