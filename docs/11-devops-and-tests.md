# 11 — Docker, migrations, seed, และชุดเทสต์ / DevOps & tests

---

## 1. ชุดเทสต์ทั้งหมด / The full test suite

**TH:** 78 เทสต์ ครอบคลุมสิ่งที่ **พังแล้วเจ็บที่สุด** ก่อนเป็นอันดับแรก (การคำนวณ slot และการกันคิวชน)

**EN:** 78 tests, prioritising what hurts most when broken: slot math and collision prevention.

| ไฟล์ / File | จำนวน | ครอบคลุม (TH) | Covers (EN) |
|---|---|---|---|
| `apps/common/tests/test_time_intervals.py` | 18 | คณิตช่วงเวลาล้วน ๆ (`SimpleTestCase` — ไม่แตะ DB) | Pure interval math, no DB |
| `apps/scheduling/tests/test_slot_availability.py` | 18 | การคำนวณ slot ทั้งสองโหมด | Both availability modes |
| `apps/scheduling/tests/test_booking_service.py` | 20 | จอง/walk-in/เลื่อน/สถานะ | Booking, walk-in, reschedule, status |
| `apps/queue/tests/test_queue_api.py` | 10 | API หน้างาน + สิทธิ์ของแพทย์ 🔒 | Front-desk API + doctor isolation 🔒 |
| `apps/accounts/tests/test_auth_and_scoping.py` | 12 | auth + branch scoping 🔒 | Auth + branch scoping 🔒 |

### คำสั่งรัน / Commands

```bash
cd backend && DATABASE_URL= python manage.py test
```

```bash
cd backend && DATABASE_URL= python manage.py test apps.scheduling
```

```bash
cd frontend && npm run typecheck
```

**🔑 ทำไมต้อง `DATABASE_URL=` (ค่าว่าง):** บังคับให้ใช้ sqlite ชั่วคราว จะได้รันเทสต์บนเครื่องที่ยังไม่มี
PostgreSQL ได้ ถ้าฐานจริงรันอยู่แล้วตัดตัวแปรนี้ออกได้เลย
**🔑 Why `DATABASE_URL=`:** it forces the sqlite fallback so tests run without PostgreSQL. Drop it
when the real database is available.

**⚠️ ข้อจำกัดบน sqlite:** exclusion constraint (ตาข่ายชั้นที่ 3) และ trigram index **ไม่ถูกสร้าง**
การกันคิวชนระดับแอปพลิเคชันยังทำงานครบทุกกรณี แต่ **ก่อนขึ้น production ต้องรันเทสต์บน PostgreSQL ด้วย**
**⚠️ sqlite limitation:** the exclusion constraint and trigram indexes are skipped. The application-level
guard is still complete, but **run the suite on PostgreSQL before shipping**.

### แนวทางเขียนเทสต์เพิ่ม / How to add tests

**TH:** ใช้ `ClinicTestDataMixin` จาก `apps/scheduling/tests/factories.py` — มี `create_clinic()`,
`create_doctor()` (พร้อมตาราง), `create_service()`, `create_patient()`, `create_time_block()`
และใช้ `next_monday()` เสมอเพื่อให้เทสต์อยู่ในอนาคต (ไม่ชนกับกฎ "ห้ามจองย้อนหลัง")

**EN:** Reuse `ClinicTestDataMixin` and always anchor on `next_monday()` so tests sit in the future and
don't trip the no-past-booking rule.

---

## 2. Migrations

| แอป / App | ไฟล์ | หมายเหตุ (TH) | Note (EN) |
|---|---|---|---|
| accounts | `0001_initial` | ตาราง User + CheckConstraint | User table + check constraint |
| clinics | `0001_initial` | ตาราง Clinic | Clinic table |
| doctors | `0001_initial` | Doctor / DoctorSchedule / TimeBlock | Three tables |
| services | `0001_initial` | ServiceType | Service catalog |
| scheduling | `0001_initial` | Appointment + index | Appointment + indexes |
| scheduling | ★ `0002_appointment_overlap_exclusion` | exclusion constraint (**PostgreSQL เท่านั้น**) | Exclusion constraint (**PostgreSQL only**) |
| patients | `0001` / `0002` / `0003` | ตาราง / FK ข้ามแอป / trigram index (PostgreSQL) | Table / cross-app FKs / trigram (PG) |
| notifications | `0001` / `0002` | ตาราง+constraint / FK ข้ามแอป | Table+constraint / cross-app FKs |

