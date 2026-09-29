# 14 — Database Schema — ตารางทั้งหมดและความสัมพันธ์ / Tables & relationships

**TH:** เอกสารนี้อธิบายฐานข้อมูลของระบบจองคิว ได้แก่ มีตารางอะไรบ้าง แต่ละตารางเก็บอะไร สำคัญอย่างไร
และเชื่อมโยงกันแบบไหน รวมถึงเหตุผลของ `on_delete`, index และ constraint แต่ละตัว

**EN:** Every table, what it stores, why it matters, and how it links to the others, including the
reasoning behind each `on_delete` rule, index and constraint.

> ฐานข้อมูลหลัก: **PostgreSQL 16** — datetime ทุกค่าเก็บเป็น **UTC** แล้วแปลงเป็น Asia/Bangkok ตอนแสดงผล
> เรื่อง transaction/ล็อก ดูต่อที่ [13-acid-and-transactions.md](13-acid-and-transactions.md)

---

## 1. ภาพรวม / Overview

ระบบมี **10 ตารางของโดเมน** แบ่งตาม Django app:

| กลุ่ม | ตาราง | บทบาท |
|---|---|---|
| 🏢 องค์กร | `clinics_clinic` | สาขา — **ศูนย์กลางของ multi-branch** แทบทุกตารางชี้มาที่นี่ |
| 👤 ผู้ใช้ | `accounts_user` | บัญชีเจ้าหน้าที่ทุก role (ไม่มีบัญชีลูกค้า) |
| 🩺 แพทย์ | `doctors_doctor` | โปรไฟล์แพทย์ (1:1 กับ user) |
| | `doctors_doctorschedule` | ตารางออกตรวจประจำสัปดาห์ |
| | `doctors_timeblock` | บล็อกเวลาที่ไม่รับคิว (พักเที่ยง, ลา, ประชุม) |
| 💉 บริการ | `services_servicetype` | แคตตาล็อกบริการ + ระยะเวลา (ใช้ร่วมทุกสาขา) |
| 📅 คิว | `scheduling_appointment` | ★ **ตารางหัวใจของระบบ** — การนัดหมาย/คิว |
| 🧑‍🤝‍🧑 คนไข้ | `patients_patient` | ข้อมูลคนไข้ (ใช้ข้ามสาขาได้) |
| | `patients_patientnote` | โน้ตสะสมของคนไข้ |
| 📱 แจ้งเตือน | `notifications_smslog` | log การส่ง SMS ทุกข้อความ |

