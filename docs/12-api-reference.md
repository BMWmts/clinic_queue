# 12 — สรุป API ทั้งหมด + ไฟล์ที่รับผิดชอบ / Endpoint → file map

**TH:** ตารางนี้ตอบคำถาม *"endpoint นี้โค้ดอยู่ไฟล์ไหน และใครฝั่ง frontend เป็นคนเรียก"*
สัญญาฉบับเต็ม (field ทุกตัว) ดูที่ `/api/docs/` (Swagger) หรือ `/api/schema/` (OpenAPI)

**EN:** This table answers *"which file implements this endpoint, and who on the frontend calls it?"*
The full contract lives at `/api/docs/` (Swagger) or `/api/schema/` (OpenAPI).

---

## 🔑 กติกาที่ใช้กับ **ทุก** endpoint / rules that apply everywhere

| กฎ (TH) | Rule (EN) |
|---|---|
| ต้อง login เสมอ ยกเว้น `login/` และ `refresh/` | Authentication required except for `login/` and `refresh/` |
| ข้อมูลถูกกรองตามสาขาของผู้ใช้ (ยกเว้น Super Admin และการค้นหาคนไข้) 🔒 | Data is branch-scoped 🔒 (except Super Admin and patient search) |
| Super Admin ต้องระบุ `?clinic_id=` เมื่อทำงานที่ต้องอ้างอิงสาขา | Super Admin must pass `?clinic_id=` for branch-bound operations |
| error มีรูปแบบเดียว: `{"error":{"code","message","details?"}}` | One error shape everywhere |
| list endpoint แบ่งหน้า: `?page=`, `?page_size=` (สูงสุด 200) | List endpoints are paginated |

---

## 1. Auth — `/api/auth/`

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| `POST /login/` | เข้าสู่ระบบ (มี rate limit 🔒) | Log in (rate-limited 🔒) | `accounts/views.LoginView` | `app/api/auth/login/route.ts` |
| `POST /refresh/` | ขอ access ใหม่ + blacklist ใบเก่า | Rotate tokens | `accounts/views.RefreshView` | `app/api/proxy/[...path]/route.ts` |
| `POST /logout/` | blacklist refresh token | Revoke session | `accounts/views.LogoutView` | `app/api/auth/logout/route.ts` |
| `GET /me/` | ข้อมูลผู้ใช้ปัจจุบัน | Current user | `accounts/views.MeView` | `AuthApiClient.me()` |
| `POST /change-password/` | เปลี่ยนรหัสผ่านตัวเอง | Change own password | `accounts/views.ChangePasswordView` | `AuthApiClient.changePassword()` |
| `GET/POST/PATCH /users/` | จัดการบัญชี (ผู้จัดการขึ้นไป 🔒) | User management (managers 🔒) | `accounts/views.UserViewSet` | — |

---

## 2. Clinics — `/api/clinics/`

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| `GET /` | รายการสาขา (role อื่นเห็นเฉพาะของตัวเอง) | List branches | `clinics/views.ClinicViewSet` | `ClinicApiClient.list()` |
| `POST /` `PATCH /{id}/` | เพิ่ม/แก้สาขา (**Super Admin เท่านั้น** 🔒) | Create/update (**Super Admin only** 🔒) | เดียวกัน | `ClinicApiClient.create/update()` |

---

## 3. Doctors — `/api/doctors/`

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| `GET /?is_active=` | รายชื่อแพทย์ในสาขา | Doctors in the branch | `doctors/views.DoctorViewSet` | `DoctorApiClient.list()` |
| `GET /{id}/availability/?date=` | ตารางทำงาน + ช่วงที่ถูกบล็อก (**ยังไม่หักคิว**) | Working + blocked windows (**bookings not deducted**) | `DoctorViewSet.availability` | `DoctorApiClient.availability()` |
| `GET/POST/PATCH/DELETE /schedules/` | ตารางออกตรวจประจำสัปดาห์ | Weekly schedules | `DoctorScheduleViewSet` | `DoctorApiClient.schedules()` |
| `GET/POST/PATCH/DELETE /time-blocks/` | ช่วงเวลาที่ถูกบล็อก | Time blocks | `TimeBlockViewSet` | `DoctorApiClient.timeBlocks()` |

