"use client";

/**
 * กล่องจองคิวล่วงหน้า (ใช้ได้ทั้งจากหน้าปฏิทินและหน้าประวัติคนไข้)
 *
 * ขั้นตอน: เลือกคนไข้ → เลือกบริการ/แพทย์/วัน → ระบบแสดงเฉพาะเวลาที่ว่างจริง → ยืนยัน
 * ทุกครั้งที่กดยืนยัน backend จะตรวจซ้ำอีกรอบ ถ้ามีคนแย่งจองไปก่อนจะได้ 409 และหน้าจอรีเฟรชเวลาว่างให้
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, patientApi, schedulingApi, serviceApi } from "@/lib/api";
import { formatTime, todayIsoDate } from "@/lib/format";
import { Alert, Button, Field, LoadingRow, Modal, Select, TextInput } from "@/components/ui";
import type { Appointment, AvailableSlot, Doctor, Patient, ServiceType } from "@/types/api";

interface BookingDialogProps {
  doctors: Doctor[];
  /** สาขาที่กำลังทำงานด้วย — จำเป็นสำหรับ Super Admin ที่ไม่ได้สังกัดสาขาใด */
  clinicId: number | null;
  initialPatient?: Patient | null;
  initialDate?: string;
  initialDoctorId?: number | null;
  onClose: () => void;
  onBooked: (appointment: Appointment) => void;
}

export function BookingDialog({
  doctors,
  clinicId,
  initialPatient = null,
  initialDate,
  initialDoctorId = null,
  onClose,
  onBooked,
}: BookingDialogProps) {
  const [services, setServices] = useState<ServiceType[]>([]);
  const [serviceId, setServiceId] = useState<number | null>(null);
  const [doctorId, setDoctorId] = useState<number | null>(initialDoctorId);
  const [targetDate, setTargetDate] = useState(initialDate ?? todayIsoDate());
  const [note, setNote] = useState("");

  const [patient, setPatient] = useState<Patient | null>(initialPatient);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<Patient[]>([]);

  const [slots, setSlots] = useState<AvailableSlot[]>([]);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    serviceApi
      .list(true)
      .then((page) => setServices(page.results))
      .catch(() => setServices([]));
  }, []);

  const selectedService = services.find((service) => service.id === serviceId) ?? null;
  const requiresDoctor = selectedService?.requires_doctor ?? true;

  const loadSlots = useCallback(async () => {
    if (!serviceId || (requiresDoctor && !doctorId)) {
      setSlots([]);
      return;
    }

    setIsLoadingSlots(true);
    setErrorMessage(null);
    try {
      const response = await schedulingApi.availableSlots({
        service_id: serviceId,
        date: targetDate,
        doctor_id: requiresDoctor ? doctorId ?? undefined : undefined,
        clinic_id: clinicId ?? undefined,
      });
      setSlots(response.slots);
    } catch (error) {
      setSlots([]);
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดเวลาว่างไม่สำเร็จ");
    } finally {
      setIsLoadingSlots(false);
    }
  }, [serviceId, doctorId, targetDate, requiresDoctor, clinicId]);

  useEffect(() => {
    void loadSlots();
  }, [loadSlots]);

  const handleSearch = async () => {
    if (searchTerm.trim().length < 2) return;
    try {
      setSearchResults(await patientApi.search(searchTerm.trim()));
    } catch {
      setSearchResults([]);
    }
  };

  const handleBook = async (slot: AvailableSlot) => {
    if (!patient || !serviceId) {
      setErrorMessage("กรุณาเลือกคนไข้และบริการก่อน");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const appointment = await schedulingApi.book({
        patient: patient.id,
        service_type: serviceId,
        doctor: requiresDoctor ? doctorId : null,
        scheduled_start: slot.start,
        note: note.trim(),
        clinic_id: clinicId ?? undefined,
      });
      onBooked(appointment);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "จองคิวไม่สำเร็จ");
      void loadSlots();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal title="จองคิวล่วงหน้า" onClose={onClose}>
      <div className="space-y-4">
        {errorMessage && <Alert>{errorMessage}</Alert>}

        <div className="rounded-lg border border-slate-200 p-3">
          <p className="mb-2 text-sm font-medium text-slate-700">คนไข้</p>
          {patient ? (
            <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
              <div>
                <p className="text-sm font-medium text-slate-800">{patient.full_name}</p>
                <p className="text-xs text-slate-500">
                  {patient.patient_code} · {patient.phone}
                </p>
              </div>
              <Button variant="ghost" onClick={() => setPatient(null)}>
                เปลี่ยน
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex gap-2">
                <TextInput
                  placeholder="ค้นหาด้วยเบอร์โทร / ชื่อ / รหัสคนไข้"
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      void handleSearch();
                    }
                  }}
                />
                <Button variant="secondary" onClick={() => void handleSearch()}>
                  ค้นหา
                </Button>
              </div>
              <ul className="max-h-40 space-y-1 overflow-y-auto">
                {searchResults.map((result) => (
                  <li key={result.id}>
                    <button
                      type="button"
                      onClick={() => setPatient(result)}
                      className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50"
                    >
                      {result.full_name}
                      <span className="ml-2 text-xs text-slate-500">
                        {result.patient_code} · {result.phone}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="บริการ">
            <Select
              value={serviceId ?? ""}
              onChange={(event) => setServiceId(event.target.value ? Number(event.target.value) : null)}
            >
              <option value="">เลือกบริการ</option>
              {services.map((service) => (
                <option key={service.id} value={service.id}>
                  {service.name} ({service.duration_minutes} นาที)
                </option>
              ))}
            </Select>
          </Field>

          <Field label="แพทย์" hint={requiresDoctor ? "บริการนี้ต้องระบุแพทย์" : "บริการนี้ไม่ต้องใช้แพทย์"}>
            <Select
              value={doctorId ?? ""}
              onChange={(event) => setDoctorId(event.target.value ? Number(event.target.value) : null)}
              disabled={!requiresDoctor}
            >
              <option value="">เลือกแพทย์</option>
              {doctors.map((doctor) => (
                <option key={doctor.id} value={doctor.id}>
                  {doctor.display_name}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="วันที่">
            <TextInput
              type="date"
              value={targetDate}
              min={todayIsoDate()}
              onChange={(event) => setTargetDate(event.target.value)}
            />
          </Field>

          <Field label="โน้ตสั้น">
            <TextInput value={note} onChange={(event) => setNote(event.target.value)} maxLength={255} />
          </Field>
        </div>

        <div>
          <p className="mb-2 text-sm font-medium text-slate-700">เวลาที่ว่างจริง</p>
          {!serviceId || (requiresDoctor && !doctorId) ? (
            <Alert tone="info">เลือกบริการและแพทย์ก่อน ระบบจึงจะคำนวณเวลาว่างให้</Alert>
          ) : isLoadingSlots ? (
            <LoadingRow label="กำลังคำนวณเวลาว่าง..." />
          ) : slots.length === 0 ? (
            <Alert tone="info">ไม่มีช่วงเวลาว่างในวันที่เลือก กรุณาเลือกวันอื่นหรือแพทย์ท่านอื่น</Alert>
          ) : (
            <div className="grid max-h-56 grid-cols-3 gap-2 overflow-y-auto sm:grid-cols-4">
              {slots.map((slot) => (
                <Button
                  key={slot.start}
                  variant="secondary"
                  disabled={isSubmitting || !patient}
                  onClick={() => void handleBook(slot)}
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
