"use client";

/**
 * กล่องรับคิว walk-in
 *
 * ระบบจะจัดให้อัตโนมัติในช่วงเวลาว่างที่เร็วที่สุด — ถ้าไม่มีเวลาว่างจริง
 * backend จะปฏิเสธ (409) และหน้าจอจะแจ้งให้เลือกแพทย์ท่านอื่นหรือนัดวันอื่น
 * (ระบบไม่อนุญาตให้แทรกคิวเกินความจุไม่ว่ากรณีใด)
 */
import { useEffect, useState } from "react";

import { ApiError, patientApi, queueApi, serviceApi } from "@/lib/api";
import { formatTimeRange } from "@/lib/format";
import { Alert, Button, Field, Modal, Select, TextInput } from "@/components/ui";
import type { Appointment, Doctor, Patient, ServiceType } from "@/types/api";

interface WalkInDialogProps {
  doctors: Doctor[];
  /** สาขาที่กำลังทำงานด้วย — จำเป็นสำหรับ Super Admin ที่ไม่ได้สังกัดสาขาใด */
  clinicId: number | null;
  onClose: () => void;
  onCreated: (appointment: Appointment) => void;
}

export function WalkInDialog({ doctors, clinicId, onClose, onCreated }: WalkInDialogProps) {
  const [services, setServices] = useState<ServiceType[]>([]);
  const [serviceId, setServiceId] = useState<number | null>(null);
  const [doctorId, setDoctorId] = useState<number | null>(null);
  const [note, setNote] = useState("");

  const [searchTerm, setSearchTerm] = useState("");
  const [searchResults, setSearchResults] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [newPatient, setNewPatient] = useState({ first_name: "", last_name: "", phone: "" });

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

  const handleSearch = async () => {
    if (searchTerm.trim().length < 2) return;
    try {
      setSearchResults(await patientApi.search(searchTerm.trim()));
    } catch {
      setSearchResults([]);
    }
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!serviceId) {
      setErrorMessage("กรุณาเลือกบริการ");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const appointment = await queueApi.walkIn({
        service_type: serviceId,
        clinic_id: clinicId ?? undefined,
        doctor: requiresDoctor ? doctorId : null,
        patient: selectedPatient?.id,
        new_patient: selectedPatient
          ? undefined
          : {
              first_name: newPatient.first_name.trim(),
              last_name: newPatient.last_name.trim(),
              phone: newPatient.phone.trim(),
            },
        note: note.trim(),
      });
      onCreated(appointment);
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "รับคิว walk-in ไม่สำเร็จ กรุณาลองใหม่",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal title="รับคิว Walk-in" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && <Alert>{errorMessage}</Alert>}

        <Field label="บริการ">
          <Select
            value={serviceId ?? ""}
            onChange={(event) => {
              setServiceId(event.target.value ? Number(event.target.value) : null);
              setDoctorId(null);
            }}
            required
          >
            <option value="">เลือกบริการ</option>
            {services.map((service) => (
              <option key={service.id} value={service.id}>
                {service.name} ({service.duration_minutes} นาที)
              </option>
            ))}
          </Select>
        </Field>

        {requiresDoctor && (
          <Field label="แพทย์" hint="บริการนี้ต้องระบุแพทย์">
            <Select
              value={doctorId ?? ""}
              onChange={(event) => setDoctorId(event.target.value ? Number(event.target.value) : null)}
              required
            >
              <option value="">เลือกแพทย์</option>
              {doctors.map((doctor) => (
                <option key={doctor.id} value={doctor.id}>
                  {doctor.display_name}
                </option>
              ))}
            </Select>
          </Field>
        )}

        <div className="rounded-lg border border-slate-200 p-3">
          <p className="mb-2 text-sm font-medium text-slate-700">คนไข้</p>

          {selectedPatient ? (
            <div className="flex items-center justify-between gap-2 rounded-lg bg-slate-50 px-3 py-2">
              <div>
                <p className="text-sm font-medium text-slate-800">{selectedPatient.full_name}</p>
                <p className="text-xs text-slate-500">
                  {selectedPatient.patient_code} · {selectedPatient.phone}
                </p>
              </div>
              <Button variant="ghost" type="button" onClick={() => setSelectedPatient(null)}>
                เปลี่ยน
              </Button>
            </div>
          ) : (
            <div className="space-y-3">
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
                <Button type="button" variant="secondary" onClick={() => void handleSearch()}>
                  ค้นหา
                </Button>
              </div>

              {searchResults.length > 0 && (
                <ul className="max-h-40 space-y-1 overflow-y-auto">
                  {searchResults.map((patient) => (
                    <li key={patient.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedPatient(patient)}
                        className="w-full rounded-lg px-3 py-2 text-left text-sm hover:bg-slate-50"
                      >
                        {patient.full_name}
                        <span className="ml-2 text-xs text-slate-500">
                          {patient.patient_code} · {patient.phone}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}

              <p className="text-xs text-slate-500">หรือกรอกข้อมูลคนไข้ใหม่</p>
              <div className="grid grid-cols-2 gap-2">
                <Field label="ชื่อ">
                  <TextInput
                    value={newPatient.first_name}
                    onChange={(event) =>
                      setNewPatient({ ...newPatient, first_name: event.target.value })
                    }
                    required={!selectedPatient}
                  />
                </Field>
                <Field label="นามสกุล">
                  <TextInput
                    value={newPatient.last_name}
                    onChange={(event) =>
                      setNewPatient({ ...newPatient, last_name: event.target.value })
                    }
                  />
                </Field>
              </div>
              <Field label="เบอร์โทร" hint="ใช้จับคู่กับประวัติเดิม เช่น 0812345678">
                <TextInput
                  value={newPatient.phone}
                  onChange={(event) => setNewPatient({ ...newPatient, phone: event.target.value })}
                  pattern="0\d{8,9}"
                  required={!selectedPatient}
                />
              </Field>
            </div>
          )}
        </div>

        <Field label="โน้ตสั้น" hint='เช่น "แพ้ยาชา"'>
          <TextInput value={note} onChange={(event) => setNote(event.target.value)} maxLength={255} />
        </Field>

        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose}>
            ยกเลิก
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "กำลังจัดคิว..." : "รับคิว"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

/** แสดงช่วงเวลาของคิวที่เพิ่งสร้าง (ใช้ในข้อความยืนยันของหน้าจอที่เรียกใช้) */
export function describeAppointmentTime(appointment: Appointment): string {
  return formatTimeRange(appointment.scheduled_start, appointment.scheduled_end);
}
