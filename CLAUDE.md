# CLAUDE.md — ระบบจองคิวคลินิกออนไลน์ (Clinic Queue Booking System)

เอกสารนี้เป็น context หลักสำหรับ Claude Code ใช้ในการสร้างโปรเจกต์ระบบจองคิวคลินิก
อ่านเอกสารนี้ทั้งหมดก่อนเริ่มเขียนโค้ด และยึดตามสถาปัตยกรรม/แบบแผนที่ระบุไว้เพื่อความสอดคล้องกันตลอดโปรเจกต์

---

## 1. ภาพรวมโปรเจกต์ (Project Overview)

ระบบจัดการคิวและการนัดหมายสำหรับคลินิกความงาม/คลินิกทั่วไป **เป็นระบบหลังบ้าน (internal/back-office) สำหรับเจ้าหน้าที่และแพทย์เท่านั้น ไม่มีหน้าเว็บสาธารณะให้ลูกค้าจองเอง** รองรับ:
- **หลายสาขา (Multi-branch / Multi-tenant)** — ผู้ใช้แต่ละคนสังกัดสาขาใดสาขาหนึ่ง, ข้อมูล (ตารางแพทย์, คิว, คนไข้) แยกตามสาขา แต่ Super Admin มองเห็น/บริหารได้ทุกสาขา
- การจองคิวโดยเจ้าหน้าที่ (staff-created) เท่านั้น
- การจัดตารางเวลาแพทย์และประเภทบริการ
- แดชบอร์ดคิวแบบเรียลไทม์สำหรับหน้างาน (front desk)
- ฐานข้อมูลลูกค้า/คนไข้พร้อมประวัติ
- แจ้งเตือนคนไข้ผ่าน SMS
- รายงานสถิติเชิงบริหาร

**กลุ่มผู้ใช้งาน (User Roles):** — ทุก role คือ "ผู้ใช้งานภายในคลินิก" ไม่มี role ของลูกค้า/คนไข้ในระบบนี้

| Role | สิทธิ์การใช้งาน |
|---|---|
| Super Admin | จัดการทั้งระบบ, มองเห็น/บริหารได้ทุกสาขา, ตั้งค่าคลินิก, จัดการ user ทุก role |
| Admin/ผู้จัดการสาขา | จัดการตารางแพทย์และเจ้าหน้าที่ในสาขาตัวเอง, ดูรายงาน, จัดการบริการ |
| เจ้าหน้าที่ (Staff/Front desk) | จัดการคิว, walk-in, ค้นหา/บันทึกข้อมูลลูกค้า — เฉพาะสาขาตัวเอง |
| แพทย์ (Doctor) | ดูตารางตัวเอง, อัปเดตสถานะคนไข้, บันทึกโน้ต |

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, TailwindCSS |
| Backend | Python Django + Django REST Framework (DRF) |
| Database | PostgreSQL |
| Auth | Django + JWT (djangorestframework-simplejwt), httpOnly cookie สำหรับ frontend |
| Realtime (คิว dashboard) | Django Channels (WebSocket) หรือ polling ทุก 5–10 วินาที (เลือก WebSocket ถ้าเวลาเอื้อ) |
| Task Queue (แจ้งเตือน/reminder) | Celery + Redis (ส่ง SMS แจ้งเตือนนัดหมาย ผ่าน SMS Gateway provider เช่น Thai Bulk SMS / Twilio — เลือก provider ตอน implement) |
| Deployment | Docker Compose (dev), แยก service: frontend / backend / db / redis |

**เหตุผลของสถาปัตยกรรม:** แยก Frontend (Next.js) และ Backend (Django REST API) ออกจากกันอย่างชัดเจน สื่อสารผ่าน REST API (+WebSocket สำหรับคิวเรียลไทม์) เพื่อให้ scale และดูแลรักษาง่าย

---

## 3. โครงสร้างโปรเจกต์ (Monorepo Structure)

