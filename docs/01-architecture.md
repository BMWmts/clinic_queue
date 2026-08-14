# 01 — สถาปัตยกรรมและการเชื่อมโยง / Architecture & wiring

---

## 1. ภาพรวม / Big picture

**TH:** ระบบแยกเป็นสองฝั่งชัดเจน — Next.js (หน้าจอ) และ Django REST Framework (ข้อมูล+กฎธุรกิจ)
เบราว์เซอร์ **ไม่เคย** ยิงไปที่ Django โดยตรง ทุกคำขอวิ่งผ่าน route handler ของ Next ที่ `/api/proxy/...`
ซึ่งเป็นตัวแนบ JWT จาก httpOnly cookie ให้ ผลคือ JavaScript ในหน้าเว็บไม่เคยเห็น token เลย
ยกเว้นทางเดียวคือ WebSocket ที่ต่อตรงไป Django (เพราะ browser แนบ header ใน handshake ไม่ได้)

**EN:** Two clearly separated halves — Next.js (UI) and Django REST Framework (data + business rules).
The browser **never** calls Django directly; every request goes through the Next route handler at
`/api/proxy/...`, which attaches the JWT from an httpOnly cookie. Page JavaScript therefore never
sees a token. The single exception is the WebSocket, which connects straight to Django (browsers
cannot attach headers during a WS handshake).

```
┌────────────── Browser ──────────────┐
│  React components                   │
│    └─ lib/api/index.ts  (API class) │
│         └─ lib/api/http.ts (fetch)  │
└──────────────┬──────────────────────┘
               │  /api/proxy/<path>        (cookie: clinic_access / clinic_refresh)
               ▼
┌────────── Next.js server ───────────┐
│  app/api/proxy/[...path]/route.ts   │  ← แนบ token + ต่ออายุอัตโนมัติเมื่อ 401
│  app/api/auth/{login,logout,ws-token}│  ← ออก/ล้าง cookie
│  middleware.ts                      │  ← กันหน้า dashboard ถ้าไม่มี session
└──────────────┬──────────────────────┘
               │  Authorization: Bearer <access>
               ▼
┌──────────── Django (DRF) ───────────┐
│  config/urls.py  →  apps/*/urls.py  │
│  views.py  →  services.py  →  models│
│  PostgreSQL                         │
└──────────────┬──────────────────────┘
               │  channels group "queue_updates_<clinic_id>"
               ▼
        WebSocket ws://…/ws/queue/<clinic_id>/?token=…
               ▲
               └──────── browser (lib/hooks/useQueueBoard.ts)
```

---

## 2. การไหลของหนึ่ง request / One request end-to-end

ตัวอย่าง: เจ้าหน้าที่กดปุ่ม "รับคิว Walk-in"
*Example: staff clicks "Add walk-in".*

| # | เกิดอะไรขึ้น (TH) | What happens (EN) | ไฟล์ / File |
|---|---|---|---|
| 1 | ผู้ใช้กรอกฟอร์มแล้วกดส่ง | User submits the dialog | `components/queue/WalkInDialog.tsx` |
| 2 | เรียก `queueApi.walkIn(...)` | Calls `queueApi.walkIn(...)` | `lib/api/index.ts` |
| 3 | `fetch("/api/proxy/queue/walk-in")` | Same | `lib/api/http.ts` |
| 4 | แนบ access token จาก cookie, ถ้า 401 ขอใหม่แล้วยิงซ้ำ | Attaches token from cookie; on 401 refreshes and retries | `app/api/proxy/[...path]/route.ts` |
| 5 | Django รับที่ `POST /api/queue/walk-in/` | Django receives it | `apps/queue/urls.py` → `views.WalkInView` |
| 6 | ตรวจสิทธิ์ role | Role permission check | `apps/common/permissions.CanOperateQueue` |
| 7 | หา clinic ของผู้ใช้ | Resolve the user's clinic | `apps/scheduling/views.resolve_request_clinic` |
| 8 | validate payload | Validate payload | `apps/queue/serializers.WalkInCreateSerializer` |
| 9 | หา/สร้างคนไข้จากเบอร์โทร | Find-or-create patient by phone | `apps/patients/services.PatientRegistrationService` |
| 10 | ★ หา slot ว่างที่เร็วที่สุด — **ไม่มีก็ปฏิเสธ** | ★ Find earliest free slot — **reject if none** | `apps/scheduling/services.SlotAvailabilityService` |
| 11 | ล็อกแถวแพทย์ + ตรวจซ้ำ + บันทึก | Lock doctor row, re-check, save | `apps/scheduling/services.AppointmentBookingService` |
| 12 | ยิง event หลัง commit | Broadcast after commit | `apps/scheduling/broadcast.py` → `apps/queue/realtime.py` |
| 13 | ทุกหน้าจอในสาขาได้รับ event | Every screen in the branch receives it | `apps/queue/consumers.py` → `lib/hooks/useQueueBoard.ts` |

