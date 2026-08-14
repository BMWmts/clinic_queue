# ระบบจองคิวคลินิกออนไลน์ (Clinic Queue Booking System)

ระบบจัดการคิวและนัดหมายสำหรับคลินิกความงาม/คลินิกทั่วไป — **เป็นระบบหลังบ้านสำหรับเจ้าหน้าที่และแพทย์เท่านั้น ไม่มีหน้าจองสาธารณะ**
รองรับหลายสาขา (multi-branch), คิว walk-in, ตารางแพทย์, ฐานข้อมูลคนไข้, รายงาน และแจ้งเตือน SMS

รายละเอียดข้อกำหนดทั้งหมดอยู่ใน [CLAUDE.md](CLAUDE.md)

---

## 1. สถาปัตยกรรม

```
clinic/
├── backend/          Django 5.2 + DRF + Channels (REST API + WebSocket)
│   ├── config/       settings, urls, asgi/wsgi, celery
│   └── apps/
│       ├── common/         โครงสร้างพื้นฐานที่ใช้ร่วมกัน (ช่วงเวลา, permission, branch scoping)
│       ├── accounts/       ผู้ใช้ + JWT auth + role
│       ├── clinics/        สาขาและการตั้งค่าที่มีผลต่อการคำนวณคิว
│       ├── doctors/        แพทย์ ตารางออกตรวจ ช่วงเวลาที่ถูกบล็อก
│       ├── services/       ประเภทบริการ + ระยะเวลา
│       ├── scheduling/     ★ คำนวณเวลาว่าง + จองคิว (หัวใจของระบบ)
│       ├── queue/          หน้าจอคิวหน้างาน + walk-in + WebSocket
│       ├── patients/       ฐานข้อมูลคนไข้ + โน้ต + ค้นหา
│       ├── reports/        รายงานเชิงบริหาร (ORM aggregation)
│       └── notifications/  SMS reminder (Celery) + SMSLog
├── frontend/         Next.js 15 (App Router) + TypeScript + TailwindCSS
│   ├── app/          หน้าจอ + route handler (login/logout/proxy)
│   ├── components/   UI แยกตามโดเมน
│   ├── lib/api/      API client แยกเป็น class ต่อโดเมน
│   └── types/        type ที่ตรงกับ serializer ของ backend
└── docker-compose.yml
```

**การไหลของข้อมูล:** เบราว์เซอร์ → route handler ของ Next (`/api/proxy/...`) → Django REST API
token ถูกเก็บใน **httpOnly cookie** เท่านั้น JavaScript ในหน้าเว็บจึงไม่เคยแตะ token และ Next จะต่ออายุ token ให้อัตโนมัติเมื่อหมดอายุ

---

## 2. เริ่มใช้งานด้วย Docker (แนะนำ)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- Frontend: http://localhost:3000
- API docs (Swagger): http://localhost:8000/api/docs/
- Django admin: http://localhost:8000/admin/

สร้างข้อมูลตัวอย่างสำหรับ dev:

```bash
docker compose exec backend python manage.py seed_dev_data
```

---

