"use client";

/**
 * หน้าจัดการแพทย์รายบุคคล — แก้โปรไฟล์ ตั้งตารางออกตรวจ และบันทึกวันลา
 *
 * ตารางออกตรวจคือข้อมูลที่ระบบใช้คำนวณ "เวลาว่างที่จองได้" ทั้งหมด
 * ถ้าแพทย์ไม่มีตารางออกตรวจ จะไม่มี slot ให้จองเลย หน้าจอนี้จึงเตือนไว้ชัดเจน
 */
import { useCallback, useEffect, useState } from "react";

import { ApiError, doctorApi } from "@/lib/api";
import { formatDateTime, todayIsoDate, toBangkokIso } from "@/lib/format";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  Field,
  LoadingRow,
  Select,
  TextInput,
} from "@/components/ui";
import type { Doctor, DoctorSchedule, TimeBlock } from "@/types/api";

const WEEKDAYS = [
  { value: 0, label: "จันทร์" },
  { value: 1, label: "อังคาร" },
  { value: 2, label: "พุธ" },
  { value: 3, label: "พฤหัสบดี" },
  { value: 4, label: "ศุกร์" },
  { value: 5, label: "เสาร์" },
  { value: 6, label: "อาทิตย์" },
];

const TIME_OFF_REASONS = [
  { value: "leave", label: "ลา" },
  { value: "lunch", label: "พักเที่ยง" },
  { value: "meeting", label: "ประชุม" },
  { value: "urgent_case", label: "เคสด่วน" },
  { value: "other", label: "อื่น ๆ" },
];

export function DoctorDetail({ doctorId }: { doctorId: number }) {
  const [doctor, setDoctor] = useState<Doctor | null>(null);
  const [schedules, setSchedules] = useState<DoctorSchedule[]>([]);
  const [timeBlocks, setTimeBlocks] = useState<TimeBlock[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadDoctor = useCallback(async () => {
    setIsLoading(true);
    try {
      const [doctorData, schedulePage, timeBlockPage] = await Promise.all([
        doctorApi.retrieve(doctorId),
        doctorApi.schedules(doctorId),
        doctorApi.timeBlocks({ doctor_id: doctorId, date_from: todayIsoDate() }),
      ]);
      setDoctor(doctorData);
      setSchedules(schedulePage.results);
      setTimeBlocks(timeBlockPage.results);
      setErrorMessage(null);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดข้อมูลแพทย์ไม่สำเร็จ");
    } finally {
      setIsLoading(false);
    }
  }, [doctorId]);

  useEffect(() => {
    void loadDoctor();
  }, [loadDoctor]);

  if (isLoading) {
    return <LoadingRow />;
  }
  if (errorMessage || !doctor) {
    return <Alert>{errorMessage ?? "ไม่พบข้อมูลแพทย์"}</Alert>;
  }

  return (
    <div className="space-y-4">
      <DoctorProfileCard doctor={doctor} onSaved={setDoctor} />
      <WeeklyScheduleCard
        doctor={doctor}
        schedules={schedules}
        onChanged={() => void loadDoctor()}
      />
      <TimeOffCard doctor={doctor} timeBlocks={timeBlocks} onChanged={() => void loadDoctor()} />
    </div>
  );
}

function DoctorProfileCard({
  doctor,
  onSaved,
}: {
  doctor: Doctor;
  onSaved: (doctor: Doctor) => void;
}) {
  const [form, setForm] = useState({
    display_name: doctor.display_name,
    specialties: doctor.specialties,
    color: doctor.color,
    is_active: doctor.is_active,
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setErrorMessage(null);
    setStatusMessage(null);

    try {
      onSaved(await doctorApi.update(doctor.id, form));
      setStatusMessage("บันทึกข้อมูลแล้ว");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "บันทึกไม่สำเร็จ");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card title={doctor.display_name} description={`${doctor.email} · ${doctor.clinic_name}`}>
      <form onSubmit={handleSubmit} className="space-y-3">
        {errorMessage && <Alert>{errorMessage}</Alert>}
        {statusMessage && <Alert tone="success">{statusMessage}</Alert>}

        <div className="grid gap-3 sm:grid-cols-3">
          <Field label="ชื่อที่แสดงบนปฏิทิน">
            <TextInput
              value={form.display_name}
              onChange={(event) => setForm({ ...form, display_name: event.target.value })}
              required
            />
          </Field>
          <Field label="ความเชี่ยวชาญ">
            <TextInput
              value={form.specialties}
              onChange={(event) => setForm({ ...form, specialties: event.target.value })}
            />
          </Field>
          <Field label="สีในปฏิทิน">
            <TextInput
              type="color"
              value={form.color}
              onChange={(event) => setForm({ ...form, color: event.target.value })}
              className="h-10 p-1"
            />
          </Field>
        </div>

        <div className="flex items-center justify-between">
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(event) => setForm({ ...form, is_active: event.target.checked })}
            />
            ยังออกตรวจอยู่ (ปิดไว้เมื่อลาออก/พักงาน — คิวเดิมยังอยู่ครบ แต่จะจองใหม่ไม่ได้)
          </label>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? "กำลังบันทึก..." : "บันทึกโปรไฟล์"}
          </Button>
        </div>
      </form>
    </Card>
  );
}