**🔑 กฎ:** แก้ model ต้องมี migration commit คู่กันเสมอ
```bash
cd backend && python manage.py makemigrations
```

**🔑 migration ที่ต้องใช้ PostgreSQL ให้ห่อด้วย `PostgresOnlySQL`** (`apps/common/db_operations.py`)
ไม่งั้น `manage.py test` บน sqlite จะพัง
**🔑** Wrap PostgreSQL-only SQL in `PostgresOnlySQL`, otherwise the sqlite test run breaks.

---

## 3. ข้อมูลตัวอย่างสำหรับ dev / Dev seed data

```bash
cd backend && python manage.py seed_dev_data
```

```bash
cd backend && python manage.py seed_dev_data --reset
```

**สร้างอะไรบ้าง / What it creates:**
2 สาขา (BKK 09:00–19:00, CNX 10:00–18:00) · 5 บริการ (มีหนึ่งตัวไม่ต้องใช้แพทย์) ·
super admin + ผู้จัดการ/เจ้าหน้าที่ต่อสาขา · แพทย์ 3 คนพร้อมตารางเช้า-บ่ายและพักเที่ยงซ้ำทุกวัน ·
คนไข้ 4 คน · คิวตัวอย่างของวันพรุ่งนี้

**บัญชีทดสอบ / Test accounts** — รหัสผ่านเดียวกันทุกบัญชี: `ClinicDev!2026`

| บทบาท / Role | อีเมล / Email |
|---|---|
| Super Admin | `root@clinic.test` |
| ผู้จัดการสาขา / Branch manager | `admin.bkk@clinic.test`, `admin.cnx@clinic.test` |
| เจ้าหน้าที่ / Staff | `staff.bkk@clinic.test`, `staff.cnx@clinic.test` |
| แพทย์ / Doctor | `doctor.ploy@clinic.test`, `doctor.non@clinic.test`, `doctor.mint@clinic.test` |

**🔑 คำสั่งนี้ปฏิเสธการรันเมื่อ `DEBUG=False`** (ต้องใส่ `--force`) ตามข้อกำหนดข้อ 7
**🔑** It refuses to run with `DEBUG=False` unless `--force` — per spec §7.

---

## 4. รันด้วย Docker / Running with Docker

```bash
cp backend/.env.example backend/.env
```

```bash
docker compose up --build
```

| Service | พอร์ต / Port | คืออะไร / What |
|---|---|---|
| frontend | 3000 | Next.js dev server |
| backend | 8000 | Daphne (ASGI — รองรับ WebSocket) |
| db | 5432 | PostgreSQL 16 |
| redis | 6379 | Channels layer + Celery broker |
| celery_worker | — | ส่ง SMS จริง / sends SMS |
| celery_beat | — | ตั้งเวลาแจ้งเตือนรายชั่วโมง / hourly scheduler |

**URL ที่ใช้บ่อย / Handy URLs:**
- หน้าเว็บ / App: http://localhost:3000
- Swagger UI: http://localhost:8000/api/docs/
- OpenAPI schema: http://localhost:8000/api/schema/
- Django admin: http://localhost:8000/admin/

```bash
docker compose exec backend python manage.py seed_dev_data
```

---

## 5. รันแบบไม่ใช้ Docker / Running without Docker

### Backend
```bash
cd backend && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt
```
```bash
cd backend && python manage.py migrate && python manage.py seed_dev_data && python manage.py runserver 8000
```

### Frontend
```bash
cd frontend && npm install && npm run dev
```

### ใช้ PostgreSQL ของ Docker จาก manage.py บนเครื่อง / Use the dockerised Postgres locally
```bash
docker compose up -d db redis
```
```bash
cd backend && DATABASE_URL=postgres://clinic:clinic@127.0.0.1:5432/clinic REDIS_URL=redis://127.0.0.1:6379/0 python manage.py migrate
```