```
clinic-queue-system/
├── backend/                      # Django project
│   ├── config/                   # settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── accounts/             # user, auth, roles
│   │   ├── clinics/               # clinic, branch settings
│   │   ├── doctors/              # doctor profile, working hours, time-off
│   │   ├── services/             # ประเภทบริการ + ระยะเวลา
│   │   ├── scheduling/           # slot generation, booking, block time
│   │   ├── queue/                # queue dashboard, walk-in, status
│   │   ├── patients/             # customer/patient database + notes
│   │   ├── reports/              # aggregation/report endpoints
│   │   └── notifications/        # SMS reminder (Celery tasks)
│   ├── manage.py
│   └── requirements.txt
├── frontend/                     # Next.js project — ระบบหลังบ้านเท่านั้น ไม่มีหน้าจองสาธารณะ
│   ├── app/
│   │   ├── (auth)/login
│   │   └── (dashboard)/
│   │       ├── queue/            # หน้าจอคิววันนี้
│   │       ├── calendar/         # ปฏิทิน/ตารางแพทย์
│   │       ├── patients/         # ค้นหา/จัดการคนไข้
│   │       ├── branches/         # (Super Admin/Admin) จัดการสาขา — เฉพาะ role ที่มีสิทธิ์
│   │       └── reports/
│   ├── components/
│   ├── lib/api/                  # api client (fetch wrapper)
│   └── types/
├── docker-compose.yml
└── CLAUDE.md
```

---

## 4. Data Model (หลัก — ออกแบบใน Django models)

### 4.1 accounts.User
- id, email, phone, password, role (super_admin/admin/staff/doctor), is_active, clinic (FK)

### 4.2 clinics.Clinic / Branch
- ชื่อสาขา, ที่อยู่, เวลาเปิด-ปิดคลินิก, timezone
- **ระบบเป็น multi-branch:** User, Doctor, Appointment, DoctorSchedule, TimeBlock ทุกตัวผูกกับ `clinic` (สาขา) ผ่าน FK — เจ้าหน้าที่/แพทย์แต่ละคนเห็นเฉพาะข้อมูลสาขาตัวเอง (filter ด้วย `request.user.clinic` ใน backend permission/queryset เสมอ) ยกเว้น Super Admin ที่ query ข้าม clinic ได้ทั้งหมด

### 4.3 doctors.Doctor
- user (FK), clinic (FK), specialties, ชื่อที่แสดง, สี (สำหรับปฏิทิน)

### 4.4 doctors.DoctorSchedule (ตารางออกตรวจประจำ)
- doctor (FK), day_of_week, start_time, end_time, is_active
- ใช้ generate available slot ล่วงหน้า (เช่น recurring weekly pattern)

### 4.5 doctors.TimeBlock (บล็อกเวลาพิเศษ)
- doctor (FK), start_datetime, end_datetime, reason (พักเที่ยง/เคสด่วน/ลา), is_recurring

### 4.6 services.ServiceType (ประเภทบริการ)
- ชื่อบริการ (เช่น ฉีดโบลดริ้วรอย, ดริปผิว), duration_minutes, price, category, requires_doctor (bool)

### 4.7 scheduling.Appointment (การจอง/คิว)
- patient (FK), doctor (FK), service_type (FK), clinic (FK)
- scheduled_start, scheduled_end (คำนวณจาก duration ของ service_type)
- status: `booked` | `confirmed` | `checked_in` | `in_progress` | `completed` | `cancelled` | `no_show`
- source: `walk_in` | `staff_created` (ไม่มี `online` เพราะระบบไม่มีหน้าจองสาธารณะ — ทุกการจองสร้างโดยเจ้าหน้าที่เท่านั้น)
- note (short note เช่น "แพ้ยาชา")
- created_by (FK User), created_at, updated_at

**Constraint สำคัญ:**
- ป้องกันคิวชนกัน — unique/overlap validation ระดับ database + application layer (เช่น exclusion constraint หรือเช็คช่วงเวลาซ้อนทับก่อน save ใน serializer/service layer)
- **ห้าม overbook เด็ดขาด:** รวมถึงคิว walk-in ด้วย — ถ้าไม่มี slot ว่างจริงตาม `DoctorSchedule`/`TimeBlock`/capacity ที่กำหนด ระบบต้อง reject การสร้าง appointment (ทั้งจองปกติและ walk-in) ไม่อนุญาตให้ยัดคิวเกิน capacity ไม่ว่ากรณีใด