## 3. เริ่มใช้งานแบบไม่ใช้ Docker

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_dev_data
python manage.py runserver 8000
```

> **หมายเหตุเรื่องฐานข้อมูล:** ระบบใช้ PostgreSQL เป็นมาตรฐาน (ตั้งค่าผ่าน `DATABASE_URL`)
> ถ้าไม่ได้ตั้งค่าไว้ จะ fallback ไปใช้ sqlite เพื่อให้รันเทสต์บนเครื่องที่ยังไม่มี PostgreSQL ได้
> โดย constraint ระดับฐานข้อมูลบางตัว (exclusion constraint กันคิวชน, trigram index)
> จะถูกข้ามบน sqlite — ส่วนการกันคิวชนระดับแอปพลิเคชันยังทำงานครบทุกกรณี **ก่อนขึ้น production ต้องใช้ PostgreSQL เสมอ**

### ต่อ PostgreSQL ของ Docker จาก `manage.py` บนเครื่อง

ไม่ต้องติดตั้ง PostgreSQL แยก — `docker-compose.yml` เปิดพอร์ต `5432` ออกมาที่เครื่องแล้ว
ค่าใน `backend/.env` ใช้ชื่อ service (`db`, `redis`) ซึ่งใช้ได้เฉพาะภายใน Docker network
เวลารันคำสั่งจากเครื่องตรง ๆ ให้ override เป็น `127.0.0.1`:

```bash
docker compose up -d db redis
```

```bash
cd backend && DATABASE_URL=postgres://clinic:clinic@127.0.0.1:5432/clinic REDIS_URL=redis://127.0.0.1:6379/0 python manage.py migrate
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env.local     # ชี้ BACKEND_INTERNAL_URL ไปที่ backend
npm run dev
```

---

## 4. บัญชีทดสอบ (หลังรัน `seed_dev_data`)

รหัสผ่านเดียวกันทุกบัญชี: `ClinicDev!2026`

| บทบาท | อีเมล | เห็นอะไร |
|---|---|---|
| Super Admin | `root@clinic.test` | ทุกสาขา + จัดการสาขา |
| ผู้จัดการสาขา | `admin.bkk@clinic.test`, `admin.cnx@clinic.test` | สาขาตัวเอง + รายงาน |
| เจ้าหน้าที่ | `staff.bkk@clinic.test`, `staff.cnx@clinic.test` | คิว/คนไข้ของสาขาตัวเอง |
| แพทย์ | `doctor.ploy@clinic.test` ฯลฯ | เฉพาะคิวของตัวเอง |

---

## 5. คำสั่งที่ใช้บ่อย

เทสต์ทั้งหมด (78 เทสต์) — ตั้ง `DATABASE_URL=` ว่างเพื่อใช้ sqlite ชั่วคราว
ถ้าไม่อยากพึ่ง PostgreSQL (ถ้าฐานจริงรันอยู่ ตัดตัวแปรนี้ออกได้เลย)

```bash
cd backend && DATABASE_URL= python manage.py test
```

```bash
cd backend && DATABASE_URL= python manage.py test apps.scheduling  # เฉพาะ logic คำนวณ slot และการจอง
```

```bash
cd frontend && npm run typecheck             # ตรวจ type ของ TypeScript
```

```bash
cd backend && celery -A config worker -l info   # worker ส่ง SMS (ต้องมี Redis)
```

```bash
cd backend && celery -A config beat -l info     # ตัวตั้งเวลาแจ้งเตือนนัดหมาย
```

---

## 6. API หลัก

| Endpoint | ใช้ทำอะไร |
|---|---|
| `POST /api/auth/login/` `refresh/` `logout/` `me/` | เข้าสู่ระบบด้วย JWT |
| `GET /api/scheduling/available-slots/?service_id=&doctor_id=&date=` | ช่วงเวลาที่ว่างจริง (หัก TimeBlock + คิวที่จองแล้ว) |
| `POST /api/scheduling/appointments/` | สร้างการจอง (ตรวจคิวชนที่ backend เสมอ) |
| `GET /api/queue/today/?date=&doctor_id=` | คิวของวันพร้อมสรุปจำนวน |
| `POST /api/queue/walk-in/` | รับคิว walk-in (ปฏิเสธเมื่อไม่มี slot ว่างจริง) |
| `PATCH /api/queue/appointments/{id}/status/` | เปลี่ยนสถานะตาม state machine |
| `PATCH /api/queue/appointments/{id}/reschedule/` | เลื่อน/สลับเวลาคิว |
| `GET /api/patients/search/?q=` | ค้นหาคนไข้ข้ามสาขา (เบอร์/ชื่อ/รหัส) |
| `GET /api/reports/summary/` `no-show-rate/` | รายงานยอดจอง, peak time, อัตราผิดนัด |
| `ws://<host>/ws/queue/{clinic_id}/?token=` | อัปเดตคิวแบบเรียลไทม์ |

ดูสัญญา API ฉบับเต็มที่ `/api/schema/` (OpenAPI) หรือ `/api/docs/`

---

## 7. กฎสำคัญของระบบที่มีเทสต์คุมไว้

1. **ห้าม overbook เด็ดขาด** — ทุกการสร้าง/เลื่อนคิว รวมถึง walk-in ต้องผ่าน
   `SlotAvailabilityService.is_slot_available()` ถ้าไม่มีเวลาว่างจริงจะตอบ `409 slot_unavailable`
2. **กันคิวชนสองชั้น** — ล็อกแถวทรัพยากร (แพทย์/สาขา) ด้วย `select_for_update` ภายใน transaction
   และมี exclusion constraint ของ PostgreSQL เป็นตาข่ายรองสุดท้าย
3. **ข้อมูลแยกตามสาขา** — ทุก queryset ผ่าน `BranchScopedQuerySetMixin` ยกเว้น Super Admin
4. **เวลา** — เก็บ UTC ในฐานข้อมูล คำนวณและแสดงผลด้วยโซนเวลาของสาขา (Asia/Bangkok)
5. **ไม่มี mock data** — ทุกหน้าจอเรียก API จริง ข้อมูลตัวอย่างอยู่ในคำสั่ง `seed_dev_data` แยกต่างหาก
