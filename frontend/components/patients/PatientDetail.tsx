"use client";

/**
 * หน้าประวัติคนไข้ — ข้อมูลติดต่อ โน้ตสะสม และประวัติการจองทั้งหมด
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, doctorApi, patientApi } from "@/lib/api";
import { formatDateTime, formatTimeRange } from "@/lib/format";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Field,
  LoadingRow,
  StatusBadge,
  TextInput,
} from "@/components/ui";
import { BookingDialog } from "@/components/booking/BookingDialog";
import { useSession } from "@/lib/hooks/useSession";
import type { Appointment, Doctor, Patient, PatientNote } from "@/types/api";

export function PatientDetail({ patientId }: { patientId: number }) {
  const { activeClinicId } = useSession();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [notes, setNotes] = useState<PatientNote[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isBookingOpen, setIsBookingOpen] = useState(false);

  const loadPatient = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const [history, noteList, doctorPage] = await Promise.all([
        patientApi.history(patientId),
        patientApi.notes(patientId),
        doctorApi.list({ is_active: true }),
      ]);
      setPatient(history.patient);
      setAppointments(history.appointments);
      setNotes(noteList);
      setDoctors(doctorPage.results);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดข้อมูลคนไข้ไม่สำเร็จ");
    } finally {
      setIsLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    void loadPatient();
  }, [loadPatient]);

  if (isLoading) {
    return <LoadingRow />;
  }

  if (errorMessage || !patient) {
    return <Alert>{errorMessage ?? "ไม่พบข้อมูลคนไข้"}</Alert>;
  }

  return (
    <div className="space-y-4">
      <Card
        title={patient.full_name}
        description={`${patient.patient_code} · ${patient.phone} · ลงทะเบียนที่ ${patient.home_clinic_name}`}
        actions={<Button onClick={() => setIsBookingOpen(true)}>+ จองคิวให้คนไข้นี้</Button>}
      >
        <dl className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-slate-500">วันเกิด</dt>
            <dd className="text-slate-800">{patient.date_of_birth ?? "ไม่ระบุ"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">เพศ</dt>
            <dd className="text-slate-800">{patient.gender}</dd>
          </div>
          <div>
            <dt className="text-slate-500">จำนวนครั้งที่มา</dt>
            <dd className="text-slate-800">{appointments.length} ครั้ง</dd>
          </div>
        </dl>
      </Card>

      <NotesSection
        patientId={patientId}
        notes={notes}
        onNoteAdded={(note) => setNotes([note, ...notes])}
      />

      <Card title="ประวัติการจอง" description={`ทั้งหมด ${appointments.length} รายการ`}>
        {appointments.length === 0 ? (
          <EmptyState message="ยังไม่มีประวัติการจอง" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {appointments.map((appointment) => (
              <li key={appointment.id} className="flex flex-wrap items-center justify-between gap-2 py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {formatDateTime(appointment.scheduled_start)} ·{" "}
                    {formatTimeRange(appointment.scheduled_start, appointment.scheduled_end)}
                  </p>
                  <p className="text-xs text-slate-500">
                    {appointment.service_name}
                    {appointment.doctor_name ? ` · ${appointment.doctor_name}` : ""}
                    {` · ${appointment.source_display}`}
                  </p>
                  {appointment.note && (
                    <p className="mt-1 text-xs text-amber-700">📌 {appointment.note}</p>
                  )}
                </div>
                <StatusBadge status={appointment.status} />
              </li>
            ))}
          </ul>
        )}
      </Card>

      {isBookingOpen && (
        <BookingDialog
          doctors={doctors}
          clinicId={activeClinicId}
          initialPatient={patient}
          onClose={() => setIsBookingOpen(false)}
          onBooked={() => {
            setIsBookingOpen(false);
            void loadPatient();
          }}
        />
      )}
    </div>
  );
}

function NotesSection({
  patientId,
  notes,
  onNoteAdded,
}: {
  patientId: number;
  notes: PatientNote[];
  onNoteAdded: (note: PatientNote) => void;
}) {
  const [noteText, setNoteText] = useState("");
  const [isPinned, setIsPinned] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!noteText.trim()) return;

    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      const note = await patientApi.addNote(patientId, noteText.trim(), isPinned);
      onNoteAdded(note);
      setNoteText("");
      setIsPinned(false);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "บันทึกโน้ตไม่สำเร็จ");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card title="โน้ตของคนไข้" description="โน้ตที่ปักหมุดจะแสดงเตือนทุกครั้งที่เปิดคิวคนไข้">
      <form onSubmit={handleSubmit} className="mb-4 space-y-2">
        {errorMessage && <Alert>{errorMessage}</Alert>}
        <Field label="เพิ่มโน้ตใหม่">
          <TextInput
            value={noteText}
            onChange={(event) => setNoteText(event.target.value)}
            placeholder='เช่น "แพ้ยาชา", "ขอหมอคนเดิม"'
          />
        </Field>
        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={isPinned}
              onChange={(event) => setIsPinned(event.target.checked)}
            />
            ปักหมุดโน้ตนี้
          </label>
          <Button type="submit" disabled={isSubmitting || !noteText.trim()}>
            บันทึกโน้ต
          </Button>
        </div>
      </form>

      {notes.length === 0 ? (
        <EmptyState message="ยังไม่มีโน้ต" />
      ) : (
        <ul className="divide-y divide-slate-100">
          {notes.map((note) => (
            <li key={note.id} className="py-2">
              <p className="text-sm text-slate-800">
                {note.is_pinned && <span className="mr-1">📌</span>}
                {note.note_text}
              </p>
              <p className="text-xs text-slate-400">
                {note.created_by_name ?? "ระบบ"} · {formatDateTime(note.created_at)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