**⚠️ อย่าสับสน:** `availability/` = ตารางดิบสำหรับวาดปฏิทิน · `available-slots/` = เวลาที่จองได้จริง
**⚠️ Don't confuse them:** the former paints the calendar; the latter is what you may book.

---

## 4. Services — `/api/services/`

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| `GET /?is_active=&category=&q=` | แคตตาล็อกบริการ (ทุก role อ่านได้) | Service catalog (readable by all) | `services/views.ServiceTypeViewSet` | `ServiceApiClient.list()` |
| `POST/PATCH/DELETE /` | จัดการบริการ (ผู้จัดการขึ้นไป 🔒) | Manage services (managers 🔒) | เดียวกัน | — |

---

## 5. Scheduling — `/api/scheduling/` ★

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| ★ `GET /available-slots/?service_id=&doctor_id=&date=` | **เวลาที่จองได้จริง** (หัก TimeBlock + คิวแล้ว) | **Genuinely bookable slots** | `scheduling/views.AvailableSlotsView` → `SlotAvailabilityService` | `SchedulingApiClient.availableSlots()` |
| ★ `POST /appointments/` | สร้างการจอง — **409 ถ้าไม่ว่างจริง** | Create a booking — **409 when unavailable** | `AppointmentViewSet.create` → `AppointmentBookingService.book()` | `SchedulingApiClient.book()` |
| `GET /appointments/?doctor_id=&patient_id=&status=&date_from=&date_to=` | รายการคิว (แพทย์เห็นเฉพาะของตัวเอง 🔒) | List appointments (doctors see only theirs 🔒) | `AppointmentViewSet.list` | `SchedulingApiClient.listAppointments()` |

**Response ของ `available-slots/`:**
```json
{ "clinic_id": 1, "timezone": "Asia/Bangkok", "date": "2026-08-20",
  "service_id": 3, "duration_minutes": 30, "doctor_id": 2,
  "slots": [{"start": "2026-08-20T09:00:00+07:00", "end": "2026-08-20T09:30:00+07:00"}] }
```

**🔑 `POST /appointments/` ไม่รับ `scheduled_end` และ `clinic`** — ระบบคำนวณ/กำหนดเองทั้งคู่ 🔒

---

## 6. Queue — `/api/queue/`

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| `GET /today/?date=&doctor_id=` | คิวของวัน + สรุปจำนวน | The day's queue + summary | `queue/views.TodayQueueView` | `QueueApiClient.today()` |
| ★ `POST /walk-in/` | รับ walk-in — **409 ถ้าไม่มี slot ว่าง** | Add walk-in — **409 when full** | `queue/views.WalkInView` | `QueueApiClient.walkIn()` |
| `PATCH /appointments/{id}/status/` | เปลี่ยนสถานะ (ตาม state machine) | Change status | `AppointmentStatusUpdateView` | `QueueApiClient.changeStatus()` |
| `PATCH /appointments/{id}/reschedule/` | เลื่อน/สลับเวลา | Reschedule | `AppointmentRescheduleView` | `QueueApiClient.reschedule()` |
| `WS /ws/queue/{clinic_id}/?token=` | อัปเดตแบบเรียลไทม์ | Realtime updates | `queue/consumers.QueueConsumer` | `lib/hooks/useQueueBoard.ts` |

**Response ของ `today/`:**
```json
{ "clinic_id": 1, "date": "2026-08-15", "timezone": "Asia/Bangkok",
  "summary": {"total": 12, "booked": 3, "checked_in": 2, "...": 0},
  "appointments": [ /* AppointmentSerializer */ ] }
```

**WebSocket event:** `{"event": "appointment_status_changed", "payload": { /* Appointment */ }}`
**รหัสปิดการเชื่อมต่อ / close codes:** `4401` = ไม่ได้ยืนยันตัวตน · `4403` = ไม่มีสิทธิ์เข้าสาขานี้ 🔒

---

