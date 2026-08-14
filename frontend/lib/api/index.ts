/**
 * API client แยกตามโดเมน (หนึ่ง class ต่อหนึ่งกลุ่มงาน)
 *
 * ห่อการเรียก endpoint ไว้ในที่เดียว เพื่อไม่ให้ component ต้องจำ path ของ API
 * และเวลา backend เปลี่ยนสัญญา ก็แก้ที่ไฟล์นี้ไฟล์เดียว
 */
import { HttpClient, httpClient } from "@/lib/api/http";
import type {
  Appointment,
  AppointmentStatus,
  AvailableSlotsResponse,
  Clinic,
  Doctor,
  DoctorAvailability,
  DoctorSchedule,
  NoShowReport,
  Paginated,
  Patient,
  PatientHistory,
  PatientNote,
  QueueTodayResponse,
  ReportSummary,
  ServiceType,
  TimeBlock,
  User,
} from "@/types/api";

class BaseApiClient {
  constructor(protected readonly http: HttpClient = httpClient) {}
}

export class AuthApiClient extends BaseApiClient {
  /** ผู้ใช้ที่ล็อกอินอยู่ (ใช้กำหนดเมนู/สิทธิ์บนหน้าจอ) */
  me(): Promise<User> {
    return this.http.get<User>("/auth/me");
  }