**🔑 ถ้าขั้นที่ 10 ไม่ผ่าน:** backend ตอบ `409 {"error":{"code":"slot_unavailable"}}` → `http.ts` แปลงเป็น `ApiError`
→ `WalkInDialog` แสดงข้อความให้เลือกแพทย์ท่านอื่น **ไม่มีทางลัดใดที่ยัดคิวเกินได้**

**🔑 If step 10 fails:** backend answers `409 slot_unavailable` → `http.ts` turns it into `ApiError`
→ the dialog tells staff to pick another doctor. **There is no path that overbooks.**

---

## 3. แผนผังการพึ่งพาของแอป backend / Backend app dependency map

**TH:** ลูกศรอ่านว่า "พึ่งพา" — สังเกตว่า `common` ไม่พึ่งใครเลย และ `queue` ยืมกฎการจองทั้งหมดจาก `scheduling`
ไม่มีการเขียนกฎซ้ำ

**EN:** Arrows mean "depends on". Note `common` depends on nothing, and `queue` borrows *all*
booking rules from `scheduling` — no rule is duplicated.

```
                    common  (ไม่พึ่งใคร / depends on nothing)
                      ▲  ▲  ▲  ▲
        ┌─────────────┘  │  │  └──────────────┐
     accounts         clinics services      patients
        ▲                ▲       ▲             ▲
        └──── doctors ───┘       │             │
                 ▲               │             │
                 └──── scheduling ─────────────┘   ★ หัวใจระบบ / core
                          ▲            ▲
                        queue      reports
                          ▲            
                    notifications
```

| แอป / App | รับผิดชอบ (TH) | Responsibility (EN) |
|---|---|---|
| `common` | ช่วงเวลา, timezone, permission, mixin, exception | Intervals, timezone, permissions, mixins, exceptions |
| `accounts` | ผู้ใช้ + role + JWT | Users, roles, JWT |
| `clinics` | สาขา + ค่าตั้งค่าที่มีผลต่อการคำนวณคิว | Branches + settings that drive slot math |
| `doctors` | แพทย์, ตารางออกตรวจ, ช่วงเวลาที่ถูกบล็อก | Doctors, weekly schedules, time blocks |
| `services` | แคตตาล็อกบริการ + ระยะเวลา | Service catalog + durations |
| `scheduling` ★ | คำนวณเวลาว่าง + จอง/เลื่อน/ยกเลิก | Slot availability + book/reschedule/cancel |
| `queue` | งานหน้าเคาน์เตอร์ + realtime | Front-desk operations + realtime |
| `patients` | ฐานข้อมูลคนไข้ + ค้นหา + โน้ต | Patient DB, search, notes |
| `reports` | รายงานจาก aggregation | Reports via ORM aggregation |
| `notifications` | SMS reminder ผ่าน Celery | SMS reminders via Celery |

---

## 4. ชั้นของโค้ดฝั่ง backend / Backend layering

**TH:** ทุกแอปใช้โครงเดียวกัน แก้ที่ชั้นถูกต้องแล้วจะไม่พังที่อื่น

**EN:** Every app follows the same layering; change the right layer and nothing else breaks.

| ชั้น / Layer | ไฟล์ / File | หน้าที่ (TH) | Responsibility (EN) |
|---|---|---|---|
| URL | `urls.py` | จับคู่ path → view | Map path → view |
| View | `views.py` | แปลง HTTP ↔ service | Translate HTTP ↔ service |
| Serializer | `serializers.py` | validate + แปลงรูปข้อมูล | Validate + shape data |
| Permission | `permissions.py` / `common/permissions.py` | 🔒 ใครทำอะไรได้ | 🔒 Who may do what |
| Service | `services.py` | ★ กฎธุรกิจทั้งหมด | ★ All business rules |
| Model | `models.py` | ข้อมูล + logic ที่ผูกกับข้อมูลนั้น | Data + logic bound to that data |