## 7. Patients — `/api/patients/`

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| `GET /search/?q=&limit=` | ค้นหา **ข้ามสาขา** (เบอร์/ชื่อ/รหัส) | **Cross-branch** search | `PatientViewSet.search` → `PatientSearchService` | `PatientApiClient.search()` |
| `GET/POST/PATCH /` `/{id}/` | CRUD คนไข้ (รหัสสร้างอัตโนมัติ) | Patient CRUD (auto code) | `PatientViewSet` | `PatientApiClient.*` |
| `GET/POST /{id}/notes/` | อ่าน/เพิ่มโน้ต | Read/add notes | `PatientViewSet.notes` | `PatientApiClient.notes/addNote()` |
| `GET /{id}/history/` | ประวัติการจองทั้งหมด | Full booking history | `PatientViewSet.history` | `PatientApiClient.history()` |

**🔑 ค้นหาคนไข้ไม่ถูกจำกัดตามสาขาโดยเจตนา** (ข้อกำหนดข้อ 4.8) แต่การสร้างผูกกับสาขาผู้ใช้เสมอ
**🔑** Patient search is intentionally cross-branch (spec §4.8); creation still binds to the user's branch.

---

## 8. Reports — `/api/reports/` 🔒 (ผู้จัดการขึ้นไป / managers and above)

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend | Frontend |
|---|---|---|---|---|
| `GET /summary/?period=daily\|monthly&date_from=&date_to=&doctor_id=` | ยอดจอง, series, heatmap, แยกตามบริการ/แพทย์, เวลารอเฉลี่ย | Totals, series, heatmap, breakdowns, average wait | `reports/views.SummaryReportView` | `ReportApiClient.summary()` |
| `GET /no-show-rate/?date_from=&date_to=&doctor_id=` | อัตราผิดนัดรวม + รายแพทย์ | No-show rate overall and per doctor | `NoShowRateReportView` | `ReportApiClient.noShowRate()` |

**🔑 ค่าเริ่มต้น = ย้อนหลัง 30 วัน · เพดาน 366 วันต่อคำขอ**

---

## 9. Notifications — `/api/notifications/` 🔒 (ผู้จัดการขึ้นไป)

| Method + Path | หน้าที่ (TH) | Role (EN) | Backend |
|---|---|---|---|
| `GET /sms-logs/?status=&appointment_id=` | ประวัติการส่ง SMS (**อ่านอย่างเดียว**, เบอร์ถูกปิดบัง 🔒) | SMS history (**read-only**, masked phone 🔒) | `notifications/views.SMSLogViewSet` |

---

## 10. เอกสารและ admin / Docs & admin

| Path | คืออะไร / What |
|---|---|
| `/api/schema/` | OpenAPI schema (drf-spectacular) |
| `/api/docs/` | Swagger UI |
| `/admin/` | Django admin — สำหรับตั้งค่าเริ่มต้นเท่านั้น / initial setup only |

---

## 11. รหัส error ทั้งหมด / All error codes

| Code | HTTP | ความหมาย (TH) | Meaning (EN) | ฝั่ง frontend จัดการอย่างไร |
|---|---|---|---|---|
| `slot_unavailable` | 409 | ไม่มีเวลาว่างจริง | No genuinely free slot | `ApiError.isSlotConflict` → แจ้งให้เลือกเวลา/แพทย์อื่น + โหลด slot ใหม่ |
| `booking_conflict` | 409 | เพิ่งถูกจองไปพอดี | Just taken | เหมือนกัน / same |
| `invalid_status_transition` | 409 | เปลี่ยนสถานะข้ามขั้น | Illegal status jump | แสดงข้อความจาก backend |
| `branch_access_denied` | 403 | แตะข้อมูลข้ามสาขา 🔒 | Cross-branch attempt 🔒 | แสดงข้อความ |
| `validation_error` | 400 | ข้อมูลไม่ผ่าน validation | Validation failed | แสดงราย field |
| `session_expired` | 401 | เซสชันหมดอายุ | Session expired | `ApiError.isSessionExpired` → กลับหน้า login |
| `refresh_required` / `invalid_refresh` | 400/401 | refresh token หาย/ใช้ไม่ได้ | Missing/invalid refresh token | ล้าง cookie แล้วกลับหน้า login |
