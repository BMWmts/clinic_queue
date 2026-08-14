"use client";

/**
 * หน้าจอคิวหน้างาน — รายการคิวของวัน พร้อมปุ่มเปลี่ยนสถานะและเลื่อนคิว
 *
 * อัปเดตอัตโนมัติผ่าน WebSocket และ polling (ดู useQueueBoard)
 */
import { useEffect, useMemo, useState } from "react";

import { ApiError, doctorApi, queueApi } from "@/lib/api";
import {
  STATUS_STYLES,
  formatTime,
  formatTimeRange,
  isoDateOf,
  shiftIsoDate,
  todayIsoDate,
} from "@/lib/format";
import { useQueueBoard } from "@/lib/hooks/useQueueBoard";
import { useSession } from "@/lib/hooks/useSession";
import {
  Alert,
  Button,
  Card,
  EmptyState,
  LoadingRow,
  Select,
  StatCard,
  StatusBadge,
  TextInput,
} from "@/components/ui";
import { RescheduleDialog } from "@/components/queue/RescheduleDialog";
import { WalkInDialog } from "@/components/queue/WalkInDialog";
import type { Appointment, AppointmentStatus, Doctor } from "@/types/api";

export function QueueBoard() {
  const { canOperateQueue } = useSession();
  const [selectedDate, setSelectedDate] = useState(todayIsoDate());
  const [selectedDoctorId, setSelectedDoctorId] = useState<number | undefined>(undefined);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [walkInOpen, setWalkInOpen] = useState(false);
  const [appointmentToReschedule, setAppointmentToReschedule] = useState<Appointment | null>(null);

  const { appointments, summary, isLoading, errorMessage, isLive, refresh, applyUpdatedAppointment } =
    useQueueBoard({ date: selectedDate, doctorId: selectedDoctorId });

  useEffect(() => {
    doctorApi
      .list({ is_active: true })
      .then((page) => setDoctors(page.results))
      .catch(() => setDoctors([]));
  }, []);

  const isToday = selectedDate === todayIsoDate();

  /** คิวที่ยังต้องดูแลอยู่หน้างาน (ไม่รวมที่จบไปแล้ว) เพื่อให้เจ้าหน้าที่เห็นงานค้างชัด ๆ */
  const activeCount = useMemo(
    () =>
      appointments.filter((appointment) =>
        ["booked", "confirmed", "checked_in", "in_progress"].includes(appointment.status),
      ).length,
    [appointments],
  );

  const handleStatusChange = async (appointment: Appointment, status: AppointmentStatus) => {
    setActionError(null);
    try {
      const updated = await queueApi.changeStatus(appointment.id, status);
      applyUpdatedAppointment(updated);
      await refresh();
    } catch (error) {
      setActionError(error instanceof ApiError ? error.message : "เปลี่ยนสถานะไม่สำเร็จ");
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">วันที่</label>
            <TextInput
              type="date"
              value={selectedDate}
              onChange={(event) => setSelectedDate(event.target.value || todayIsoDate())}
              className="w-44"
            />
          </div>
          <Button variant="secondary" onClick={() => setSelectedDate(shiftIsoDate(selectedDate, -1))}>
            ← วันก่อน
          </Button>
          <Button variant="secondary" onClick={() => setSelectedDate(todayIsoDate())}>
            วันนี้
          </Button>
          <Button variant="secondary" onClick={() => setSelectedDate(shiftIsoDate(selectedDate, 1))}>
            วันถัดไป →
          </Button>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">แพทย์</label>
            <Select
              value={selectedDoctorId ?? ""}
              onChange={(event) =>
                setSelectedDoctorId(event.target.value ? Number(event.target.value) : undefined)
              }
              className="w-48"
            >
              <option value="">ทุกท่าน</option>
              {doctors.map((doctor) => (
                <option key={doctor.id} value={doctor.id}>
                  {doctor.display_name}
                </option>
              ))}
            </Select>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span
            className={`rounded-full px-2.5 py-1 text-xs ${
              isLive ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-500"
            }`}
            title={isLive ? "เชื่อมต่อแบบเรียลไทม์อยู่" : "อัปเดตอัตโนมัติทุก 10 วินาที"}
          >
            {isLive ? "● เรียลไทม์" : "○ อัปเดตทุก 10 วิ"}
          </span>
          <Button variant="secondary" onClick={() => void refresh()}>
            รีเฟรช
          </Button>
          {canOperateQueue && isToday && (
            <Button onClick={() => setWalkInOpen(true)}>+ รับคิว Walk-in</Button>
          )}
        </div>
      </div>

      {(errorMessage || actionError) && <Alert>{actionError ?? errorMessage}</Alert>}

      <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
        <StatCard label="คิวทั้งหมด" value={summary?.total ?? 0} />
        <StatCard label="ยังไม่เสร็จ" value={activeCount} hint="จองแล้ว/รอพบแพทย์/กำลังรักษา" />
        <StatCard label="รอพบแพทย์" value={summary?.checked_in ?? 0} />
        <StatCard label="เสร็จสิ้น" value={summary?.completed ?? 0} />
        <StatCard label="ไม่มาตามนัด" value={summary?.no_show ?? 0} />
      </div>

      <Card title={`คิววันที่ ${selectedDate}`} description={`ทั้งหมด ${appointments.length} คิว`}>
        {isLoading ? (
          <LoadingRow />
        ) : appointments.length === 0 ? (
          <EmptyState message="ยังไม่มีคิวในวันนี้" />
        ) : (
          <div className="table-scroll">
            <table className="w-full min-w-[820px] text-sm">
              <thead>
                <tr className="border-b border-slate-100 text-left text-xs uppercase text-slate-500">
                  <th className="px-2 py-2">เวลา</th>
                  <th className="px-2 py-2">คนไข้</th>
                  <th className="px-2 py-2">บริการ</th>
                  <th className="px-2 py-2">แพทย์</th>
                  <th className="px-2 py-2">สถานะ</th>
                  <th className="px-2 py-2">การจัดการ</th>
                </tr>
              </thead>
              <tbody>
                {appointments.map((appointment) => (
                  <QueueRow
                    key={appointment.id}
                    appointment={appointment}
                    canOperateQueue={canOperateQueue}
                    onStatusChange={handleStatusChange}
                    onReschedule={() => setAppointmentToReschedule(appointment)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {walkInOpen && (
        <WalkInDialog
          doctors={doctors}
          onClose={() => setWalkInOpen(false)}
          onCreated={(appointment) => {
            applyUpdatedAppointment(appointment);
            setWalkInOpen(false);
            void refresh();
          }}
        />
      )}

      {appointmentToReschedule && (
        <RescheduleDialog
          appointment={appointmentToReschedule}
          doctors={doctors}
          onClose={() => setAppointmentToReschedule(null)}
          onRescheduled={(appointment) => {
            applyUpdatedAppointment(appointment);
            setAppointmentToReschedule(null);
            void refresh();
          }}
        />
      )}
    </div>
  );
}

function QueueRow({
  appointment,
  canOperateQueue,
  onStatusChange,
  onReschedule,
}: {
  appointment: Appointment;
  canOperateQueue: boolean;
  onStatusChange: (appointment: Appointment, status: AppointmentStatus) => Promise<void>;
  onReschedule: () => void;
}) {
  const canReschedule =
    canOperateQueue && !["completed", "cancelled"].includes(appointment.status);

  return (
    <tr className="border-b border-slate-50 align-top">
      <td className="px-2 py-3 font-medium text-slate-800">
        {formatTimeRange(appointment.scheduled_start, appointment.scheduled_end)}
        {appointment.source === "walk_in" && (
          <span className="ml-1 rounded bg-amber-50 px-1.5 py-0.5 text-[11px] text-amber-700">
            walk-in
          </span>
        )}
      </td>
      <td className="px-2 py-3">
        <p className="font-medium text-slate-800">{appointment.patient_name}</p>
        <p className="text-xs text-slate-500">{appointment.patient_code}</p>
        {appointment.note && <p className="mt-1 text-xs text-amber-700">📌 {appointment.note}</p>}
      </td>
      <td className="px-2 py-3 text-slate-700">
        {appointment.service_name}
        <span className="block text-xs text-slate-400">{appointment.duration_minutes} นาที</span>
      </td>
      <td className="px-2 py-3 text-slate-700">
        {appointment.doctor_name ? (
          <span className="inline-flex items-center gap-1.5">
            <span
              className="inline-block h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: appointment.doctor_color ?? "#94a3b8" }}
            />
            {appointment.doctor_name}
          </span>
        ) : (
          <span className="text-slate-400">ไม่ระบุแพทย์</span>
        )}
      </td>
      <td className="px-2 py-3">
        <StatusBadge status={appointment.status} />
        {appointment.checked_in_at && (
          <p className="mt-1 text-xs text-slate-400">เช็คอิน {formatTime(appointment.checked_in_at)}</p>
        )}
      </td>
      <td className="px-2 py-3">
        <div className="flex flex-wrap gap-1.5">
          {appointment.allowed_next_statuses.map((status) => (
            <Button
              key={status}
              variant={status === "cancelled" || status === "no_show" ? "secondary" : "primary"}
              onClick={() => void onStatusChange(appointment, status)}
              className="px-2.5 py-1 text-xs"
            >
              {STATUS_STYLES[status].label}
            </Button>
          ))}
          {canReschedule && (
            <Button variant="ghost" onClick={onReschedule} className="px-2.5 py-1 text-xs">
              เลื่อนคิว
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

/** ใช้ภายในเทสต์/หน้าอื่นเมื่อต้องแปลงวันที่ปัจจุบันเป็นค่าเริ่มต้นของตัวเลือกวัน */
export const defaultQueueDate = () => isoDateOf(new Date());
