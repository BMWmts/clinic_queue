"use client";

/**
 * ตารางแพทย์รายวัน — คอลัมน์ละหนึ่งแพทย์ แถวละครึ่งชั่วโมง
 *
 * แสดงสามสถานะของช่องเวลา: มีคิวแล้ว / ถูกบล็อก (พักเที่ยง ลา) / ว่างรับได้
 * ช่องที่ว่างกดเพื่อเปิดกล่องจองได้ทันที โดยเวลาที่จองจริงยังต้องผ่านการตรวจจาก backend
 */
import { useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, doctorApi, schedulingApi } from "@/lib/api";
import { formatTime, isoDateOf, shiftIsoDate, todayIsoDate } from "@/lib/format";
import { useSession } from "@/lib/hooks/useSession";
import { Alert, Button, Card, EmptyState, LoadingRow, TextInput } from "@/components/ui";
import { BookingDialog } from "@/components/booking/BookingDialog";
import type { Appointment, Doctor, DoctorAvailability } from "@/types/api";

const ROW_MINUTES = 30;
const DEFAULT_START_HOUR = 8;
const DEFAULT_END_HOUR = 20;

interface TimeRow {
  /** เวลาเริ่มของแถวในหน่วย "นาทีนับจากเที่ยงคืนตามเวลาไทย" */
  minuteOfDay: number;
  label: string;
}

function minuteOfDayOf(isoString: string): number {
  const localTime = formatTime(isoString);
  const [hours, minutes] = localTime.split(":").map(Number);
  return hours * 60 + minutes;
}

function buildTimeRows(availabilities: DoctorAvailability[]): TimeRow[] {
  const workingIntervals = availabilities.flatMap((availability) => availability.working_intervals);

  const startMinute = workingIntervals.length
    ? Math.min(...workingIntervals.map((interval) => minuteOfDayOf(interval.start)))
    : DEFAULT_START_HOUR * 60;
  const endMinute = workingIntervals.length
    ? Math.max(...workingIntervals.map((interval) => minuteOfDayOf(interval.end)))
    : DEFAULT_END_HOUR * 60;

  const rows: TimeRow[] = [];
  for (let minute = startMinute; minute < endMinute; minute += ROW_MINUTES) {
    const hour = Math.floor(minute / 60);
    const minutePart = minute % 60;
    rows.push({
      minuteOfDay: minute,
      label: `${String(hour).padStart(2, "0")}:${String(minutePart).padStart(2, "0")}`,
    });
  }
  return rows;
}

