/**
 * Type ของข้อมูลที่รับ-ส่งกับ backend
 *
 * ตรงกับ serializer ฝั่ง Django (ดู /api/schema/ สำหรับสัญญา API ฉบับเต็ม)
 * ห้ามใช้ `any` — ทุก field ต้องมี type ชัดเจนเพื่อให้ refactor ได้อย่างปลอดภัย
 */

export type UserRole = "super_admin" | "admin" | "staff" | "doctor";

export interface User {
  id: number;
  email: string;
  full_name: string;
  phone: string;
  role: UserRole;
  role_display: string;
  clinic: number | null;
  clinic_name: string | null;
  is_active: boolean;
  date_joined: string;
}

export interface Clinic {
  id: number;
  name: string;
  code: string;
  address: string;
  phone: string;
  opening_time: string;
  closing_time: string;
  timezone: string;
  slot_interval_minutes: number;
  non_doctor_service_capacity: number;
  sms_provider: string;
  sms_sender_name: string;
  is_active: boolean;
}

export interface Doctor {
  id: number;
  user: number;
  email: string;
  clinic: number;
  clinic_name: string;
  display_name: string;
  specialties: string;
  color: string;
  is_active: boolean;
}

export interface DoctorSchedule {
  id: number;
  doctor: number;
  doctor_name: string;
  clinic: number;
  day_of_week: number;
  day_of_week_display: string;
  start_time: string;
  end_time: string;
  is_active: boolean;
}

export interface TimeBlock {
  id: number;
  doctor: number;
  doctor_name: string;
  clinic: number;
  start_datetime: string;
  end_datetime: string;
  reason: string;
  reason_display: string;
  note: string;
  is_recurring: boolean;
  recurrence: "none" | "daily" | "weekly";
  recurrence_end_date: string | null;
}

export interface ServiceType {
  id: number;
  name: string;
  category: string;
  description: string;
  duration_minutes: number;
  price: string;
  requires_doctor: boolean;
  is_active: boolean;
}

export type AppointmentStatus =
  | "booked"
  | "confirmed"
  | "checked_in"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "no_show";

export interface Appointment {
  id: number;
  patient: number;
  patient_name: string;
  patient_code: string;
  patient_phone: string;
  doctor: number | null;
  doctor_name: string | null;
  doctor_color: string | null;
  service_type: number;
  service_name: string;
  duration_minutes: number;
  clinic: number;
  scheduled_start: string;
  scheduled_end: string;
  status: AppointmentStatus;
  status_display: string;
  allowed_next_statuses: AppointmentStatus[];
  source: "walk_in" | "staff_created";
  source_display: string;
  note: string;
  checked_in_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  waiting_minutes: number | null;
  created_at: string;
}

export interface Patient {
  id: number;
  patient_code: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  date_of_birth: string | null;
  gender: "female" | "male" | "other" | "unspecified";
  home_clinic: number;
  home_clinic_name: string;
  is_active: boolean;
  pinned_notes: string[];
  created_at: string;
}

export interface PatientNote {
  id: number;
  patient: number;
  appointment: number | null;
  note_text: string;
  is_pinned: boolean;
  created_by_name: string | null;
  created_at: string;
}

export interface PatientHistory {
  patient: Patient;
  appointments: Appointment[];
}

export interface AvailableSlot {
  start: string;
  end: string;
}

export interface AvailableSlotsResponse {
  clinic_id: number;
  timezone: string;
  date: string;
  service_id: number;
  duration_minutes: number;
  doctor_id: number | null;
  slots: AvailableSlot[];
}

export interface QueueSummary {
  total: number;
  booked: number;
  confirmed: number;
  checked_in: number;
  in_progress: number;
  completed: number;
  cancelled: number;
  no_show: number;
}

export interface QueueTodayResponse {
  clinic_id: number;
  date: string;
  timezone: string;
  summary: QueueSummary;
  appointments: Appointment[];
}

export interface DoctorAvailability {
  doctor_id: number;
  date: string;
  timezone: string;
  working_intervals: { start: string; end: string }[];
  blocked_intervals: { start: string; end: string }[];
}

export interface ReportSeriesPoint {
  bucket: string;
  total: number;
  completed: number;
  cancelled: number;
  no_show: number;
}

export interface ReportSummary {
  date_from: string;
  date_to: string;
  group_by: string;
  timezone: string;
  totals: QueueSummary;
  series: ReportSeriesPoint[];
  peak_hours: { weekday: number; hour: number; total: number }[];
  by_service: {
    service_id: number;
    service_name: string;
    total: number;
    completed_revenue: number;
  }[];
  by_doctor: {
    doctor_id: number;
    doctor_name: string;
    total: number;
    completed: number;
    booked_minutes: number;
  }[];
  average_waiting_minutes: number | null;
}

export interface NoShowReport {
  date_from: string;
  date_to: string;
  total_appointments: number;
  no_show_count: number;
  completed_count: number;
  no_show_rate: number;
  by_doctor: {
    doctor_id: number | null;
    doctor_name: string | null;
    total: number;
    no_show: number;
    no_show_rate: number;
  }[];
}

/** รูปแบบผลลัพธ์แบบแบ่งหน้าของ DRF */
export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

/** รูปแบบ error กลางของ backend */
export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
}