function WeeklyScheduleCard({
  doctor,
  schedules,
  onChanged,
}: {
  doctor: Doctor;
  schedules: DoctorSchedule[];
  onChanged: () => void;
}) {
  const [form, setForm] = useState({ day_of_week: 0, start_time: "09:00", end_time: "12:00" });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleAdd = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setErrorMessage(null);

    try {
      await doctorApi.createSchedule({
        doctor: doctor.id,
        day_of_week: Number(form.day_of_week),
        start_time: form.start_time,
        end_time: form.end_time,
      });
      onChanged();
    } catch (error) {
      setErrorMessage(
        error instanceof ApiError ? error.message : "เพิ่มช่วงเวลาออกตรวจไม่สำเร็จ",
      );
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (scheduleId: number) => {
    setErrorMessage(null);
    try {
      await doctorApi.deleteSchedule(scheduleId);
      onChanged();
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "ลบช่วงเวลาไม่สำเร็จ");
    }
  };

  return (
    <Card
      title="ตารางออกตรวจประจำสัปดาห์"
      description="ระบบใช้ตารางนี้คำนวณเวลาว่างที่จองได้ — เพิ่มได้หลายช่วงต่อวัน เช่น เช้าและบ่าย"
    >
      <div className="space-y-4">
        {errorMessage && <Alert>{errorMessage}</Alert>}
        {schedules.length === 0 && (
          <Alert tone="info">
            ยังไม่มีตารางออกตรวจ — ตอนนี้ระบบจะยังจองคิวให้แพทย์ท่านนี้ไม่ได้เลย
          </Alert>
        )}

        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {WEEKDAYS.map((weekday) => {
            const daySchedules = schedules
              .filter((schedule) => schedule.day_of_week === weekday.value)
              .sort((a, b) => a.start_time.localeCompare(b.start_time));

            return (
              <div key={weekday.value} className="rounded-lg border border-slate-200 p-3">
                <p className="mb-2 text-sm font-medium text-slate-700">{weekday.label}</p>
                {daySchedules.length === 0 ? (
                  <p className="text-xs text-slate-400">ไม่ออกตรวจ</p>
                ) : (
                  <ul className="space-y-1">
                    {daySchedules.map((schedule) => (
                      <li
                        key={schedule.id}
                        className="flex items-center justify-between gap-2 text-sm text-slate-700"
                      >
                        <span>
                          {schedule.start_time.slice(0, 5)} - {schedule.end_time.slice(0, 5)}
                        </span>
                        <Button
                          variant="ghost"
                          className="px-2 py-0.5 text-xs text-rose-600"
                          onClick={() => void handleDelete(schedule.id)}
                        >
                          ลบ
                        </Button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>

        <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3">
          <Field label="วัน">
            <Select
              value={form.day_of_week}
              onChange={(event) => setForm({ ...form, day_of_week: Number(event.target.value) })}
              className="w-36"
            >
              {WEEKDAYS.map((weekday) => (
                <option key={weekday.value} value={weekday.value}>
                  {weekday.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="เริ่ม">
            <TextInput
              type="time"
              value={form.start_time}
              onChange={(event) => setForm({ ...form, start_time: event.target.value })}
              className="w-32"
              required
            />
          </Field>
          <Field label="ถึง">
            <TextInput
              type="time"
              value={form.end_time}
              onChange={(event) => setForm({ ...form, end_time: event.target.value })}
              className="w-32"
              required
            />
          </Field>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? "กำลังเพิ่ม..." : "+ เพิ่มช่วงเวลา"}
          </Button>
        </form>
      </div>
    </Card>
  );
}

function TimeOffCard({
  doctor,
  timeBlocks,
  onChanged,
}: {
  doctor: Doctor;
  timeBlocks: TimeBlock[];
  onChanged: () => void;
}) {
  const [form, setForm] = useState({
    date: todayIsoDate(),
    start_time: "12:00",
    end_time: "13:00",
    reason: "leave",
    note: "",
    is_recurring: false,
  });
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const handleAdd = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setErrorMessage(null);

    try {
      await doctorApi.createTimeBlock({
        doctor: doctor.id,
        start_datetime: toBangkokIso(form.date, form.start_time),
        end_datetime: toBangkokIso(form.date, form.end_time),
        reason: form.reason,
        note: form.note.trim(),
        is_recurring: form.is_recurring,
        recurrence: form.is_recurring ? "daily" : "none",
      });
      onChanged();
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "บันทึกช่วงเวลาที่ลาไม่สำเร็จ");
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (timeBlockId: number) => {
    setErrorMessage(null);
    try {
      await doctorApi.deleteTimeBlock(timeBlockId);
      onChanged();
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "ลบไม่สำเร็จ");
    }
  };

  return (
    <Card
      title="วันลา / ช่วงเวลาที่ไม่รับคิว"
      description="เวลาที่บล็อกไว้จะถูกตัดออกจากเวลาว่างทันที คิวที่จองไว้แล้วจะไม่ถูกลบอัตโนมัติ"
    >
      <div className="space-y-4">
        {errorMessage && <Alert>{errorMessage}</Alert>}

        {timeBlocks.length === 0 ? (
          <EmptyState message="ยังไม่มีช่วงเวลาที่บล็อกไว้ในอนาคต" />
        ) : (
          <ul className="divide-y divide-slate-100">
            {timeBlocks.map((timeBlock) => (
              <li key={timeBlock.id} className="flex items-center justify-between gap-2 py-2">
                <div>
                  <p className="text-sm text-slate-800">
                    {timeBlock.reason_display}
                    {timeBlock.is_recurring && (
                      <span className="ml-2 rounded bg-sky-100 px-1.5 py-0.5 text-xs text-sky-700">
                        ซ้ำทุกวัน
                      </span>
                    )}
                  </p>
                  <p className="text-xs text-slate-500">
                    {formatDateTime(timeBlock.start_datetime)} ถึง{" "}
                    {formatDateTime(timeBlock.end_datetime)}
                    {timeBlock.note ? ` · ${timeBlock.note}` : ""}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  className="text-xs text-rose-600"
                  onClick={() => void handleDelete(timeBlock.id)}
                >
                  ลบ
                </Button>
              </li>
            ))}
          </ul>
        )}

        <form onSubmit={handleAdd} className="flex flex-wrap items-end gap-2 border-t border-slate-100 pt-3">
          <Field label="วันที่">
            <TextInput
              type="date"
              value={form.date}
              onChange={(event) => setForm({ ...form, date: event.target.value })}
              className="w-40"
              required
            />
          </Field>
          <Field label="ตั้งแต่">
            <TextInput
              type="time"
              value={form.start_time}
              onChange={(event) => setForm({ ...form, start_time: event.target.value })}
              className="w-28"
              required
            />
          </Field>
          <Field label="ถึง">
            <TextInput
              type="time"
              value={form.end_time}
              onChange={(event) => setForm({ ...form, end_time: event.target.value })}
              className="w-28"
              required
            />
          </Field>
          <Field label="เหตุผล">
            <Select
              value={form.reason}
              onChange={(event) => setForm({ ...form, reason: event.target.value })}
              className="w-32"
            >
              {TIME_OFF_REASONS.map((reason) => (
                <option key={reason.value} value={reason.value}>
                  {reason.label}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="บันทึกเพิ่มเติม">
            <TextInput
              value={form.note}
              onChange={(event) => setForm({ ...form, note: event.target.value })}
              className="w-48"
            />
          </Field>
          <label className="flex items-center gap-2 pb-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={form.is_recurring}
              onChange={(event) => setForm({ ...form, is_recurring: event.target.checked })}
            />
            ซ้ำทุกวัน
          </label>
          <Button type="submit" disabled={isSaving}>
            {isSaving ? "กำลังบันทึก..." : "+ เพิ่ม"}
          </Button>
        </form>
      </div>
    </Card>
  );
}
