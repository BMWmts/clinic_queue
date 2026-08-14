"use client";

/**
 * หน้าค้นหา/ลงทะเบียนคนไข้
 *
 * ค้นข้ามสาขาได้ (ลูกค้าคนเดียวกันเดินเข้าได้หลายสาขา) และใช้เบอร์โทรเป็นตัวจับคู่
 * ข้อมูลเดิม เพื่อไม่ให้เกิดประวัติซ้ำ
 */
import { useState } from "react";
import Link from "next/link";

import { ApiError, patientApi } from "@/lib/api";
import { Alert, Button, Card, EmptyState, Field, Select, TextInput } from "@/components/ui";
import type { Patient } from "@/types/api";

export function PatientDirectory() {
  const [searchTerm, setSearchTerm] = useState("");
  const [results, setResults] = useState<Patient[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [isSearching, setIsSearching] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const handleSearch = async (event?: React.FormEvent<HTMLFormElement>) => {
    event?.preventDefault();
    if (searchTerm.trim().length < 2) {
      setErrorMessage("กรุณาพิมพ์อย่างน้อย 2 ตัวอักษร");
      return;
    }

    setIsSearching(true);
    setErrorMessage(null);
    try {
      setResults(await patientApi.search(searchTerm.trim(), 50));
      setHasSearched(true);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "ค้นหาไม่สำเร็จ");
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="space-y-4">
      {errorMessage && <Alert>{errorMessage}</Alert>}

      <Card
        title="ค้นหาคนไข้"
        description="ค้นด้วยเบอร์โทร ชื่อ หรือรหัสคนไข้ (ค้นได้ทุกสาขา)"
        actions={
          <Button variant="secondary" onClick={() => setIsCreateOpen((open) => !open)}>
            {isCreateOpen ? "ปิดฟอร์ม" : "+ ลงทะเบียนคนไข้ใหม่"}
          </Button>
        }
      >
        <form onSubmit={handleSearch} className="flex gap-2">
          <TextInput
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="เช่น 0812345678, สมหญิง, BKK-000001"
            autoFocus
          />
          <Button type="submit" disabled={isSearching}>
            {isSearching ? "กำลังค้นหา..." : "ค้นหา"}
          </Button>
        </form>
      </Card>

      {isCreateOpen && (
        <NewPatientForm
          onCreated={(patient) => {
            setResults([patient, ...results]);
            setHasSearched(true);
            setIsCreateOpen(false);
          }}
        />
      )}

      <Card title="ผลการค้นหา" description={hasSearched ? `พบ ${results.length} รายการ` : undefined}>
        {!hasSearched ? (
          <EmptyState message="พิมพ์คำค้นแล้วกดค้นหาเพื่อดูรายชื่อคนไข้" />
        ) : results.length === 0 ? (
          <EmptyState message="ไม่พบคนไข้ที่ตรงกับคำค้น — ลงทะเบียนใหม่ได้จากปุ่มด้านบน" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {results.map((patient) => (
              <li key={patient.id} className="py-3">
                <Link
                  href={`/patients/${patient.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg px-2 py-1 hover:bg-slate-50"
                >
                  <div>
                    <p className="font-medium text-slate-800">{patient.full_name}</p>
                    <p className="text-xs text-slate-500">
                      {patient.patient_code} · {patient.phone} · ลงทะเบียนที่{" "}
                      {patient.home_clinic_name}
                    </p>
                    {patient.pinned_notes.length > 0 && (
                      <p className="mt-1 text-xs text-amber-700">📌 {patient.pinned_notes[0]}</p>
                    )}
                  </div>
                  <span className="text-sm text-brand-600">ดูประวัติ →</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function NewPatientForm({ onCreated }: { onCreated: (patient: Patient) => void }) {
  const [form, setForm] = useState({
    first_name: "",
    last_name: "",
    phone: "",
    date_of_birth: "",
    gender: "unspecified",
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const patient = await patientApi.create({
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        date_of_birth: form.date_of_birth || null,
        gender: form.gender,
      });
      onCreated(patient);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "ลงทะเบียนคนไข้ไม่สำเร็จ");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card title="ลงทะเบียนคนไข้ใหม่" description="ระบบจะสร้างรหัสคนไข้ให้อัตโนมัติ">
      <form onSubmit={handleSubmit} className="space-y-3">
        {errorMessage && <Alert>{errorMessage}</Alert>}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="ชื่อ">
            <TextInput
              value={form.first_name}
              onChange={(event) => setForm({ ...form, first_name: event.target.value })}
              required
            />
          </Field>
          <Field label="นามสกุล">
            <TextInput
              value={form.last_name}
              onChange={(event) => setForm({ ...form, last_name: event.target.value })}
            />
          </Field>
          <Field label="เบอร์โทร" hint="เช่น 0812345678">
            <TextInput
              value={form.phone}
              onChange={(event) => setForm({ ...form, phone: event.target.value })}
              pattern="0\d{8,9}"
              required
            />
          </Field>
          <Field label="วันเกิด">
            <TextInput
              type="date"
              value={form.date_of_birth}
              onChange={(event) => setForm({ ...form, date_of_birth: event.target.value })}
            />
          </Field>
          <Field label="เพศ">
            <Select
              value={form.gender}
              onChange={(event) => setForm({ ...form, gender: event.target.value })}
            >
              <option value="unspecified">ไม่ระบุ</option>
              <option value="female">หญิง</option>
              <option value="male">ชาย</option>
              <option value="other">อื่น ๆ</option>
            </Select>
          </Field>
        </div>

        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "กำลังบันทึก..." : "บันทึกคนไข้"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