ฐานข้อมูลจริงมีทั้งหมด **21 ตาราง** — อีก 11 ตารางเป็นโครงสร้างพื้นฐานที่ Django และ SimpleJWT สร้างให้อัตโนมัติ
(ดู [หัวข้อ 8](#8-ตารางของ-framework--framework-tables))

---

## 2. แผนภาพความสัมพันธ์ / ER diagram

```mermaid
erDiagram
    CLINIC ||--o{ USER : "สังกัด (users)"
    CLINIC ||--o{ DOCTOR : "มีแพทย์ (doctors)"
    CLINIC ||--o{ DOCTOR_SCHEDULE : "(doctor_schedules)"
    CLINIC ||--o{ TIME_BLOCK : "(time_blocks)"
    CLINIC ||--o{ APPOINTMENT : "คิวของสาขา (appointments)"
    CLINIC ||--o{ PATIENT : "สาขาที่ลงทะเบียน (registered_patients)"
    CLINIC ||--o{ SMS_LOG : "(sms_logs)"

    USER ||--o| DOCTOR : "1:1 (doctor_profile)"
    USER |o--o{ APPOINTMENT : "created_by"
    USER |o--o{ PATIENT : "created_by"
    USER |o--o{ PATIENT_NOTE : "created_by"

    DOCTOR ||--o{ DOCTOR_SCHEDULE : "ตารางประจำ (schedules)"
    DOCTOR ||--o{ TIME_BLOCK : "บล็อกเวลา (time_blocks)"
    DOCTOR |o--o{ APPOINTMENT : "รับคิว (appointments)"

    SERVICE_TYPE ||--o{ APPOINTMENT : "บริการที่จอง"

    PATIENT ||--o{ APPOINTMENT : "นัดของคนไข้"
    PATIENT ||--o{ PATIENT_NOTE : "โน้ต (notes)"
    PATIENT ||--o{ SMS_LOG : "(sms_logs)"

    APPOINTMENT |o--o{ PATIENT_NOTE : "โน้ตของนัดนี้ (nullable)"
    APPOINTMENT |o--o{ SMS_LOG : "SMS ของนัดนี้ (nullable)"

    CLINIC {
        bigint id PK
        varchar code UK
        varchar name
        time opening_time
        time closing_time
        varchar timezone
        smallint slot_interval_minutes
        smallint non_doctor_service_capacity
        varchar sms_provider
    }
    USER {
        bigint id PK
        varchar email UK
        varchar role
        bigint clinic_id FK "null ได้เฉพาะ super_admin"
    }
    DOCTOR {
        bigint id PK
        bigint user_id FK,UK
        bigint clinic_id FK
        varchar display_name
        varchar color
    }
    DOCTOR_SCHEDULE {
        bigint id PK
        bigint doctor_id FK
        bigint clinic_id FK
        smallint day_of_week
        time start_time
        time end_time
    }
    TIME_BLOCK {
        bigint id PK
        bigint doctor_id FK
        bigint clinic_id FK
        timestamptz start_datetime
        timestamptz end_datetime
        varchar reason
        varchar recurrence
    }
    SERVICE_TYPE {
        bigint id PK
        varchar name UK
        smallint duration_minutes
        decimal price
        bool requires_doctor
    }
    APPOINTMENT {
        bigint id PK
        bigint patient_id FK
        bigint doctor_id FK "null = บริการไม่ใช้แพทย์"
        bigint service_type_id FK
        bigint clinic_id FK
        timestamptz scheduled_start
        timestamptz scheduled_end
        varchar status
        varchar source
        bigint created_by_id FK
    }
    PATIENT {
        bigint id PK
        varchar patient_code UK
        varchar first_name
        varchar last_name
        varchar phone
        bigint home_clinic_id FK
    }
    PATIENT_NOTE {
        bigint id PK
        bigint patient_id FK
        bigint appointment_id FK "nullable"
        text note_text
        bool is_pinned
    }
    SMS_LOG {
        bigint id PK
        bigint clinic_id FK
        bigint patient_id FK
        bigint appointment_id FK "nullable"
        varchar kind
        varchar status
        timestamptz sent_at
    }
```

### อ่านแผนภาพแบบย่อ / The shape in one paragraph

**TH:** `Clinic` อยู่บนสุด ทุกอย่างสังกัดสาขา → `Doctor` มีตารางประจำ (`DoctorSchedule`) และช่วงงดรับ (`TimeBlock`)
→ `Appointment` คือจุดที่ทุกเส้นมาบรรจบ: **ใคร** (`Patient`) มาทำ **อะไร** (`ServiceType`) กับ **ใคร** (`Doctor`)
**ที่ไหน** (`Clinic`) **เมื่อไร** (`scheduled_start/end`) และ **ใครบันทึก** (`created_by`)
→ จากนัดหนึ่งนัดจะแตกออกไปเป็นโน้ต (`PatientNote`) และ SMS แจ้งเตือน (`SMSLog`)

---

## 3. รายละเอียดแต่ละตาราง / Table reference

> คอลัมน์ `created_at` (มี index) และ `updated_at` มีในทุกตารางยกเว้น `accounts_user` (มาจาก `TimeStampedModel`)
> ตารางที่มี `created_by` ด้วยสืบทอดจาก `AuditableModel` — ดู [apps/common/models.py](../backend/apps/common/models.py)

### 3.1 `clinics_clinic` — สาขา 🏢

**ความสำคัญ:** เป็น "หน่วยแบ่งข้อมูล" ของระบบ multi-branch — permission ของ Admin/Staff/Doctor
filter ทุก query ด้วย `clinic` ของผู้ใช้เสมอ

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `id` | bigint PK | |
| `code` | varchar(20) **UNIQUE** | รหัสสาขา เช่น `BKK` — ใช้เป็น prefix ของรหัสคนไข้ (`BKK-000123`) |
| `name`, `address`, `phone` | | |
| `opening_time`, `closing_time` | time | กรอบเวลาทำการ — slot ต้องอยู่ในกรอบนี้ |
| `timezone` | varchar(64) | default `Asia/Bangkok` |
| `slot_interval_minutes` | smallint | ระยะห่างของเวลาเริ่ม slot (default 15 นาที) |
| `non_doctor_service_capacity` | smallint | จำนวนเคสพร้อมกันสูงสุดของบริการที่ไม่ใช้แพทย์ (default 1) |
| `sms_provider`, `sms_sender_name` | varchar | ตั้ง SMS gateway แยกต่อสาขาได้ |
| `is_active` | bool | ปิดสาขาแบบ soft (ไม่ลบข้อมูล) |

**Constraint:** `clinic_closing_time_after_opening_time` — `closing_time > opening_time`

### 3.2 `accounts_user` — บัญชีเจ้าหน้าที่ 👤

**ความสำคัญ:** ใช้ login (JWT) และกำหนดสิทธิ์ผ่าน `role` + `clinic`

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `email` | varchar(254) **UNIQUE** | ใช้เป็น username |
| `password` | varchar(128) | **hash** โดย Django — ไม่เก็บ plain text |
| `role` | varchar(20), index | `super_admin` / `admin` / `staff` / `doctor` |
| `clinic_id` | FK → clinic, **nullable** | null ได้เฉพาะ `super_admin` (มองข้ามสาขา) |
| `full_name`, `phone` | | |
| `is_active`, `is_staff`, `is_superuser`, `last_login`, `date_joined` | | ฟิลด์มาตรฐานของ Django auth |

**Constraint:** `user_non_super_admin_requires_clinic` — `role = 'super_admin' OR clinic_id IS NOT NULL`
→ ฐานข้อมูลรับประกันว่าไม่มีพนักงาน "ลอย" ที่ไม่สังกัดสาขา (ถ้ามีจะหลุด branch scoping)

### 3.3 `doctors_doctor` — โปรไฟล์แพทย์ 🩺

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `user_id` | FK → user, **UNIQUE (1:1)** | แพทย์หนึ่งคน = บัญชีเดียว |
| `clinic_id` | FK → clinic | ต้องตรงกับ `user.clinic` (ตรวจใน `clean()`) |
| `display_name` | varchar(150) | ชื่อที่แสดง เช่น "พญ. สมหญิง" |
| `specialties` | varchar(255) | |
| `color` | varchar(7) | สี hex สำหรับปฏิทิน |
| `is_active` | bool | |

**Index:** `(clinic_id, is_active)` — หน้าจอดึง "แพทย์ที่ยัง active ของสาขานี้" บ่อยที่สุด

### 3.4 `doctors_doctorschedule` — ตารางออกตรวจประจำสัปดาห์

**ความสำคัญ:** เป็น **แหล่งที่มาของเวลาว่าง** — slot จองได้ต้องอยู่ในช่วงเหล่านี้เท่านั้น

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `doctor_id` | FK → doctor | |
| `clinic_id` | FK → clinic | คัดลอกจาก `doctor.clinic` อัตโนมัติตอน save (denormalized) |
| `day_of_week` | smallint 0–6 | 0 = จันทร์ |
| `start_time`, `end_time` | time | หนึ่งแถว = หนึ่งช่วง (วันเดียวมีหลายช่วงได้ เช่น เช้า/บ่าย) |
| `is_active` | bool | |

**Constraints:** `doctor_schedule_end_after_start`, `doctor_schedule_unique_start_per_day` (`doctor, day_of_week, start_time` ห้ามซ้ำ)
**Index:** `(doctor_id, day_of_week, is_active)` — ใช้ตอนคำนวณ slot ของ "แพทย์คนนี้ วันนี้"

### 3.5 `doctors_timeblock` — บล็อกเวลาพิเศษ

**ความสำคัญ:** **หักออก** จากเวลาว่างในตาราง (พักเที่ยง, ลา, เคสด่วน)

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `doctor_id`, `clinic_id` | FK | `clinic` คัดลอกจากแพทย์เหมือนตารางประจำ |
| `start_datetime`, `end_datetime` | timestamptz | `start_datetime` มี index |
| `reason` | varchar | `lunch` / `meeting` / `urgent_case` / `leave` / `other` |
| `note` | varchar(255) | |
| `is_recurring`, `recurrence`, `recurrence_end_date` | | รองรับ `daily` / `weekly` (เช่น พักเที่ยงทุกวัน) |

**Constraint:** `time_block_end_after_start` · **Index:** `(doctor_id, start_datetime)`

### 3.6 `services_servicetype` — ประเภทบริการ 💉

**ความสำคัญ:** `duration_minutes` เป็นตัวกำหนดความยาวคิว — `scheduled_end` คำนวณจากค่านี้เสมอ
เป็น **แคตตาล็อกกลาง** (ไม่มี `clinic_id`) เพื่อให้รายงานข้ามสาขาเทียบบริการเดียวกันได้

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `name` | varchar(150) **UNIQUE** | |
| `category` | varchar(80), index | |
| `description` | text | |
| `duration_minutes` | smallint | |
| `price` | decimal | |
| `requires_doctor` | bool | `false` → คิวไม่มีแพทย์ ใช้เพดาน `clinic.non_doctor_service_capacity` แทน |
| `is_active` | bool | |

### 3.7 `scheduling_appointment` — การนัดหมาย/คิว ★📅

**ความสำคัญ:** ตารางหัวใจ ทุกฟีเจอร์ (หน้าคิว, ปฏิทิน, ประวัติคนไข้, รายงาน, SMS) อ่านจากที่นี่

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `patient_id` | FK → patient | |
| `doctor_id` | FK → doctor, **nullable** | null = บริการที่ไม่ใช้แพทย์ |
| `service_type_id` | FK → service_type | |
| `clinic_id` | FK → clinic | สาขาที่มารับบริการ (อาจต่างจาก `patient.home_clinic`) |
| `scheduled_start`, `scheduled_end` | timestamptz | `end = start + service.duration_minutes` |
| `status` | varchar, index | `booked` → `confirmed` → `checked_in` → `in_progress` → `completed` / `cancelled` / `no_show` |
| `source` | varchar | `staff_created` / `walk_in` (ไม่มี `online`) |
| `note` | varchar(255) | โน้ตสั้นของนัดนี้ |
| `checked_in_at`, `started_at`, `completed_at` | timestamptz null | เวลาจริงของแต่ละขั้น — ใช้คำนวณเวลารอในรายงาน |
| `cancelled_reason` | varchar(255) | |
| `created_by_id` | FK → user, nullable | audit trail |

**Constraints:**
- `appointment_end_after_start` — `scheduled_end > scheduled_start`
- **`appointment_no_overlap_per_doctor`** (exclusion, PostgreSQL) — แพทย์คนเดียวกันห้ามมีคิวที่ยังกินเวลาซ้อนกัน
  (นับเฉพาะ `booked/confirmed/checked_in/in_progress/completed`) — รายละเอียดใน [13-acid](13-acid-and-transactions.md)

**Indexes:**
| Index | ใช้กับ query |
|---|---|
| `scheduled_start` | ช่วงเวลาทั่วไป |
| `(clinic_id, scheduled_start)` | หน้าคิววันนี้ของสาขา, ปฏิทิน, รายงาน |
| `(doctor_id, scheduled_start)` | คำนวณ slot ว่างของแพทย์, ตารางของแพทย์ |
| `(status, scheduled_start)` | งาน SMS หา "นัดที่ยัง booked/confirmed ในช่วงเวลานี้" |
| GiST `(doctor_id, tstzrange)` | สร้างอัตโนมัติโดย exclusion constraint |

### 3.8 `patients_patient` — คนไข้ 🧑‍🤝‍🧑

**ความสำคัญ:** ใช้ร่วมข้ามสาขา — คนไข้คนเดียวไปหลายสาขาได้โดยไม่สร้าง record ซ้ำ (จับคู่ด้วยเบอร์โทร)

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `patient_code` | varchar(20) **UNIQUE** | สร้างอัตโนมัติ `<รหัสสาขา>-<ลำดับ 6 หลัก>` |
| `first_name`, `last_name` | varchar(100) | |
| `phone` | varchar(10), index | ตัวค้นหาหลัก |
| `date_of_birth` | date null | |
| `gender` | varchar | `female` / `male` / `other` / `unspecified` |
| `home_clinic_id` | FK → clinic | สาขาที่ลงทะเบียนครั้งแรก — **ไม่ได้** จำกัดว่าจองได้ที่สาขาเดียว |
| `is_active` | bool | |
| `created_by_id` | FK → user, nullable | |

**Constraint:** `patient_unique_phone_and_name` — `(phone, first_name, last_name)` ห้ามซ้ำ
(เบอร์เดียวกันมีหลายคนได้ เช่น แม่กับลูก แต่ชื่อ-สกุลเดียวกันซ้ำไม่ได้)

**Indexes:** `phone`, `(last_name, first_name)`, และ **GIN trigram** บน `first_name`, `last_name`
(migration `0003_patient_search_indexes`, ใช้ `pg_trgm`) — ให้ค้นชื่อแบบพิมพ์บางส่วนได้เร็ว

### 3.9 `patients_patientnote` — โน้ตคนไข้

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `patient_id` | FK → patient | |
| `appointment_id` | FK → appointment, **nullable** | ผูกกับนัดใดนัดหนึ่งได้ หรือเป็นโน้ตทั่วไปของคนไข้ |
| `note_text` | text | เช่น "แพ้ยาชา", "ขอหมอคนเดิม" |
| `is_pinned` | bool | โน้ตสำคัญแสดงบนสุด |
| `created_by_id` | FK → user, nullable | |

**Index:** `(patient_id, -created_at)` — ดึงโน้ตล่าสุดของคนไข้

### 3.10 `notifications_smslog` — log การส่ง SMS 📱

**ความสำคัญ:** ตรวจย้อนหลังได้ว่าส่งอะไร ถึงใคร สำเร็จหรือไม่ และกันส่งซ้ำ

| คอลัมน์ | ชนิด | หมายเหตุ |
|---|---|---|
| `clinic_id`, `patient_id` | FK | |
| `appointment_id` | FK, nullable | null ได้สำหรับ SMS แบบ `manual` |
| `kind` | varchar | `appointment_reminder` / `manual` |
| `message` | text | ข้อความที่ส่งจริง |
| `status` | varchar, index | `pending` → `sent` / `failed` |
| `provider`, `provider_message_id`, `error_message` | | ข้อมูลจาก gateway |
| `sent_at` | timestamptz null | |

**Constraint:** `sms_unique_reminder_per_appointment` — `(appointment_id, kind)` ห้ามซ้ำ **ยกเว้นแถวที่ `failed`**
(partial unique) → ส่ง reminder ได้ครั้งเดียวต่อนัด แต่ถ้าล้มเหลวยังส่งใหม่ได้
**Index:** `(clinic_id, -created_at)`

---

## 4. ความสัมพันธ์และกฎการลบ / Relationships & `on_delete`

| จาก → ไป | ชนิด | `on_delete` | เหตุผล |
|---|---|---|---|
| user → clinic | N:1 | **PROTECT** | ลบสาขาที่ยังมีพนักงานไม่ได้ |
| doctor → user | **1:1** | **PROTECT** | ต้องจัดการโปรไฟล์แพทย์ก่อนลบบัญชี |
| doctor → clinic | N:1 | PROTECT | |
| doctor_schedule → doctor | N:1 | **CASCADE** | ตารางประจำไม่มีความหมายถ้าไม่มีแพทย์ |
| time_block → doctor | N:1 | **CASCADE** | เหมือนกัน |
| doctor_schedule / time_block → clinic | N:1 | PROTECT | |
| appointment → patient | N:1 | **PROTECT** | ห้ามลบคนไข้ที่มีประวัตินัด (ข้อมูลรักษา/รายงาน) |
| appointment → doctor | N:1 | **PROTECT** | ห้ามลบแพทย์ที่มีคิว — ใช้ `is_active=false` แทน |
| appointment → service_type | N:1 | **PROTECT** | ห้ามลบบริการที่ถูกใช้แล้ว — รายงานย้อนหลังต้องอยู่ครบ |
| appointment → clinic | N:1 | PROTECT | |
| patient → home_clinic | N:1 | PROTECT | |
| patient_note → patient | N:1 | **CASCADE** | โน้ตเป็นของคนไข้ |
| patient_note → appointment | N:1 | **SET_NULL** | ถ้านัดหายไป โน้ตยังเก็บไว้กับคนไข้ |
| sms_log → patient / clinic | N:1 | PROTECT | log ต้องตรวจย้อนหลังได้ |
| sms_log → appointment | N:1 | **SET_NULL** | log อยู่ต่อแม้นัดถูกลบ |
| `created_by` ทุกตาราง → user | N:1 | **SET_NULL** | ลบบัญชีพนักงานได้โดยไม่ทำให้ข้อมูลที่เขาบันทึกหายไป |

**หลักที่ใช้ / Design rule:**
- **PROTECT** เป็นค่าหลัก — ข้อมูลทางการแพทย์และรายงานต้องไม่หายเพราะลบแม่ตาราง
  ในทางปฏิบัติระบบ "ลบ" ด้วยการตั้ง `is_active = false` (soft delete) แทน
- **CASCADE** ใช้เฉพาะข้อมูลที่เป็น "ส่วนหนึ่ง" ของแม่จริง ๆ (ตารางแพทย์, โน้ต)
- **SET_NULL** ใช้กับการอ้างอิงเสริม (audit, ลิงก์ไปนัด) ที่ข้อมูลลูกควรอยู่ต่อได้

---

## 5. ทำไม `clinic_id` ซ้ำหลายที่? / Why is `clinic_id` everywhere?

**TH:** `doctor_schedule` และ `time_block` หา clinic ผ่าน `doctor.clinic` ได้อยู่แล้ว แต่ยังเก็บ `clinic_id` ซ้ำ
(denormalization) โดยตั้งใจ เพราะ:

1. **Branch scoping ทำได้แบบเดียวกันทุกตาราง** — `BranchScopedQuerySetMixin` filter `clinic = user.clinic`
   ได้ตรง ๆ ไม่ต้อง join ต่อแต่ละ model
2. **ป้องกันข้อมูลรั่วข้ามสาขา** — ถ้าต้องจำว่าตารางไหนต้อง join ผ่านอะไร มีโอกาสลืมและเปิดข้อมูลข้ามสาขา
3. **Index ได้ตรง** — query ต่อสาขาใช้ index ได้โดยไม่ join

ความถูกต้องรักษาไว้ด้วย `save()` ที่ตั้ง `clinic = doctor.clinic` เสมอ และ `Doctor.clean()` ที่ตรวจว่า
`doctor.clinic == user.clinic`

**ข้อยกเว้นที่ตั้งใจ:** `services_servicetype` **ไม่มี** `clinic_id` (แคตตาล็อกกลาง) และ `patients_patient`
ใช้ `home_clinic_id` ซึ่งเป็นแค่ "สาขาที่ลงทะเบียน" ไม่ใช่ขอบเขตการมองเห็น — ค้นหา/จองข้ามสาขาได้

---

## 6. ข้อมูลไหลผ่านตารางอย่างไร / How data flows

### จองคิว 1 ครั้ง

```
1. ค้นคนไข้         patients_patient          (phone index / trigram)
                    └─ ไม่เจอ → INSERT patient (สร้าง patient_code)
2. หาเวลาว่าง       doctors_doctorschedule    (ช่วงที่ออกตรวจ)
                    − doctors_timeblock       (หักบล็อกเวลา)
                    − scheduling_appointment  (หักคิวที่จองแล้ว)
                    + services_servicetype    (ความยาว slot)
3. บันทึก           LOCK doctors_doctor → INSERT scheduling_appointment
4. แจ้งเตือน         (วันก่อนนัด) Celery → INSERT notifications_smslog → ส่ง → UPDATE status
```

### Query หลักของแต่ละหน้าจอ

| หน้าจอ / งาน | ตารางหลัก | Index ที่ใช้ |
|---|---|---|
| หน้าคิววันนี้ | appointment ⨝ patient, doctor, service_type | `(clinic_id, scheduled_start)` |
| คำนวณ slot ว่าง | doctor_schedule, time_block, appointment | `(doctor, day_of_week, is_active)`, `(doctor, start_datetime)`, `(doctor, scheduled_start)` |
| ค้นหาคนไข้ | patient | `phone`, trigram GIN |
| ประวัติคนไข้ | appointment, patient_note | FK `patient_id`, `(patient, -created_at)` |
| รายงาน / no-show rate | appointment (aggregate `Count` + `Case/When`) | `(clinic_id, scheduled_start)`, `(status, scheduled_start)` |
| งานส่ง SMS | appointment, sms_log | `(status, scheduled_start)` |

---

## 7. สรุป Constraint ทั้งหมด / All constraints

| ตาราง | Constraint | ชนิด | กฎ |
|---|---|---|---|
| clinic | `clinic_closing_time_after_opening_time` | CHECK | ปิด > เปิด |
| clinic | `code` | UNIQUE | |
| user | `user_non_super_admin_requires_clinic` | CHECK | ไม่ใช่ super admin ต้องมีสาขา |
| user | `email` | UNIQUE | |
| doctor | `user_id` | UNIQUE | 1:1 |
| doctor_schedule | `doctor_schedule_end_after_start` | CHECK | จบ > เริ่ม |
| doctor_schedule | `doctor_schedule_unique_start_per_day` | UNIQUE | (doctor, day, start) |
| time_block | `time_block_end_after_start` | CHECK | จบ > เริ่ม |
| service_type | `name` | UNIQUE | |
| appointment | `appointment_end_after_start` | CHECK | จบ > เริ่ม |
| appointment | **`appointment_no_overlap_per_doctor`** | **EXCLUDE (GiST)** | แพทย์เดียวกันห้ามมีคิวซ้อนเวลา |
| patient | `patient_code` | UNIQUE | |
| patient | `patient_unique_phone_and_name` | UNIQUE | (phone, first, last) |
| sms_log | `sms_unique_reminder_per_appointment` | UNIQUE (partial) | reminder 1 ครั้ง/นัด ยกเว้นที่ failed |

**PostgreSQL extensions ที่ใช้:** `btree_gist` (exclusion constraint), `pg_trgm` (ค้นชื่อคนไข้)
— ทั้งสองถูกข้ามบน SQLite ผ่าน `PostgresOnlySQL`

---

## 8. ตารางของ framework / Framework tables

**TH:** นอกจาก 10 ตารางของคลินิก ฐานข้อมูลยังมีอีก **11 ตาราง** ที่เราไม่ได้ออกแบบเอง
แต่ Django และ library สร้างให้อัตโนมัติ

**EN:** Besides the 10 domain tables there are 11 infrastructure tables created automatically by
Django and SimpleJWT.

### 8.1 ทำไม Django ถึงสร้างให้ / Why they exist

ใน Django ระบบถูกแบ่งเป็น **app** ย่อย ๆ ทุก app (ทั้งที่เราเขียนเองและที่มากับ Django) มี `models.py`
และ `migrations/` ของตัวเอง ตอนรัน `python manage.py migrate` Django จะไล่ **ทุก app ใน `INSTALLED_APPS`**
แล้วสร้างตารางให้ครบ โดยไม่แยกว่าเป็น app ของใคร

ตารางแต่ละตัวจึงมาจาก app ที่เราเปิดใช้ใน [settings.py](../backend/config/settings.py):

```python
INSTALLED_APPS = [
    "django.contrib.admin",          # → django_admin_log
    "django.contrib.auth",           # → auth_permission, auth_group, auth_group_permissions
    "django.contrib.contenttypes",   # → django_content_type
    "django.contrib.sessions",       # → django_session
    ...
    "rest_framework_simplejwt.token_blacklist",  # → token_blacklist_* (2 ตาราง)
    ...
    "apps.accounts",                 # → accounts_user (+ user_groups, user_user_permissions)
    "apps.clinics",                  # → clinics_clinic
    ...                              # ← 10 ตารางที่ออกแบบเอง
]
```

ส่วน `django_migrations` เป็นกรณีพิเศษ — คำสั่ง `migrate` สร้างเองเพื่อจดว่ารัน migration ไหนไปแล้ว
ทุกโปรเจกต์ Django จึงมีตารางนี้เสมอ

**ทำไมใช้ app สำเร็จรูปแทนเขียนเอง** — เป็นงานที่ทุกเว็บต้องมี และเขียนเองให้ปลอดภัยได้ยาก
Django เตรียมไว้ให้แบบผ่านการทดสอบแล้ว (แนวคิด "batteries included"):

| App | ให้อะไร | ถ้าไม่ใช้ ต้องเขียนเอง |
|---|---|---|
| `auth` | ระบบผู้ใช้, **hash รหัสผ่าน**, ตรวจรหัสผ่าน | การเข้ารหัสรหัสผ่าน — พลาดง่ายและอันตราย |
| `admin` | หน้า `/admin/` ดู/แก้ข้อมูลทุกตารางได้ทันที | หน้าจัดการข้อมูลหลังบ้านทั้งหมด |
| `contenttypes` | ทะเบียน model ที่ `auth` และ `admin` ต้องใช้ | (เป็นฐานของสองตัวบน) |
| `sessions` | จำสถานะ login ของหน้า admin | ระบบ session |
| `token_blacklist` | ยกเลิก JWT ได้จริงตอน logout | ระบบเพิกถอน token |

**ทำไม `accounts_user` พ่วงมาอีก 2 ตาราง** — model `User` สืบทอดคลาสสำเร็จรูปของ Django
([apps/accounts/models.py](../backend/apps/accounts/models.py)):

```python
class User(AbstractBaseUser, PermissionsMixin):
```

`PermissionsMixin` มีฟิลด์ `groups` และ `user_permissions` แบบ many-to-many ซึ่งฐานข้อมูลต้องใช้ตารางกลาง
Django จึงสร้าง `accounts_user_groups` และ `accounts_user_user_permissions` ให้ — เราสืบทอด mixin นี้
เพราะหน้า `/admin/` ใช้มันเช็คสิทธิ์การเข้าใช้

### 8.2 แต่ละตารางทำอะไร / What each table does

> จำนวนแถวเป็นตัวอย่างจากฐานข้อมูล dev ณ 2026-09-30

#### 🔐 ระบบสิทธิ์ของ Django — 5 ตาราง (แทบไม่ได้ใช้)

| ตาราง | แถว | หน้าที่ |
|---|---|---|
| `auth_permission` | 68 | รายการสิทธิ์อัตโนมัติ 4 สิทธิ์ต่อ model (add/change/delete/view) |
| `auth_group` | 0 | กลุ่มผู้ใช้ เช่น "ทีมพยาบาล" |
| `auth_group_permissions` | 0 | กลุ่มไหนมีสิทธิ์อะไร |
| `accounts_user_groups` | 0 | ผู้ใช้คนไหนอยู่กลุ่มไหน |
| `accounts_user_user_permissions` | 0 | สิทธิ์พิเศษรายคน |

**ทำไมเกือบทั้งหมดว่าง:** ระบบนี้ **ไม่ได้ใช้** ระบบสิทธิ์ของ Django แต่ใช้คอลัมน์ `role` ใน `accounts_user`
(super_admin / admin / staff / doctor) แล้วเช็คสิทธิ์ในโค้ดเอง ([apps/common/permissions.py](../backend/apps/common/permissions.py))
ซึ่งเรียบง่ายและตรงกับ 4 role ใน spec มากกว่า ตารางยังต้องมีอยู่เพราะ `PermissionsMixin` และหน้า admin อ้างถึง

#### 🔑 ระบบ Login (SimpleJWT) — 2 ตาราง (ใช้งานจริง)

| ตาราง | หน้าที่ |
|---|---|
| `token_blacklist_outstandingtoken` | สมุดบันทึก refresh token ทุกใบที่ระบบออกให้ตอน login |
| `token_blacklist_blacklistedtoken` | token ที่ถูกยกเลิกแล้ว |

ถ้าไม่มี 2 ตารางนี้ การ logout จะแค่ลบ cookie แต่ token เดิมยังใช้ได้จนหมดอายุ (7 วัน) —
เมื่อมีตารางนี้ logout จะเพิกถอน token ได้จริงทันที และทุกครั้งที่ต่ออายุ token ใบเก่าจะถูกยกเลิกด้วย
(`BLACKLIST_AFTER_ROTATION`) ใครขโมย token เก่าไปก็ใช้ไม่ได้

> ข้อมูลในสองตารางนี้เป็นสถานะการ login ของแต่ละเครื่อง — ไม่ถูกรวมใน [DB/clinic.sql](../DB/clinic.sql)

#### ⚙️ ตารางระบบของ Django — 4 ตาราง

| ตาราง | หน้าที่ | ความสำคัญ |
|---|---|---|
| `django_migrations` | บันทึกว่า migration ไหนรันแล้ว | **สำคัญมาก** — ถ้าหาย `migrate` จะพยายามสร้างตารางซ้ำแล้ว error |
| `django_content_type` | ทะเบียนว่าระบบมี model อะไรบ้าง | ใช้ภายใน เชื่อม `auth_permission` กับ model |
| `django_admin_log` | ประวัติการแก้ข้อมูลผ่านหน้า `/admin/` | มีข้อมูลเมื่อมีคนใช้หน้า admin |
| `django_session` | session ของหน้า `/admin/` | ใช้เฉพาะหน้า admin — หน้าเว็บหลักใช้ JWT |

### 8.3 ตัดทิ้งได้ไหม / Can they be removed?

- ตัด `admin` + `sessions` ออกจาก `INSTALLED_APPS` ได้ (หาย 2 ตาราง) แต่จะเสียหน้า `/admin/` ที่ใช้ตรวจ/แก้ข้อมูลตอนพัฒนา
- ตัด `auth` + `contenttypes` **ไม่ได้** — การ hash รหัสผ่านและ JWT พึ่งสองตัวนี้
- ตารางว่างแทบไม่กินพื้นที่และไม่ทำให้ระบบช้าลง — **ไม่คุ้มที่จะตัด**
- **ห้ามลบตารางเหล่านี้ด้วยมือ** แม้จะว่าง เพราะ Django อ้างถึงอยู่ — หน้า admin หรือ `migrate` จะพัง

### 8.4 สรุปสำหรับวิทยานิพนธ์ / One-line summary

> ระบบมี 10 ตารางหลักตามการออกแบบ ส่วนอีก 11 ตารางเป็นตารางพื้นฐานของ Django framework และ SimpleJWT
> ที่ใช้สำหรับระบบยืนยันตัวตน การจัดการสิทธิ์ และการบันทึก migration

---

## 9. แก้ schema อย่างไร / Changing the schema

1. แก้ `models.py` ของ app ที่เกี่ยวข้อง
2. `python manage.py makemigrations` → **commit ไฟล์ migration คู่กับโค้ดเสมอ**
3. ถ้าเพิ่มสถานะใหม่ใน `OCCUPYING_STATUSES` → ต้องสร้าง migration แก้ SQL ของ exclusion constraint ด้วย
4. ถ้าเพิ่มตารางที่เป็นข้อมูลของสาขา → ใส่ `clinic` FK (PROTECT) และใช้ `BranchScopedQuerySetMixin` ใน view
5. อัปเดตเอกสารนี้