**🔑 กฎ:** ถ้าเขียน `if` ที่เกี่ยวกับกฎธุรกิจใน `views.py` แปลว่าวางผิดชั้น — ย้ายไป `services.py`
**🔑 Rule:** a business-rule `if` inside `views.py` is in the wrong layer — move it to `services.py`.

---

## 5. ชั้นของโค้ดฝั่ง frontend / Frontend layering

| ชั้น / Layer | ที่อยู่ / Location | หน้าที่ (TH) | Responsibility (EN) |
|---|---|---|---|
| Page | `app/(dashboard)/*/page.tsx` | Server Component บาง ๆ ตั้ง title + วาง component | Thin server component: title + mount |
| Component | `components/<domain>/*.tsx` | UI + state ของหน้าจอ | UI + screen state |
| Hook | `lib/hooks/*` | state ที่ใช้ซ้ำ (เซสชัน, ข้อมูลคิว) | Reusable state (session, queue data) |
| API client | `lib/api/index.ts` | หนึ่ง class ต่อหนึ่งโดเมน | One class per domain |
| Transport | `lib/api/http.ts` | fetch + แปลง error | fetch + error mapping |
| Route handler | `app/api/**/route.ts` | 🔒 จัดการ token/cookie | 🔒 Token & cookie handling |
| Types | `types/api.ts` | สัญญาข้อมูลที่ตรงกับ serializer | Contract matching the serializers |

**🔑 กฎ:** component **ห้าม** เรียก `fetch()` เอง ต้องผ่าน api client เสมอ
**🔑 Rule:** components must **never** call `fetch()` directly — always go through an API client.

---

## 6. ที่มาของ "เวลาว่าง" / Where "free time" comes from

**TH:** สูตรเดียวที่ทั้งระบบใช้ ไม่ว่าจะจองจากหน้าไหน:

**EN:** One formula the whole system uses, no matter which screen books:

```
เวลาว่างจริง / real free time
  = ตารางออกตรวจของแพทย์ (DoctorSchedule)      ← doctors/models.py
  ∩ เวลาเปิด-ปิดของสาขา (Clinic)                ← clinics/models.py
  − ช่วงเวลาที่ถูกบล็อก (TimeBlock)             ← doctors/services.py
  − คิวที่ยังกินเวลา (Appointment.occupying)     ← scheduling/models.py
  แล้วซอยเป็นช่อง ๆ ตาม slot_interval_minutes   ← common/time_intervals.py
  และตัดช่วงที่ยาวไม่พอ duration_minutes ออก     ← services/models.py
```

**🔑 บริการที่ไม่ต้องมีแพทย์** ใช้อีกสูตร: นับคิวที่ซ้อนกัน แล้วเทียบกับ `clinic.non_doctor_service_capacity`
(เช่น มีเตียงดริป 3 เตียง → รับพร้อมกันได้ 3 คิว)

**🔑 Services not requiring a doctor** use a different rule: count overlapping appointments and
compare against `clinic.non_doctor_service_capacity` (e.g. 3 drip beds → 3 concurrent slots).

---

## 7. การกันคิวชน 3 ชั้น / Three layers of collision protection

| ชั้น | กลไก (TH) | Mechanism (EN) | ไฟล์ / File |
|---|---|---|---|
| 1 | หน้าจอแสดงเฉพาะเวลาที่ backend บอกว่าว่าง | UI only offers slots the backend returned | `BookingDialog.tsx`, `RescheduleDialog.tsx` |
| 2 | ★ ล็อกแถวทรัพยากร + ตรวจซ้ำใน transaction | ★ Row lock on the resource + re-check inside the transaction | `scheduling/services.py` |
| 3 | exclusion constraint ของ PostgreSQL | PostgreSQL exclusion constraint | `scheduling/migrations/0002_...` |

**🔑 ชั้นที่ 1 เป็นแค่ UX** — ถึงมีคนแก้ request เองก็ยังผ่านชั้น 2 และ 3 ไม่ได้
**🔑 Layer 1 is UX only** — a hand-crafted request still cannot get past layers 2 and 3.