  async login(email: string, password: string): Promise<User> {
    const response = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload?.detail ?? "อีเมลหรือรหัสผ่านไม่ถูกต้อง");
    }
    const payload = (await response.json()) as { user: User };
    return payload.user;
  }

  async logout(): Promise<void> {
    await fetch("/api/auth/logout", { method: "POST" });
  }

  changePassword(currentPassword: string, newPassword: string): Promise<void> {
    return this.http.post<void>("/auth/change-password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }
}

export class ClinicApiClient extends BaseApiClient {
  list(): Promise<Paginated<Clinic>> {
    return this.http.get<Paginated<Clinic>>("/clinics");
  }

  create(payload: Partial<Clinic>): Promise<Clinic> {
    return this.http.post<Clinic>("/clinics", payload);
  }

  update(clinicId: number, payload: Partial<Clinic>): Promise<Clinic> {
    return this.http.patch<Clinic>(`/clinics/${clinicId}`, payload);
  }
}

export class DoctorApiClient extends BaseApiClient {
  list(params: { clinic_id?: number; is_active?: boolean } = {}): Promise<Paginated<Doctor>> {
    return this.http.get<Paginated<Doctor>>("/doctors", params);
  }

  retrieve(doctorId: number): Promise<Doctor> {
    return this.http.get<Doctor>(`/doctors/${doctorId}`);
  }

  /** รับแพทย์ใหม่ — backend สร้างบัญชีล็อกอินและโปรไฟล์ให้พร้อมกันในคำสั่งเดียว */
  create(payload: {
    email: string;
    full_name: string;
    password: string;
    display_name: string;
    phone?: string;
    specialties?: string;
    color?: string;
    clinic_id?: number;
  }): Promise<Doctor> {
    return this.http.post<Doctor>("/doctors", payload);
  }

  update(doctorId: number, payload: Partial<Doctor>): Promise<Doctor> {
    return this.http.patch<Doctor>(`/doctors/${doctorId}`, payload);
  }

  schedules(doctorId?: number): Promise<Paginated<DoctorSchedule>> {
    return this.http.get<Paginated<DoctorSchedule>>("/doctors/schedules", {
      doctor_id: doctorId,
      page_size: 100,
    });
  }

  createSchedule(payload: {
    doctor: number;
    day_of_week: number;
    start_time: string;
    end_time: string;
  }): Promise<DoctorSchedule> {
    return this.http.post<DoctorSchedule>("/doctors/schedules", payload);
  }

  deleteSchedule(scheduleId: number): Promise<void> {
    return this.http.delete<void>(`/doctors/schedules/${scheduleId}`);
  }

  timeBlocks(params: { doctor_id?: number; date_from?: string; date_to?: string } = {}): Promise<
    Paginated<TimeBlock>
  > {
    return this.http.get<Paginated<TimeBlock>>("/doctors/time-blocks", params);
  }

  createTimeBlock(payload: {
    doctor: number;
    start_datetime: string;
    end_datetime: string;
    reason: string;
    note?: string;
    is_recurring?: boolean;
    recurrence?: "none" | "daily" | "weekly";
  }): Promise<TimeBlock> {
    return this.http.post<TimeBlock>("/doctors/time-blocks", payload);
  }

  deleteTimeBlock(timeBlockId: number): Promise<void> {
    return this.http.delete<void>(`/doctors/time-blocks/${timeBlockId}`);
  }

  availability(doctorId: number, date: string): Promise<DoctorAvailability> {
    return this.http.get<DoctorAvailability>(`/doctors/${doctorId}/availability`, { date });
  }
}

export class ServiceApiClient extends BaseApiClient {
  list(onlyActive = true): Promise<Paginated<ServiceType>> {
    return this.http.get<Paginated<ServiceType>>("/services", {
      is_active: onlyActive ? true : undefined,
      page_size: 200,
    });
  }
}

export class SchedulingApiClient extends BaseApiClient {
  /** ช่วงเวลาที่จองได้จริง — หน้าจอจองต้องเรียกอันนี้เสมอ ห้ามเดาเวลาว่างเอง */
  availableSlots(params: {
    service_id: number;
    date: string;
    doctor_id?: number;
    clinic_id?: number;
  }): Promise<AvailableSlotsResponse> {
    return this.http.get<AvailableSlotsResponse>("/scheduling/available-slots", params);
  }

  listAppointments(params: {
    date_from?: string;
    date_to?: string;
    doctor_id?: number;
    patient_id?: number;
    status?: string;
    clinic_id?: number;
    page_size?: number;
  }): Promise<Paginated<Appointment>> {
    return this.http.get<Paginated<Appointment>>("/scheduling/appointments", params);
  }

  book(payload: {
    patient: number;
    service_type: number;
    scheduled_start: string;
    doctor?: number | null;
    note?: string;
    clinic_id?: number;
  }): Promise<Appointment> {
    return this.http.post<Appointment>("/scheduling/appointments", payload);
  }
}

export class QueueApiClient extends BaseApiClient {
  today(params: { date?: string; doctor_id?: number; clinic_id?: number } = {}): Promise<QueueTodayResponse> {
    return this.http.get<QueueTodayResponse>("/queue/today", params);
  }

  walkIn(payload: {
    service_type: number;
    doctor?: number | null;
    patient?: number;
    new_patient?: {
      first_name: string;
      last_name?: string;
      phone: string;
    };
    note?: string;
    preferred_start?: string;
    clinic_id?: number;
  }): Promise<Appointment> {
    return this.http.post<Appointment>("/queue/walk-in", payload);
  }

  changeStatus(
    appointmentId: number,
    status: AppointmentStatus,
    cancelledReason = "",
  ): Promise<Appointment> {
    return this.http.patch<Appointment>(`/queue/appointments/${appointmentId}/status`, {
      status,
      cancelled_reason: cancelledReason,
    });
  }

  reschedule(
    appointmentId: number,
    scheduledStart: string,
    doctorId?: number | null,
  ): Promise<Appointment> {
    return this.http.patch<Appointment>(`/queue/appointments/${appointmentId}/reschedule`, {
      scheduled_start: scheduledStart,
      doctor: doctorId ?? undefined,
    });
  }
}

export class PatientApiClient extends BaseApiClient {
  search(query: string, limit = 20): Promise<Patient[]> {
    return this.http.get<Patient[]>("/patients/search", { q: query, limit });
  }

  list(params: { phone?: string; page?: number } = {}): Promise<Paginated<Patient>> {
    return this.http.get<Paginated<Patient>>("/patients", params);
  }

  retrieve(patientId: number): Promise<Patient> {
    return this.http.get<Patient>(`/patients/${patientId}`);
  }

  create(payload: {
    first_name: string;
    last_name?: string;
    phone: string;
    date_of_birth?: string | null;
    gender?: string;
    /** สาขาที่คนไข้ลงทะเบียน — Super Admin ต้องระบุ ผู้ใช้ทั่วไป backend เติมให้เอง */
    clinic_id?: number;
  }): Promise<Patient> {
    return this.http.post<Patient>("/patients", payload);
  }

  update(patientId: number, payload: Partial<Patient>): Promise<Patient> {
    return this.http.patch<Patient>(`/patients/${patientId}`, payload);
  }

  history(patientId: number): Promise<PatientHistory> {
    return this.http.get<PatientHistory>(`/patients/${patientId}/history`);
  }

  notes(patientId: number): Promise<PatientNote[]> {
    return this.http.get<PatientNote[]>(`/patients/${patientId}/notes`);
  }

  addNote(patientId: number, noteText: string, isPinned = false): Promise<PatientNote> {
    return this.http.post<PatientNote>(`/patients/${patientId}/notes`, {
      note_text: noteText,
      is_pinned: isPinned,
    });
  }
}

export class ReportApiClient extends BaseApiClient {
  summary(params: {
    period?: "daily" | "monthly";
    date_from?: string;
    date_to?: string;
    doctor_id?: number;
    clinic_id?: number;
  }): Promise<ReportSummary> {
    return this.http.get<ReportSummary>("/reports/summary", params);
  }

  noShowRate(params: {
    date_from?: string;
    date_to?: string;
    doctor_id?: number;
    clinic_id?: number;
  }): Promise<NoShowReport> {
    return this.http.get<NoShowReport>("/reports/no-show-rate", params);
  }
}

export const authApi = new AuthApiClient();
export const clinicApi = new ClinicApiClient();
export const doctorApi = new DoctorApiClient();
export const serviceApi = new ServiceApiClient();
export const schedulingApi = new SchedulingApiClient();
export const queueApi = new QueueApiClient();
export const patientApi = new PatientApiClient();
export const reportApi = new ReportApiClient();

export { ApiError } from "@/lib/api/http";