### 4.8 patients.Patient
- ชื่อ-สกุล, เบอร์โทร (index สำหรับค้นหาเร็ว), patient_code (auto-generated, unique), วันเกิด, เพศ
- `home_clinic` (FK, สาขาที่ลงทะเบียนครั้งแรก) — แต่ค้นหา/จองคิวข้ามสาขาได้ (คนไข้คนเดียวกันไปหลายสาขาได้ ใช้เบอร์โทรเป็นตัวจับคู่ข้อมูลเดิม) เพื่อไม่ให้ต้องสร้าง record ซ้ำเวลาลูกค้าไปคนละสาขา

### 4.9 patients.PatientNote
- patient (FK), appointment (FK, nullable), note_text, created_by (FK User), created_at
- ใช้เก็บโน้ตสะสม เช่น "แพ้ยาชา", "ขอหมอคนเดิม"

### 4.10 reports (ไม่ต้องมี model แยก — ใช้ aggregate query จาก Appointment)

---

## 5. Feature Breakdown & API Requirements

### 5.1 ระบบจัดการตารางเวลา (Calendar & Scheduling)
- [ ] CRUD `DoctorSchedule` (ตารางออกตรวจประจำสัปดาห์ต่อแพทย์)
- [ ] CRUD `TimeBlock` (บล็อกเวลาพิเศษ, รองรับ recurring เช่น พักเที่ยงทุกวัน)
- [ ] Endpoint `GET /api/scheduling/available-slots/?doctor_id=&service_id=&date=`
      → คำนวณช่วงเวลาว่างจริง โดยหัก TimeBlock และ Appointment ที่จองแล้วออก, slot ยาวตาม `service_type.duration_minutes`
- [ ] Endpoint `POST /api/scheduling/appointments/` → สร้างการจอง พร้อม validate ไม่ให้เวลาชนกัน (server-side, ไม่พึ่ง frontend อย่างเดียว)
- [ ] CRUD `ServiceType`

### 5.2 ระบบจัดการคิวและหน้าจอพนักงาน (Queue Dashboard)
- [ ] `GET /api/queue/today/?clinic_id=&doctor_id=` → รายชื่อคิววันนี้ เรียงตามเวลา พร้อมสถานะ
- [ ] `POST /api/queue/walk-in/` → เพิ่มคิว walk-in แทรกเข้าตารางปัจจุบันได้ทันที **เฉพาะเมื่อมี slot ว่างจริงเท่านั้น** — ห้าม overbook, ถ้าไม่มี slot ว่างให้ระบบแจ้งเตือนและปฏิเสธ (staff ต้องเลือกเวลาอื่นหรือแพทย์ท่านอื่นแทน)
- [ ] `PATCH /api/queue/appointments/{id}/status/` → เปลี่ยนสถานะ (รอพบแพทย์ → กำลังรักษา → เสร็จสิ้น / ไม่มา)
- [ ] `PATCH /api/queue/appointments/{id}/reschedule/` → เลื่อน/สลับเวลาคิว (drag-and-drop ฝั่ง frontend เรียก endpoint นี้)
- [ ] Realtime update: WebSocket channel `queue_updates_{clinic_id}` broadcast ทุกครั้งที่มีการเปลี่ยนสถานะ/เพิ่มคิว
  - ถ้าไม่ทำ WebSocket ในเฟสแรก ให้ frontend poll ทุก 5–10 วิ

### 5.3 ระบบฐานข้อมูลลูกค้า (Customer & Patient Management)
- [ ] `GET /api/patients/search/?q=` → ค้นหาด้วยเบอร์โทร/ชื่อ/รหัสคนไข้ (ใช้ index + trigram search ถ้าข้อมูลเยอะ)
- [ ] CRUD `Patient`
- [ ] `POST /api/patients/{id}/notes/` → เพิ่มโน้ตย่อ
- [ ] `GET /api/patients/{id}/history/` → ประวัติการจองทั้งหมดของคนไข้

### 5.4 ระบบรายงาน (Reports)
- [ ] `GET /api/reports/summary/?period=daily|monthly&date_from=&date_to=` → สรุปยอดจอง, breakdown ตามช่วงเวลา (peak time heatmap ตามชั่วโมง/วัน)
- [ ] `GET /api/reports/no-show-rate/?date_from=&date_to=&doctor_id=` → อัตราการผิดนัด (no_show / total booked)
- [ ] ควรใช้ Django ORM aggregation (`annotate`, `Count`, `Case/When`) ไม่ query ดิบใน view

