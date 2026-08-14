/**
 * ฟังก์ชันจัดรูปแบบการแสดงผล (แยกออกจาก UI component เพื่อให้ใช้ซ้ำและทดสอบได้)
 *
 * ทุกเวลาที่ได้จาก backend เป็น ISO string พร้อม timezone — แปลงเป็นเวลาไทยตอนแสดงผล
 */
import type { AppointmentStatus } from "@/types/api";

const BANGKOK_TIME_ZONE = "Asia/Bangkok";

const timeFormatter = new Intl.DateTimeFormat("th-TH", {
  hour: "2-digit",
  minute: "2-digit",
  timeZone: BANGKOK_TIME_ZONE,
});

const dateFormatter = new Intl.DateTimeFormat("th-TH", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: BANGKOK_TIME_ZONE,
});

const weekdayFormatter = new Intl.DateTimeFormat("th-TH", {
  weekday: "long",
  timeZone: BANGKOK_TIME_ZONE,
});

/** เวลา เช่น "09:30" */
export function formatTime(isoString: string): string {
  return timeFormatter.format(new Date(isoString));
}

/** วันที่ เช่น "13 ส.ค. 2569" */
export function formatDate(isoString: string): string {
  return dateFormatter.format(new Date(isoString));
}

export function formatWeekday(isoString: string): string {
  return weekdayFormatter.format(new Date(isoString));
}

export function formatDateTime(isoString: string): string {
  return `${formatDate(isoString)} ${formatTime(isoString)} น.`;
}

/** ช่วงเวลาแบบ "09:30 - 10:00" */
export function formatTimeRange(startIso: string, endIso: string): string {
  return `${formatTime(startIso)} - ${formatTime(endIso)}`;
}

export function formatBaht(amount: number | string): string {
  const numericAmount = typeof amount === "string" ? Number(amount) : amount;
  return new Intl.NumberFormat("th-TH", {
    style: "currency",
    currency: "THB",
    maximumFractionDigits: 0,
  }).format(Number.isFinite(numericAmount) ? numericAmount : 0);
}

export function formatPercent(ratio: number): string {
  return `${(ratio * 100).toFixed(1)}%`;
}

/** วันที่วันนี้ในรูปแบบ YYYY-MM-DD ตามเวลาไทย (ใช้ส่งเป็น query param) */
export function todayIsoDate(): string {
  return isoDateOf(new Date());
}

/** แปลง Date เป็น YYYY-MM-DD ตามเวลาไทย */
export function isoDateOf(date: Date): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: BANGKOK_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

/** เลื่อนวันที่แบบ YYYY-MM-DD ไปข้างหน้า/หลังตามจำนวนวัน */
export function shiftIsoDate(isoDate: string, days: number): string {
  const date = new Date(`${isoDate}T00:00:00+07:00`);
  date.setDate(date.getDate() + days);
  return isoDateOf(date);
}

/**
 * ประกอบวันที่ (YYYY-MM-DD) กับเวลา (HH:mm) จากช่องกรอกให้เป็น ISO string เวลาไทย
 *
 * ช่อง input แบบ date/time ของเบราว์เซอร์ให้ค่ามาเป็น "เวลานาฬิกา" ที่ไม่มีโซนเวลา
 * ต้องระบุ +07:00 ให้ชัดเจน มิฉะนั้น backend จะตีความเป็น UTC แล้วเวลาเคลื่อน 7 ชั่วโมง
 */
export function toBangkokIso(isoDate: string, clockTime: string): string {
  return `${isoDate}T${clockTime.length === 5 ? `${clockTime}:00` : clockTime}+07:00`;
}

/** สีประจำสถานะคิว — ใช้ให้ตรงกันทุกหน้าจอ */
export const STATUS_STYLES: Record<AppointmentStatus, { label: string; className: string }> = {
  booked: { label: "จองแล้ว", className: "bg-slate-100 text-slate-700 border-slate-200" },
  confirmed: { label: "ยืนยันแล้ว", className: "bg-sky-100 text-sky-800 border-sky-200" },
  checked_in: { label: "รอพบแพทย์", className: "bg-amber-100 text-amber-800 border-amber-200" },
  in_progress: { label: "กำลังรักษา", className: "bg-violet-100 text-violet-800 border-violet-200" },
  completed: { label: "เสร็จสิ้น", className: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  cancelled: { label: "ยกเลิก", className: "bg-rose-100 text-rose-800 border-rose-200" },
  no_show: { label: "ไม่มาตามนัด", className: "bg-zinc-200 text-zinc-700 border-zinc-300" },
};

/** ชื่อวันในสัปดาห์แบบ ISO (1 = จันทร์) สำหรับ heatmap ของรายงาน */
export const ISO_WEEKDAY_LABELS: Record<number, string> = {
  1: "จ.",
  2: "อ.",
  3: "พ.",
  4: "พฤ.",
  5: "ศ.",
  6: "ส.",
  7: "อา.",
};