**🔑 ทำไมต้อง override เป็น `127.0.0.1`:** ค่าใน `.env` ใช้ชื่อ service (`db`, `redis`)
ซึ่งใช้ได้เฉพาะภายใน docker network
**🔑** The `.env` values use docker service names, which only resolve inside the docker network.

### Celery (ต้องมี Redis / requires Redis)
```bash
cd backend && celery -A config worker -l info
```
```bash
cd backend && celery -A config beat -l info
```

---

## 6. เช็คลิสต์ก่อนขึ้น production / Production checklist 🔒

| ✔ | รายการ (TH) | Item (EN) |
|---|---|---|
| ☐ | ตั้ง `DJANGO_SECRET_KEY` เป็นค่าสุ่มยาว | Set a long random `DJANGO_SECRET_KEY` |
| ☐ | `DJANGO_DEBUG=false` | Same |
| ☐ | ใช้ **PostgreSQL** (ไม่ใช่ sqlite) — ตาข่ายชั้นฐานข้อมูลจะทำงาน | Use **PostgreSQL** so the DB-level net is active |
| ☐ | ตั้ง `REDIS_URL` (ไม่งั้น realtime + Celery ทำงานไม่ครบ) | Set `REDIS_URL` |
| ☐ | เปลี่ยน `SMS_PROVIDER` จาก `console` เป็นเจ้าจริง + ใส่ credential | Switch off the console SMS provider |
| ☐ | ตั้ง `DJANGO_ALLOWED_HOSTS` และ `FRONTEND_ORIGIN` ให้ตรงโดเมนจริง | Set hosts and CORS origin |
| ☐ | รันเทสต์บน PostgreSQL | Run the suite on PostgreSQL |
| ☐ | ยืนยันว่า `.env` **ไม่ได้** ถูก commit | Confirm `.env` is not committed |
| ☐ | ห้ามรัน `seed_dev_data` บนฐานจริง | Never seed the production database |
| ☐ | `frontend` ใช้ `npm run build && npm start` (ไม่ใช่ `npm run dev`) | Build the frontend for production |

---

## 7. ปัญหาที่เจอบ่อย / Common problems

| อาการ / Symptom | สาเหตุ (TH) | Cause & fix (EN) |
|---|---|---|
| จองไม่ได้ ขึ้น `slot_unavailable` ทั้งที่ตารางดูว่าง | แพทย์ไม่มี `DoctorSchedule` ของวันนั้น หรือเวลาอยู่นอกเวลาทำการสาขา หรือเป็นเวลาที่ผ่านไปแล้ว | No schedule for that weekday, outside clinic hours, or in the past |
| WebSocket ไม่ทำงาน (ป้ายขึ้น "อัปเดตทุก 10 วิ") | ไม่ได้ตั้ง `NEXT_PUBLIC_WS_URL` หรือไม่มี Redis — **ระบบยังใช้งานได้ปกติด้วย polling** | `NEXT_PUBLIC_WS_URL` unset or no Redis — **the app still works via polling** |
| `seed_dev_data` พังบน Windows เรื่องภาษาไทย | คอนโซล cp1252 — คำสั่งจัดการให้แล้วผ่าน `_ensure_utf8_console()` | Handled by `_ensure_utf8_console()` |
| เทสต์พังเพราะ `btree_gist` | รันบน sqlite แต่ migration ไม่ได้ห่อด้วย `PostgresOnlySQL` | Wrap the SQL in `PostgresOnlySQL` |
| login แล้วเด้งกลับหน้า login | cookie ไม่ถูกตั้ง — เช็ค `BACKEND_INTERNAL_URL` ว่า Next เรียก Django ได้จริง | Cookies not set — verify `BACKEND_INTERNAL_URL` |
| `403 branch_access_denied` | Super Admin ลืมส่ง `?clinic_id=` หรือผู้ใช้พยายามแตะข้อมูลข้ามสาขา | Missing `?clinic_id=` for Super Admin, or a genuine cross-branch attempt |