### 5.5 ระบบแจ้งเตือนคนไข้ (SMS Notification)
- [ ] Celery task ส่ง SMS แจ้งเตือนนัดหมายล่วงหน้า (เช่น ก่อนนัด 1 วัน) ผ่าน SMS Gateway provider
- [ ] เก็บ log การส่ง SMS (`notifications.SMSLog`: patient, appointment FK, message, status: sent/failed, sent_at) เพื่อตรวจสอบย้อนหลังได้
- [ ] Config เบอร์/ผู้ให้บริการ SMS ต่อสาขาได้ (เผื่อบางสาขาใช้ provider คนละเจ้า) — เก็บใน Clinic settings

### 5.6 ระบบ Login / Auth
- [ ] `POST /api/auth/login/` → JWT (access + refresh), เก็บ refresh token เป็น httpOnly cookie
- [ ] `POST /api/auth/refresh/`
- [ ] `POST /api/auth/logout/`
- [ ] Role-based permission (DRF `permissions.BasePermission` custom class ต่อ role)
- [ ] **Branch-scoped permission:** ทุก queryset ของ Admin/Staff/Doctor ต้อง filter ด้วย `clinic` ของ user ที่ login อยู่เสมอ (ห้ามเห็น/แก้ข้อมูลข้ามสาขาโดยไม่ได้ตั้งใจ) — ยกเว้น Super Admin
- [ ] Frontend: middleware ของ Next.js เช็ค session ก่อนเข้าหน้า dashboard, redirect ไป `/login` ถ้าไม่ได้ login

---

## 6. Non-Functional Requirements

- **Timezone:** ใช้ Asia/Bangkok เป็นมาตรฐาน ทุก datetime เก็บใน DB เป็น UTC แล้วแปลงตอนแสดงผล
- **Validation การชนกันของคิว:** ต้องเช็คที่ backend เสมอ (ห้ามเชื่อ frontend อย่างเดียว) — ใช้ transaction + select_for_update เพื่อป้องกัน race condition ตอนจองพร้อมกัน
- **Audit trail:** เก็บ `created_by`, `updated_at` ทุกตารางสำคัญ เพื่อ trace ว่าใครแก้ไขคิว
- **Performance:** index บน `phone`, `patient_code`, `scheduled_start` ของ Appointment
- **Security:** input validation ทุก endpoint, rate limit บน login, ไม่เก็บ password plain text (Django หนึ่งจัดการ hashing ให้อยู่แล้ว)

---

## 7. ข้อกำหนดสำคัญ: ห้ามใช้ Mock Data

**ห้ามสร้างข้อมูลจำลอง (mock data) หรือ hardcode ข้อมูลปลอมไว้ในโค้ดทั้งฝั่ง frontend และ backend**
ให้เชื่อมต่อกับฐานข้อมูลจริงและ API จริงตั้งแต่ต้น ตามรายละเอียดดังนี้:

- **Frontend:** ห้ามใช้ mock JSON, fixture, หรือ fake API response ใด ๆ — ทุกหน้าต้องเรียก API จาก backend จริงผ่าน `lib/api/` เท่านั้น (รวมถึงตอน dev ก็ให้รัน backend คู่กันเสมอ ไม่ใช้ mock server)
- **Backend:** ห้ามสร้าง endpoint ที่ return ข้อมูล hardcode/ตัวอย่างไว้ถาวร — ทุก endpoint ต้อง query จาก PostgreSQL จริง
- **Database:** ถ้าต้องการข้อมูลไว้ทดสอบระหว่างพัฒนา ให้ใช้ Django migration + seed script (management command เช่น `python manage.py seed_dev_data`) ที่รันแยกต่างหาก ไม่ผูกติดกับ business logic และต้องลบ/ปิดการใช้งานได้ง่ายก่อนขึ้น production — ห้ามฝัง mock data ปนอยู่ในโค้ด logic หลัก
- **Testing:** unit test/integration test สามารถใช้ test fixture ได้ตามปกติ (เพราะเป็นส่วนของการทดสอบ ไม่ใช่ตัวระบบจริง) แต่ต้องแยก scope ชัดเจนจากโค้ด production

เป้าหมายคือให้ทุกฟีเจอร์ที่สร้างเสร็จแล้ว **ใช้งานได้จริงกับข้อมูลจริงทันที** ไม่ต้องแก้จาก mock เป็นของจริงภายหลัง