export function CalendarBoard() {
  const { activeClinicId, needsClinicSelection } = useSession();
  const [targetDate, setTargetDate] = useState(todayIsoDate());
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [availabilities, setAvailabilities] = useState<DoctorAvailability[]>([]);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [bookingDoctorId, setBookingDoctorId] = useState<number | null>(null);
  const [isBookingOpen, setIsBookingOpen] = useState(false);

  const loadCalendar = useCallback(async () => {
    if (needsClinicSelection) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);
    try {
      const doctorPage = await doctorApi.list({
        is_active: true,
        clinic_id: activeClinicId ?? undefined,
      });
      const activeDoctors = doctorPage.results;

      const [availabilityList, appointmentPage] = await Promise.all([
        Promise.all(activeDoctors.map((doctor) => doctorApi.availability(doctor.id, targetDate))),
        schedulingApi.listAppointments({
          date_from: targetDate,
          date_to: targetDate,
          page_size: 200,
          clinic_id: activeClinicId ?? undefined,
        }),
      ]);

      setDoctors(activeDoctors);
      setAvailabilities(availabilityList);
      setAppointments(appointmentPage.results);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "โหลดตารางแพทย์ไม่สำเร็จ");
    } finally {
      setIsLoading(false);
    }
  }, [targetDate, activeClinicId, needsClinicSelection]);

  useEffect(() => {
    void loadCalendar();
  }, [loadCalendar]);

  const timeRows = useMemo(() => buildTimeRows(availabilities), [availabilities]);

  /** หาสถานะของช่องเวลาหนึ่งช่อง เพื่อให้ตารางอ่านง่ายในสายตาเดียว */
  const describeCell = (doctorId: number, minuteOfDay: number) => {
    const rowStart = minuteOfDay;
    const rowEnd = minuteOfDay + ROW_MINUTES;

    const appointment = appointments.find(
      (item) =>
        item.doctor === doctorId &&
        !["cancelled", "no_show"].includes(item.status) &&
        minuteOfDayOf(item.scheduled_start) < rowEnd &&
        minuteOfDayOf(item.scheduled_end) > rowStart,
    );
    if (appointment) {
      const isFirstRow = minuteOfDayOf(appointment.scheduled_start) >= rowStart;
      return { kind: "appointment" as const, appointment, isFirstRow };
    }

    const availability = availabilities.find((item) => item.doctor_id === doctorId);
    const isBlocked = availability?.blocked_intervals.some(
      (interval) =>
        minuteOfDayOf(interval.start) < rowEnd && minuteOfDayOf(interval.end) > rowStart,
    );
    if (isBlocked) {
      return { kind: "blocked" as const };
    }

    const isWorking = availability?.working_intervals.some(
      (interval) =>
        minuteOfDayOf(interval.start) <= rowStart && minuteOfDayOf(interval.end) >= rowEnd,
    );
    return { kind: isWorking ? ("free" as const) : ("off" as const) };
  };

  if (needsClinicSelection) {
    return (
      <Alert tone="info">
        กรุณาเลือกสาขาที่ต้องการดูแลจากแถบด้านบนขวา ระบบจึงจะแสดงตารางแพทย์ของสาขานั้นให้
      </Alert>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-500">วันที่</label>
            <TextInput
              type="date"
              value={targetDate}
              onChange={(event) => setTargetDate(event.target.value || todayIsoDate())}
              className="w-44"
            />
          </div>
          <Button variant="secondary" onClick={() => setTargetDate(shiftIsoDate(targetDate, -1))}>
            ← วันก่อน
          </Button>
          <Button variant="secondary" onClick={() => setTargetDate(todayIsoDate())}>
            วันนี้
          </Button>
          <Button variant="secondary" onClick={() => setTargetDate(shiftIsoDate(targetDate, 1))}>
            วันถัดไป →
          </Button>
        </div>

        <Button
          onClick={() => {
            setBookingDoctorId(doctors[0]?.id ?? null);
            setIsBookingOpen(true);
          }}
        >
          + จองคิวล่วงหน้า
        </Button>
      </div>

      {errorMessage && <Alert>{errorMessage}</Alert>}

      <Card
        title={`ตารางแพทย์ ${targetDate}`}
        description="สีเทา = ถูกบล็อก, ช่องว่าง = รับคิวได้, กดช่องว่างเพื่อจอง"
      >
        {isLoading ? (
          <LoadingRow />
        ) : doctors.length === 0 ? (
          <EmptyState message="ยังไม่มีแพทย์ในสาขานี้" />
        ) : (
          <div className="table-scroll">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr>
                  <th className="w-20 border-b border-slate-100 px-2 py-2 text-left text-xs text-slate-500">
                    เวลา
                  </th>
                  {doctors.map((doctor) => (
                    <th
                      key={doctor.id}
                      className="border-b border-slate-100 px-2 py-2 text-left text-xs text-slate-600"
                    >
                      <span className="inline-flex items-center gap-1.5">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full"
                          style={{ backgroundColor: doctor.color }}
                        />
                        {doctor.display_name}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {timeRows.map((row) => (
                  <tr key={row.minuteOfDay}>
                    <td className="border-b border-slate-50 px-2 py-1 text-xs text-slate-400">
                      {row.label}
                    </td>
                    {doctors.map((doctor) => {
                      const cell = describeCell(doctor.id, row.minuteOfDay);
                      return (
                        <td key={doctor.id} className="border-b border-l border-slate-50 p-0">
                          <CalendarCell
                            cell={cell}
                            onBook={() => {
                              setBookingDoctorId(doctor.id);
                              setIsBookingOpen(true);
                            }}
                          />
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {isBookingOpen && (
        <BookingDialog
          doctors={doctors}
          clinicId={activeClinicId}
          initialDate={targetDate}
          initialDoctorId={bookingDoctorId}
          onClose={() => setIsBookingOpen(false)}
          onBooked={() => {
            setIsBookingOpen(false);
            void loadCalendar();
          }}
        />
      )}
    </div>
  );
}

type CellDescription =
  | { kind: "appointment"; appointment: Appointment; isFirstRow: boolean }
  | { kind: "blocked" }
  | { kind: "free" }
  | { kind: "off" };

function CalendarCell({ cell, onBook }: { cell: CellDescription; onBook: () => void }) {
  if (cell.kind === "appointment") {
    const { appointment, isFirstRow } = cell;
    return (
      <div
        className="h-9 px-2 py-1 text-xs"
        style={{ backgroundColor: `${appointment.doctor_color ?? "#2563eb"}1a` }}
        title={`${appointment.patient_name} · ${appointment.service_name}`}
      >
        {isFirstRow && (
          <span className="block truncate font-medium text-slate-700">
            {appointment.patient_name} · {appointment.service_name}
          </span>
        )}
      </div>
    );
  }

  if (cell.kind === "blocked") {
    return <div className="h-9 bg-slate-200/70" title="ช่วงเวลาที่ถูกบล็อก" />;
  }

  if (cell.kind === "off") {
    return <div className="h-9 bg-slate-50" title="นอกเวลาออกตรวจ" />;
  }

  return (
    <button
      type="button"
      onClick={onBook}
      className="h-9 w-full text-left text-xs text-transparent transition hover:bg-brand-50 hover:text-brand-700"
      title="ว่าง — กดเพื่อจองคิว"
    >
      + จอง
    </button>
  );
}

/** ใช้จากหน้าอื่นเมื่อต้องเปิดปฏิทินที่วันใดวันหนึ่ง */
export const calendarDateOf = (date: Date) => isoDateOf(date);
