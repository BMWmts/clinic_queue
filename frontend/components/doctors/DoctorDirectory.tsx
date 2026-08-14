"use client";

/**
 * หน้ารายชื่อแพทย์ + รับแพทย์ใหม่เข้าทำงาน
 *
 * การรับแพทย์ใหม่ยิงไปที่ POST /api/doctors/ ครั้งเดียว แล้ว backend สร้างทั้ง
 * บัญชีล็อกอินและโปรไฟล์ให้ในทรานแซกชันเดียว (ดู DoctorRegistrationService)
 */
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ApiError, doctorApi } from "@/lib/api";
import { useSession } from "@/lib/hooks/useSession";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Field,
  LoadingRow,
  Modal,
  TextInput,
} from "@/components/ui";
import type { Doctor, DoctorSchedule } from "@/types/api";

const DOCTOR_COLOR_CHOICES = ["#2563eb", "#16a34a", "#db2777", "#f59e0b", "#7c3aed", "#0891b2"];

export function DoctorDirectory() {
  const { activeClinicId, needsClinicSelection } = useSession();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [scheduleCounts, setScheduleCounts] = useState<Record<number, number>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const loadDoctors = useCallback(async () => {
    if (needsClinicSelection) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const page = await doctorApi.list({ clinic_id: activeClinicId ?? undefined });
      setDoctors(page.results);

      // นับจำนวนช่วงเวลาออกตรวจของแต่ละคน เพื่อเตือนคนที่ยังไม่ได้ตั้งตาราง
      const schedulePage = await doctorApi.schedules();
      const counts: Record<number, number> = {};
      schedulePage.results.forEach((schedule: DoctorSchedule) => {
        if (schedule.is_active) {
          counts[schedule.doctor] = (counts[schedule.doctor] ?? 0) + 1;
        }
      });
      setScheduleCounts(counts);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดรายชื่อแพทย์ไม่สำเร็จ");
    } finally {
      setIsLoading(false);
    }
  }, [activeClinicId, needsClinicSelection]);

  useEffect(() => {
    void loadDoctors();
  }, [loadDoctors]);

  if (needsClinicSelection) {
    return (
      <Alert tone="info">
        กรุณาเลือกสาขาที่ต้องการดูแลจากแถบด้านบนขวา ระบบจึงจะแสดงรายชื่อแพทย์ของสาขานั้นให้
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      {errorMessage && <Alert>{errorMessage}</Alert>}

      <Card
        title="แพทย์ในสาขา"
        description={`ทั้งหมด ${doctors.length} ท่าน`}
        actions={<Button onClick={() => setIsCreateOpen(true)}>+ รับแพทย์ใหม่</Button>}
      >
        {isLoading ? (
          <LoadingRow />
        ) : doctors.length === 0 ? (
          <EmptyState message="ยังไม่มีแพทย์ในสาขานี้ — กดปุ่ม 'รับแพทย์ใหม่' เพื่อเริ่มต้น" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {doctors.map((doctor) => {
              const scheduleCount = scheduleCounts[doctor.id] ?? 0;
              return (
                <li key={doctor.id} className="py-3">
                  <Link
                    href={`/doctors/${doctor.id}`}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg px-2 py-1 hover:bg-slate-50"
                  >
                    <div>
                      <p className="flex items-center gap-2 font-medium text-slate-800">
                        <span
                          className="inline-block h-3 w-3 rounded-full"
                          style={{ backgroundColor: doctor.color }}
                        />
                        {doctor.display_name}
                        {!doctor.is_active && (
                          <span className="rounded bg-slate-200 px-1.5 py-0.5 text-xs text-slate-600">
                            ปิดใช้งาน
                          </span>
                        )}
                      </p>
                      <p className="text-xs text-slate-500">
                        {doctor.email}
                        {doctor.specialties ? ` · ${doctor.specialties}` : ""}
                      </p>
                      {scheduleCount === 0 ? (
                        <p className="mt-1 text-xs text-amber-700">
                          ⚠ ยังไม่ได้ตั้งตารางออกตรวจ — ยังจองคิวให้แพทย์ท่านนี้ไม่ได้
                        </p>
                      ) : (
                        <p className="mt-1 text-xs text-slate-400">
                          ตารางออกตรวจ {scheduleCount} ช่วงเวลา/สัปดาห์
                        </p>
                      )}
                    </div>
                    <span className="text-sm text-brand-600">จัดการตาราง →</span>
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </Card>

      {isCreateOpen && (
        <NewDoctorDialog
          clinicId={activeClinicId}
          onClose={() => setIsCreateOpen(false)}
          onCreated={() => {
            setIsCreateOpen(false);
            void loadDoctors();
          }}
        />
      )}
    </div>
  );
}

function NewDoctorDialog({
  clinicId,
  onClose,
  onCreated,
}: {
  clinicId: number | null;
  onClose: () => void;
  onCreated: (doctor: Doctor) => void;
}) {
  const [form, setForm] = useState({
    full_name: "",
    display_name: "",
    email: "",
    phone: "",
    password: "",
    specialties: "",
    color: DOCTOR_COLOR_CHOICES[0],
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const doctor = await doctorApi.create({
        email: form.email.trim(),
        full_name: form.full_name.trim(),
        // เว้นว่างได้ — ระบบจะใช้ชื่อเต็มเป็นชื่อที่แสดงบนปฏิทินแทน
        display_name: form.display_name.trim() || form.full_name.trim(),
        password: form.password,
        phone: form.phone.trim(),
        specialties: form.specialties.trim(),
        color: form.color,
        clinic_id: clinicId ?? undefined,
      });
      onCreated(doctor);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "รับแพทย์ใหม่ไม่สำเร็จ");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal title="รับแพทย์ใหม่เข้าทำงาน" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {errorMessage && <Alert>{errorMessage}</Alert>}

        <Alert tone="info">
          ระบบจะสร้างบัญชีสำหรับให้แพทย์ล็อกอินเข้าดูคิวของตัวเองด้วย
          หลังบันทึกแล้วอย่าลืมตั้งตารางออกตรวจ ไม่เช่นนั้นจะยังจองคิวให้ไม่ได้
        </Alert>

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="ชื่อ-สกุล (ตามบัญชีผู้ใช้)">
            <TextInput
              value={form.full_name}
              onChange={(event) => setForm({ ...form, full_name: event.target.value })}
              placeholder="พญ. สมหญิง ใจดี"
              required
            />
          </Field>

          <Field label="ชื่อที่แสดงบนปฏิทิน" hint="เว้นว่างได้ จะใช้ชื่อ-สกุลแทน">
            <TextInput
              value={form.display_name}
              onChange={(event) => setForm({ ...form, display_name: event.target.value })}
              placeholder="พญ. สมหญิง"
            />
          </Field>

          <Field label="อีเมล (ใช้ล็อกอิน)">
            <TextInput
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
              required
            />
          </Field>

          <Field label="รหัสผ่านเริ่มต้น" hint="อย่างน้อย 8 ตัวอักษร ให้แพทย์เปลี่ยนเองภายหลัง">
            <TextInput
              type="password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
              minLength={8}
              required
            />
          </Field>

          <Field label="เบอร์โทร">
            <TextInput
              value={form.phone}
              onChange={(event) => setForm({ ...form, phone: event.target.value })}
              pattern="0\d{8,9}"
              placeholder="0812345678"
            />
          </Field>

          <Field label="ความเชี่ยวชาญ">
            <TextInput
              value={form.specialties}
              onChange={(event) => setForm({ ...form, specialties: event.target.value })}
              placeholder="ผิวหนังและความงาม"
            />
          </Field>
        </div>

        <Field label="สีประจำตัวในปฏิทิน">
          <div className="flex gap-2">
            {DOCTOR_COLOR_CHOICES.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setForm({ ...form, color })}
                aria-label={`เลือกสี ${color}`}
                className={`h-8 w-8 rounded-full border-2 transition ${
                  form.color === color ? "border-slate-800" : "border-transparent"
                }`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        </Field>

        <div className="flex justify-end gap-2">
          <Button variant="secondary" type="button" onClick={onClose}>
            ยกเลิก
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "กำลังบันทึก..." : "บันทึกแพทย์"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