---

## 8. มาตรฐานการเขียนโค้ด: อ่านง่าย ปลอดภัย และเป็น OOP

โค้ดทุกส่วนของระบบนี้ต้องเขียนให้ **มนุษย์อ่านและแก้ไขต่อได้ในอนาคต** ไม่ใช่แค่ทำงานได้ ยึดหลักดังนี้:

### 8.1 อ่านง่าย (Readable)
- ตั้งชื่อ function/class/variable ให้สื่อความหมายชัดเจน เต็มคำ ไม่ย่อจนเดาไม่ออก (เช่น `calculate_available_slots()` ไม่ใช่ `calcAvSlt()`)
- 1 function ทำหน้าที่เดียว (Single Responsibility) — ถ้า function ยาวเกิน ~30-40 บรรทัด หรือทำหลายอย่างในตัวเดียว ให้แตกออกเป็น function ย่อย
- ใส่ docstring/comment อธิบาย "ทำไม" (why) ไม่ใช่แค่ "ทำอะไร" (what) โดยเฉพาะ business logic ที่ซับซ้อน เช่น การคำนวณ slot ว่าง หรือการเช็คคิวชนกัน
- ใช้ type hints ทุกที่ (Python: type annotation ครบทุก function signature, TypeScript: ห้ามใช้ `any` พร่ำเพรื่อ ต้องกำหนด type/interface ชัดเจน)
- โครงสร้างไฟล์/โฟลเดอร์ต้องสอดคล้องกับหมวด 3 เสมอ ไม่ปนกันข้าม concern (เช่น อย่าเอา business logic ไปแปะใน view ตรง ๆ)

### 8.2 ปลอดภัย (Secure by Default)
- Validate และ sanitize input ทุกจุดที่รับข้อมูลจากผู้ใช้ (serializer-level validation ฝั่ง Django, form validation ฝั่ง Next.js) ห้ามเชื่อ input จาก client โดยไม่เช็คซ้ำที่ backend
- ใช้ Django ORM เท่านั้นในการ query ห้ามเขียน raw SQL แบบ string concatenation (ป้องกัน SQL Injection) ถ้าจำเป็นต้องใช้ raw query ให้ใช้ parameterized query เท่านั้น
- ทุก endpoint ต้องผ่าน authentication + role-based permission check ก่อนเข้าถึงข้อมูล (ตามหมวด 5.6/branch-scoped permission) ห้ามมี endpoint ที่เปิดให้เข้าถึงข้อมูลได้โดยไม่เช็คสิทธิ์
- ห้าม log หรือแสดงข้อมูลอ่อนไหว (password, token, เบอร์โทร/ข้อมูลคนไข้แบบเต็ม) ใน console log หรือ error message ที่ส่งกลับไป frontend
- Secrets/API keys (SMS gateway, database credential) ต้องเก็บใน environment variable เท่านั้น ห้าม hardcode ในโค้ดหรือ commit ลง git
- ป้องกัน XSS ฝั่ง frontend ด้วยการไม่ใช้ `dangerouslySetInnerHTML` กับข้อมูลที่มาจากผู้ใช้โดยไม่ sanitize ก่อน

### 8.3 เขียนแบบ OOP (Object-Oriented, เพื่อให้แก้ไข/ต่อยอดง่าย)
- **Backend (Django):** ใช้หลัก OOP ผ่าน class-based design ดังนี้
  - Business logic แต่ละโดเมน (scheduling, queue, patients, reports) ให้ห่อเป็น **Service class** ใน `services.py` (เช่น `AppointmentBookingService`, `SlotAvailabilityService`) ที่มี method ชัดเจนต่อ action หนึ่ง ไม่ใช่เขียน function ลอย ๆ กระจัดกระจาย
  - ใช้ Django Model methods/properties สำหรับ logic ที่ผูกกับ entity นั้นโดยตรง (เช่น `Appointment.overlaps_with()`) เพื่อให้ logic อยู่ใกล้ข้อมูลที่มันเกี่ยวข้อง
  - ใช้ DRF ViewSets/Serializers ตามหลัก OOP ของ framework อยู่แล้ว (inheritance สำหรับ permission/mixin ที่ใช้ซ้ำ เช่น `BranchScopedQuerySetMixin`)
  - หลีกเลี่ยงการเขียน logic ซ้ำ ๆ ในหลายที่ — ถ้าเห็น pattern ซ้ำ ให้ดึงขึ้นเป็น base class หรือ mixin
