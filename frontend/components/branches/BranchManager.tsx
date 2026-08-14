"use client";

/**
 * จัดการสาขา — Super Admin เพิ่ม/แก้ไขได้ทุกสาขา, role อื่นเห็นเฉพาะสาขาตัวเองแบบอ่านอย่างเดียว
 *
 * ค่าที่ตั้งที่นี่มีผลต่อการคำนวณคิวโดยตรง (เวลาเปิด-ปิด, ความละเอียดของตาราง,
 * เพดานคิวของบริการที่ไม่ต้องมีแพทย์) จึงอธิบายผลของแต่ละค่าไว้ข้างช่องกรอก
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, clinicApi } from "@/lib/api";
import { useSession } from "@/lib/hooks/useSession";
import { Alert, Button, Card, EmptyState, Field, LoadingRow, TextInput } from "@/components/ui";
import type { Clinic } from "@/types/api";

const EMPTY_FORM = {
  name: "",
  code: "",
  address: "",
  phone: "",
  opening_time: "09:00",
  closing_time: "18:00",
  slot_interval_minutes: 15,
  non_doctor_service_capacity: 1,
};

export function BranchManager() {
  const { isSuperAdmin } = useSession();
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const loadClinics = useCallback(async () => {
    setIsLoading(true);
    try {
      const page = await clinicApi.list();
      setClinics(page.results);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดข้อมูลสาขาไม่สำเร็จ");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadClinics();
  }, [loadClinics]);

  return (
    <div className="space-y-4">
      {errorMessage && <Alert>{errorMessage}</Alert>}

      <Card
        title="สาขาทั้งหมด"
        description={isSuperAdmin ? "คุณจัดการได้ทุกสาขา" : "คุณเห็นเฉพาะสาขาที่สังกัด"}
        actions={
          isSuperAdmin && (
            <Button variant="secondary" onClick={() => setIsCreateOpen((open) => !open)}>
              {isCreateOpen ? "ปิดฟอร์ม" : "+ เพิ่มสาขา"}
            </Button>
          )
        }
      >
        {isLoading ? (
          <LoadingRow />
        ) : clinics.length === 0 ? (
          <EmptyState message="ยังไม่มีข้อมูลสาขา" />
        ) : (
          <div className="table-scroll">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                  <th className="px-2 py-2">สาขา</th>
                  <th className="px-2 py-2">เวลาทำการ</th>
                  <th className="px-2 py-2">ความละเอียดตาราง</th>
                  <th className="px-2 py-2">เพดานคิวไม่ใช้แพทย์</th>
                  <th className="px-2 py-2">สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {clinics.map((clinic) => (
                  <tr key={clinic.id} className="border-b border-slate-50">
                    <td className="px-2 py-3">
                      <p className="font-medium text-slate-800">{clinic.name}</p>
                      <p className="text-xs text-slate-500">
                        {clinic.code} · {clinic.phone || "ไม่ระบุเบอร์"}
                      </p>
                    </td>
                    <td className="px-2 py-3 text-slate-700">
                      {clinic.opening_time.slice(0, 5)} - {clinic.closing_time.slice(0, 5)}
                      <span className="block text-xs text-slate-400">{clinic.timezone}</span>
                    </td>
                    <td className="px-2 py-3 text-slate-700">{clinic.slot_interval_minutes} นาที</td>
                    <td className="px-2 py-3 text-slate-700">
                      {clinic.non_doctor_service_capacity} คิวพร้อมกัน
                    </td>
                    <td className="px-2 py-3">
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs ${
                          clinic.is_active
                            ? "bg-emerald-100 text-emerald-700"
                            : "bg-slate-200 text-slate-600"
                        }`}
                      >
                        {clinic.is_active ? "เปิดใช้งาน" : "ปิดใช้งาน"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {isSuperAdmin && isCreateOpen && (
        <NewBranchForm
          onCreated={(clinic) => {
            setClinics([...clinics, clinic]);
            setIsCreateOpen(false);
          }}
        />
      )}
    </div>
  );
}

function NewBranchForm({ onCreated }: { onCreated: (clinic: Clinic) => void }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const clinic = await clinicApi.create({
        ...form,
        code: form.code.toUpperCase(),
        slot_interval_minutes: Number(form.slot_interval_minutes),
        non_doctor_service_capacity: Number(form.non_doctor_service_capacity),
      });
      onCreated(clinic);
      setForm(EMPTY_FORM);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "เพิ่มสาขาไม่สำเร็จ");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card title="เพิ่มสาขาใหม่">
      <form onSubmit={handleSubmit} className="space-y-3">
        {errorMessage && <Alert>{errorMessage}</Alert>}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="ชื่อสาขา">
            <TextInput
              value={form.name}
              onChange={(event) => setForm({ ...form, name: event.target.value })}
              required
            />
          </Field>
          <Field label="รหัสสาขา" hint="ใช้เป็น prefix ของรหัสคนไข้ เช่น BKK">
            <TextInput
              value={form.code}
              onChange={(event) => setForm({ ...form, code: event.target.value.toUpperCase() })}
              pattern="[A-Za-z0-9\-]{2,20}"
              required
            />
          </Field>
          <Field label="เวลาเปิด">
            <TextInput
              type="time"
              value={form.opening_time}
              onChange={(event) => setForm({ ...form, opening_time: event.target.value })}
              required
            />
          </Field>
          <Field label="เวลาปิด">
            <TextInput
              type="time"
              value={form.closing_time}
              onChange={(event) => setForm({ ...form, closing_time: event.target.value })}
              required
            />
          </Field>
          <Field
            label="ความละเอียดของตาราง (นาที)"
            hint="ระบบจะเสนอเวลาเริ่มคิวเป็นช่วง ๆ ตามค่านี้"
          >
            <TextInput
              type="number"
              min={5}
              max={120}
              value={form.slot_interval_minutes}
              onChange={(event) =>
                setForm({ ...form, slot_interval_minutes: Number(event.target.value) })
              }
              required
            />
          </Field>
          <Field
            label="เพดานคิวของบริการที่ไม่ต้องมีแพทย์"
            hint="เช่น จำนวนเตียงดริปที่รับพร้อมกันได้"
          >
            <TextInput
              type="number"
              min={1}
              max={50}
              value={form.non_doctor_service_capacity}
              onChange={(event) =>
                setForm({ ...form, non_doctor_service_capacity: Number(event.target.value) })
              }
              required
            />
          </Field>
          <Field label="เบอร์โทรสาขา">
            <TextInput
              value={form.phone}
              onChange={(event) => setForm({ ...form, phone: event.target.value })}
            />
          </Field>
          <Field label="ที่อยู่">
            <TextInput
              value={form.address}
              onChange={(event) => setForm({ ...form, address: event.target.value })}
            />
          </Field>
        </div>

        <div className="flex justify-end">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "กำลังบันทึก..." : "บันทึกสาขา"}
          </Button>
        </div>
      </form>
    </Card>
  );
}