- **Frontend (Next.js/TypeScript):** เน้นความชัดเจนของโครงสร้างมากกว่า OOP แบบเข้มงวด (เพราะ React เป็น component-based) แต่ให้ยึดหลักการเดียวกัน:
  - แยก API client เป็น class หรือ module ที่ห่อ logic การเรียก API แต่ละโดเมนไว้ด้วยกัน (เช่น `class PatientApiClient { search(); getHistory(); addNote(); }`) แทนการเรียก `fetch()` กระจัดกระจายในแต่ละ component
  - แยก business/formatting logic ออกจาก UI component ไปไว้ใน `lib/` หรือ custom hooks เพื่อให้ทดสอบและแก้ไขได้อิสระจาก UI
- เป้าหมายของหลักการนี้คือให้เวลามีคนมาแก้ไขหรือเพิ่มฟีเจอร์ในอนาคต **หาโค้ดที่เกี่ยวข้องเจอง่าย แก้จุดเดียวไม่กระทบส่วนอื่น และเข้าใจ logic ได้โดยไม่ต้องถามคนเขียนเดิม**

---

## 9. Development Conventions

- **Backend:** ใช้ Django REST Framework ViewSets + Serializers, business logic แยกไปไว้ใน `services.py` ของแต่ละ app (อย่าเขียน logic หนักในของ view/serializer โดยตรง)
- **Frontend:** ใช้ Server Components สำหรับหน้าที่ไม่ต้อง interactive มาก, Client Components เฉพาะส่วนที่ต้องใช้ state (เช่น drag-and-drop คิว)
- **API contract:** ให้ backend สร้าง OpenAPI schema (drf-spectacular) เพื่อ frontend generate type ได้ตรงกัน
- **Testing:** เขียน unit test ฝั่ง backend สำหรับ logic การคำนวณ slot ว่าง และการเช็คคิวชนกัน เป็นอันดับแรก เพราะเป็นหัวใจของระบบ
- **Migrations:** ทุกการเปลี่ยน model ต้องมี migration file commit คู่กันเสมอ

---

## 10. ลำดับการพัฒนาที่แนะนำ (Suggested Build Order)

1. Setup project scaffold (Django + Next.js + docker-compose + PostgreSQL)
2. Auth & User/Role system
3. Models หลัก: Clinic, Doctor, ServiceType, DoctorSchedule, TimeBlock
4. Logic คำนวณ available slots + Appointment booking (ป้องกันคิวชน) — **หัวใจของระบบ ทำให้แน่นก่อน**
5. Queue Dashboard + Walk-in + เปลี่ยนสถานะ
6. Patient database + search + notes
7. Reports
8. Realtime (WebSocket) — ถ้ามีเวลา ไม่งั้นใช้ polling ไปก่อน
9. Notification/reminder (Celery) — เป็น phase ถัดไป ถ้า scope ต้องการ

---

## 11. การตัดสินใจที่ยืนยันแล้ว (Confirmed Decisions)

| หัวข้อ | การตัดสินใจ | ผลกระทบต่อระบบ |
|---|---|---|
| จำนวนสาขา | **หลายสาขา (Multi-branch)** | ทุก model หลักผูกกับ `clinic` FK, permission ต้อง filter ตามสาขาเสมอ, Super Admin เท่านั้นที่มองข้ามสาขาได้ |
| การจองของลูกค้า | **ไม่มีหน้าเว็บสาธารณะ** — เป็นระบบหลังบ้านให้เจ้าหน้าที่จองให้เท่านั้น | ไม่มี role "ลูกค้า", ไม่มีหน้า `booking/` ฝั่ง public, `Appointment.source` มีแค่ `walk_in`/`staff_created` |
| ช่องทางแจ้งเตือน | **SMS เท่านั้น** | ใช้ Celery + SMS Gateway, ไม่ต้องทำ LINE OA/Email ในเฟสนี้ |
| Overbook policy | **ไม่อนุญาตเด็ดขาด** (รวม walk-in) | ทุก endpoint สร้าง/แก้ appointment ต้อง reject ถ้าไม่มี slot ว่างจริง ไม่มีข้อยกเว้น |
