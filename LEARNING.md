# LEARNING.md — เรียนรู้โปรเจกต์นี้ตั้งแต่ศูนย์

> คู่มือสำหรับ **มือใหม่** ที่ต้องมาดูแล/ต่อยอดระบบจองคิวคลินิกนี้
> อ่านจากบนลงล่างได้เลย แต่ละบทมี "เป้าหมาย", "เนื้อหา", และ "ลองทำ" ให้ฝึกจริง
>
> *A hands-on course for newcomers to this clinic queue system. Each chapter has a goal, an
> explanation, and an exercise. Written in Thai with English technical terms.*

**คู่มืออธิบายโค้ดรายไฟล์ (ไทย/อังกฤษ) อยู่ที่ [`docs/`](docs/README.md)** — เอกสารนี้สอน *ภาพรวมและวิธีคิด*
ส่วน `docs/` เป็น *พจนานุกรมรายไฟล์* ใช้คู่กัน

---

## สารบัญ

| บท | หัวข้อ | ใช้เวลาโดยประมาณ |
|---|---|---|
| 0 | [ก่อนเริ่ม: ต้องรู้อะไรมาก่อน](#บทที่-0-ก่อนเริ่ม) | 10 นาที |
| 1 | [ระบบนี้แก้ปัญหาอะไรให้ใคร](#บทที่-1-ระบบนี้แก้ปัญหาอะไร) | 15 นาที |
| 2 | [ติดตั้งและรันให้เห็นของจริง](#บทที่-2-ติดตั้งและรัน) | 30 นาที |
| 3 | [เดินตามคิวหนึ่งใบตั้งแต่ต้นจนจบ](#บทที่-3-เดินตามคิวหนึ่งใบ) | 45 นาที |
| 4 | [แนวคิดที่ 1: ช่วงเวลาและการคำนวณเวลาว่าง](#บทที่-4-แนวคิดที่-1-ช่วงเวลา) | 60 นาที |
| 5 | [แนวคิดที่ 2: ห้าม overbook — กันคิวชน 3 ชั้น](#บทที่-5-แนวคิดที่-2-ห้าม-overbook) | 60 นาที |
| 6 | [แนวคิดที่ 3: หลายสาขา (multi-branch)](#บทที่-6-แนวคิดที่-3-หลายสาขา) | 30 นาที |
| 7 | [แนวคิดที่ 4: เวลาและ timezone](#บทที่-7-แนวคิดที่-4-เวลาและ-timezone) | 30 นาที |
| 8 | [แนวคิดที่ 5: token ที่ JavaScript แตะไม่ได้](#บทที่-8-แนวคิดที่-5-token-ที่-javascript-แตะไม่ได้) | 40 นาที |
| 9 | [แนวคิดที่ 6: realtime และการถอยไป polling](#บทที่-9-แนวคิดที่-6-realtime) | 30 นาที |
| 10 | [อ่านโค้ด Django ให้เป็น](#บทที่-10-อ่านโค้ด-django-ให้เป็น) | 60 นาที |
| 11 | [อ่านโค้ด Next.js ให้เป็น](#บทที่-11-อ่านโค้ด-nextjs-ให้เป็น) | 60 นาที |
| 12 | [เทสต์: อ่านและเขียนเพิ่ม](#บทที่-12-เทสต์) | 45 นาที |
| 13 | [ลงมือ: เพิ่มฟีเจอร์แรกของคุณ](#บทที่-13-ลงมือเพิ่มฟีเจอร์แรก) | 2 ชั่วโมง |
| 14 | [กับดักที่มือใหม่ตกบ่อย](#บทที่-14-กับดักที่มือใหม่ตกบ่อย) | 20 นาที |
| 15 | [คำศัพท์ + ไปต่อทางไหน](#บทที่-15-คำศัพท์และไปต่อ) | 15 นาที |

---

# บทที่ 0: ก่อนเริ่ม

**เป้าหมาย:** รู้ว่าต้องมีพื้นฐานอะไร และเตรียมเครื่องอย่างไร

## ต้องรู้อะไรมาก่อน

| หัวข้อ | ระดับที่ต้องการ | ถ้ายังไม่รู้ ให้ไปอ่าน |
|---|---|---|
| Python พื้นฐาน | อ่าน class/function/type hint ได้ | docs.python.org tutorial |
| Django + DRF | ไม่ต้องรู้มาก่อน — บทที่ 10 สอนให้ | Django Girls Tutorial |
| TypeScript/React | อ่าน component + `useState` ได้ | react.dev learn |
| SQL | ไม่จำเป็น (เราใช้ ORM เท่านั้น) | — |
| Git | เพิ่ม/commit ได้ | — |

**ไม่ต้องรู้:** Redis, Celery, WebSocket, Docker — โปรเจกต์ตั้งค่าให้หมดแล้ว บทที่เกี่ยวข้องจะอธิบายเท่าที่จำเป็น

## ต้องมีในเครื่อง

- Python 3.12+
- Node.js 20+
- (ทางเลือก) Docker Desktop — ถ้ามีจะง่ายที่สุด

## 3 ไฟล์ที่ต้องรู้จักก่อนเปิดโค้ด

| ไฟล์ | คืออะไร |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | **ข้อกำหนดต้นทาง** — ทุกกฎในระบบมาจากที่นี่ ถ้าสงสัยว่า "ทำไมโค้ดเป็นแบบนี้" ให้กลับมาอ่าน |
| [`README.md`](README.md) | วิธีติดตั้งและรัน |
| [`docs/README.md`](docs/README.md) | คู่มืออธิบายโค้ดรายไฟล์ |

> **💡 นิสัยที่ควรสร้างตั้งแต่วันแรก:** ก่อนแก้อะไร ให้ถามตัวเองว่า *"ข้อกำหนดข้อไหนใน CLAUDE.md
> ที่ทำให้โค้ดเดิมเป็นแบบนี้"* โค้ดในโปรเจกต์นี้เกือบทั้งหมดมีเหตุผลรองรับ ไม่ใช่ความบังเอิญ

---

# บทที่ 1: ระบบนี้แก้ปัญหาอะไร

**เป้าหมาย:** เข้าใจ "ธุรกิจ" ก่อนเข้าใจโค้ด

## สถานการณ์จริงที่ระบบนี้รองรับ

คลินิกความงามมีหลายสาขา แต่ละสาขามีแพทย์หลายคน คนไข้มาสองแบบ:

1. **นัดล่วงหน้า** — โทรมาหรือมาจองที่เคาน์เตอร์ เจ้าหน้าที่จองให้
2. **Walk-in** — เดินเข้ามาเลย เจ้าหน้าที่ต้องหาช่องเวลาว่างให้ทันที

**⚠️ สิ่งที่ระบบนี้ไม่มี:** หน้าเว็บให้ลูกค้าจองเอง — **ทุกการจองสร้างโดยเจ้าหน้าที่เท่านั้น**
นี่คือเหตุผลที่ `Appointment.source` มีแค่ `staff_created` กับ `walk_in` ไม่มี `online`

## ใครใช้ระบบนี้บ้าง

| บทบาท | ทำอะไรได้ | ทำอะไรไม่ได้ |
|---|---|---|
| **Super Admin** | ทุกอย่าง ทุกสาขา | — |
| **ผู้จัดการสาขา (Admin)** | จัดการแพทย์/บริการ/ตาราง/ดูรายงาน — **เฉพาะสาขาตัวเอง** | ข้ามไปสาขาอื่น, สร้างบัญชี super admin |
| **เจ้าหน้าที่ (Staff)** | จัดการคิว, walk-in, คนไข้ — เฉพาะสาขาตัวเอง | ดูรายงาน, จัดการสาขา |
| **แพทย์ (Doctor)** | ดูตารางตัวเอง, อัปเดตสถานะ **คิวของตัวเองเท่านั้น** | แตะคิวของแพทย์ท่านอื่น |

## กฎธุรกิจข้อเดียวที่สำคัญที่สุด

> ### 🚫 ห้าม overbook เด็ดขาด
> ถ้าไม่มีเวลาว่างจริง ระบบต้อง **ปฏิเสธ** ไม่มีข้อยกเว้น — รวมถึงคิว walk-in

**ทำไมถึงเข้มขนาดนี้?** เพราะการยัดคิวเกินหมายถึงคนไข้นั่งรอนานเกินจริง แพทย์ทำงานเกินเวลา
และคลินิกเสียชื่อ ระบบจึงถูกออกแบบให้ **เป็นไปไม่ได้ทางเทคนิค** ที่จะ overbook ไม่ใช่แค่ "ไม่ควรทำ"

กฎข้อนี้เป็นที่มาของโค้ดจำนวนมาก:
- `SlotAvailabilityService` (คำนวณเวลาว่างจริง)
- `select_for_update` (กัน race condition)
- exclusion constraint ใน PostgreSQL (ตาข่ายสุดท้าย)
- เทสต์ 37 ตัวใน `apps/scheduling/tests/`

## 🔨 ลองทำ

เปิด [`CLAUDE.md`](CLAUDE.md) แล้วหาหัวข้อ **"11. การตัดสินใจที่ยืนยันแล้ว"**
อ่านตาราง 4 แถวนั้นให้จบ — สี่บรรทัดนี้อธิบายเหตุผลของสถาปัตยกรรมทั้งระบบ

---

# บทที่ 2: ติดตั้งและรัน

**เป้าหมาย:** เห็นระบบทำงานจริงในเบราว์เซอร์ภายใน 30 นาที

## ทางที่ 1 — Docker (ง่ายที่สุด)

```bash
cp backend/.env.example backend/.env
```

```bash
docker compose up --build
```

```bash
docker compose exec backend python manage.py seed_dev_data
```

## ทางที่ 2 — ไม่ใช้ Docker

```bash
cd backend && python -m venv .venv && .venv/Scripts/activate && pip install -r requirements.txt
```

```bash
cd backend && cp .env.example .env && python manage.py migrate && python manage.py seed_dev_data
```

```bash
cd backend && python manage.py runserver 8000
```

เปิดอีก terminal:

```bash
cd frontend && npm install && npm run dev
```

## เข้าใช้งาน

เปิด http://localhost:3000 แล้ว login — **รหัสผ่านทุกบัญชี: `ClinicDev!2026`**

| ลอง login ด้วย | แล้วสังเกต |
|---|---|
| `staff.bkk@clinic.test` | เมนูมีแค่ คิว/ตารางแพทย์/คนไข้ — **ไม่มี** รายงานกับสาขา |
| `admin.bkk@clinic.test` | เมนูเพิ่ม รายงาน + สาขา (แต่แก้สาขาไม่ได้) |
| `root@clinic.test` | เห็นทุกอย่าง + เพิ่มสาขาได้ |
| `doctor.ploy@clinic.test` | หน้าคิวแสดง **เฉพาะคิวของหมอพลอย** |

**นี่คือ multi-branch + role-based permission ที่ทำงานจริง** — จำภาพนี้ไว้ บทที่ 6 จะอธิบายว่าโค้ดทำได้อย่างไร

## รันเทสต์

```bash
cd backend && DATABASE_URL= python manage.py test
```

ควรได้ **78 tests ผ่านทั้งหมด** ถ้าไม่ผ่านให้แก้ก่อนไปต่อ

## 🔨 ลองทำ

1. เปิด http://localhost:8000/api/docs/ (Swagger) — เลื่อนดู endpoint ทั้งหมด
2. ไปที่หน้า "ตารางแพทย์" ในเว็บ กดช่องว่างสีขาว → ลองจองคิวหนึ่งใบ
3. กลับไปหน้า "คิววันนี้" เปลี่ยนวันเป็นวันที่คุณจอง → เห็นคิวที่เพิ่งสร้าง

---

# บทที่ 3: เดินตามคิวหนึ่งใบ

**เป้าหมาย:** รู้ว่าเมื่อกดปุ่มหนึ่งครั้ง โค้ดวิ่งผ่านไฟล์ไหนบ้าง — นี่คือทักษะที่สำคัญที่สุดในการดูแลโปรเจกต์

## สถานการณ์: เจ้าหน้าที่กด "รับคิว Walk-in"

เปิดไฟล์ตามลำดับนี้ทีละไฟล์ อ่านคร่าว ๆ แล้วไปต่อ:

### ฝั่งเบราว์เซอร์

**1️⃣ `frontend/components/queue/WalkInDialog.tsx`**
ฟอร์มที่ผู้ใช้กรอก → ฟังก์ชัน `handleSubmit()` เรียก `queueApi.walkIn({...})`

**2️⃣ `frontend/lib/api/index.ts` → class `QueueApiClient`**
```ts
walkIn(payload) { return this.http.post<Appointment>("/queue/walk-in", payload); }
```
สั้นมาก เพราะหน้าที่มันคือ "จำ path ของ API แทน component"

**3️⃣ `frontend/lib/api/http.ts` → `HttpClient.post()`**
ยิง `fetch("/api/proxy/queue/walk-in")` — สังเกตว่า **ไม่มี token ตรงนี้เลย**

### ฝั่ง Next.js server

**4️⃣ `frontend/app/api/proxy/[...path]/route.ts`**
- แปลง path เป็น `/api/queue/walk-in/`
- อ่าน access token จาก **httpOnly cookie** แล้วแนบเป็น `Authorization: Bearer ...`
- ถ้าได้ 401 → refresh token แล้วยิงซ้ำอัตโนมัติ

> 💡 **นี่คือหัวใจของ auth ทั้งระบบ** — บทที่ 8 อธิบายละเอียด

### ฝั่ง Django

**5️⃣ `backend/apps/queue/urls.py`** → จับคู่ path กับ `WalkInView`

**6️⃣ `backend/apps/queue/views.py` → `WalkInView.post()`**
สังเกตว่า view **สั้นมาก** ทำแค่ 4 อย่าง: หาสาขา → validate → เรียก service → คืน response
**ไม่มีกฎธุรกิจอยู่ใน view เลย** — นี่คือหลักการที่ต้องรักษาไว้

**7️⃣ `backend/apps/queue/serializers.py` → `WalkInCreateSerializer`**
ตรวจว่าส่ง `patient` (คนเดิม) **หรือ** `new_patient` (คนใหม่) มาอย่างใดอย่างหนึ่ง

**8️⃣ `backend/apps/queue/services.py` → `QueueService.add_walk_in()`**
หาคนไข้เดิมจากเบอร์โทร (ไม่มีก็สร้างใหม่) แล้วส่งต่อให้ booking service

**9️⃣ ★ `backend/apps/scheduling/services.py` → `AppointmentBookingService.book_walk_in()`**
```python
slot = availability.find_next_available_slot(search_from, search_days=1)
if slot is None:
    raise SlotUnavailableError("วันนี้ไม่มีช่วงเวลาว่างเหลือแล้ว ...")
return self.book(...)
```
**นี่คือจุดที่กฎ "ห้าม overbook" ถูกบังคับใช้จริง**

**🔟 `AppointmentBookingService.book()`**
```python
with transaction.atomic():
    self._lock_resource(doctor)                    # ล็อกแถวแพทย์
    if not availability.is_slot_available(interval):
        raise SlotUnavailableError(...)            # ตรวจซ้ำ
    self._save_guarding_overlap(appointment)       # บันทึก
```

**1️⃣1️⃣ `backend/apps/scheduling/broadcast.py`** → ส่ง event ให้ทุกหน้าจอในสาขา

### กลับสู่เบราว์เซอร์

**1️⃣2️⃣ `frontend/lib/hooks/useQueueBoard.ts`** → รับ event ผ่าน WebSocket แล้วเพิ่มคิวใหม่เข้ารายการ

## ภาพสรุป

```
WalkInDialog → QueueApiClient → HttpClient → proxy route → Django URL
   → WalkInView → WalkInCreateSerializer → QueueService
   → AppointmentBookingService ★ (ด่านห้าม overbook)
   → บันทึก → broadcast → useQueueBoard → หน้าจอทุกเครื่องอัปเดต
```

## 🔨 ลองทำ

**แบบฝึกหัดที่ 1:** เดินตามเส้นทางของ **"เปลี่ยนสถานะคิว"** ด้วยตัวเอง
เริ่มจาก `QueueBoard.tsx` ปุ่มในคอลัมน์ "การจัดการ" แล้วไล่ไปจนถึง `Appointment.apply_status()`
จดชื่อไฟล์ที่ผ่านลงกระดาษ (ควรได้ประมาณ 8-9 ไฟล์)

**แบบฝึกหัดที่ 2:** ใส่ `print()` หรือ `logger.info()` ใน `AppointmentBookingService.book()`
แล้วลองจองคิวจากหน้าเว็บ ดูว่า log ขึ้นจริงไหม — ยืนยันว่าคุณเข้าใจเส้นทางถูกต้อง

---

# บทที่ 4: แนวคิดที่ 1 — ช่วงเวลา

**เป้าหมาย:** เข้าใจ "หัวใจ" ของระบบ — การคำนวณเวลาว่าง

## ปัญหา

คำถามง่าย ๆ ว่า *"หมอพลอยว่างช่วงไหนบ้างวันจันทร์"* จริง ๆ แล้วซับซ้อนมาก เพราะต้องคิดว่า:

- หมอออกตรวจ 09:00–12:00 และ 13:00–17:00 (สองช่วง)
- แต่คลินิกเปิด 09:00–19:00 (ตัดขอบ)
- พักเที่ยง 12:00–13:00 (ตัดออก — แต่รอบนี้ไม่ทับอยู่แล้ว)
- มีประชุม 14:00–15:00 (เจาะกลางช่วงบ่าย → แตกเป็นสองช่วง)
- มีคิวจองแล้ว 10:00–10:30 และ 16:00–16:30 (ตัดออกอีก)
- บริการที่จะจองใช้เวลา 45 นาที (ช่องที่สั้นกว่านี้ใช้ไม่ได้)
- ระบบเสนอเวลาทุก 15 นาที (09:00, 09:15, 09:30, ...)
- ถ้าเป็นวันนี้ ห้ามเสนอเวลาที่ผ่านไปแล้ว

**ถ้าเขียนโค้ดนี้แบบไม่มีโครงสร้าง จะได้ `if` ซ้อนกัน 6 ชั้นที่ไม่มีใครกล้าแก้**

## วิธีแก้: แยกเป็น "คณิตศาสตร์ของช่วงเวลา"

เปิด `backend/apps/common/time_intervals.py` — ไฟล์นี้ **ไม่รู้จัก Django หรือคลินิกเลย**
มันรู้แค่เรื่อง "ช่วงเวลา"

### `TimeInterval` — ช่วงเวลาหนึ่งช่วง

```python
morning = TimeInterval(9:00, 12:00)
lunch   = TimeInterval(12:00, 13:00)

morning.overlaps_with(lunch)   # False! ← จุดที่ต้องเข้าใจ
morning.subtract(lunch)        # [9:00-12:00] ไม่โดนตัดเลย
```

### ⭐ กฎ half-open `[start, end)`

**"คิวที่จบ 10:00 กับคิวที่เริ่ม 10:00 ไม่ชนกัน"**

ฟังดูเป็นรายละเอียดเล็ก ๆ แต่ถ้าตัดสินใจผิดจะเกิดอย่างใดอย่างหนึ่ง:
- ถ้าถือว่าชน → จองติดกันไม่ได้เลย เสียเวลาแพทย์วันละหลายชั่วโมง
- ถ้าไม่ระวังให้สม่ำเสมอ → บางที่ชน บางที่ไม่ชน เกิด bug ที่หาไม่เจอ

โปรเจกต์นี้ใช้ half-open **ทุกที่** รวมถึงใน SQL ของ PostgreSQL (`tstzrange(..., '[)')`)

### `subtract()` — คืนได้ 0, 1 หรือ 2 ช่วง

```
ช่วงทำงาน:  |========13:00-17:00========|
ประชุม:            |==14:00-15:00==|
ผลลัพธ์:    |=13-14=|              |=15-17=|   ← 2 ช่วง!
```

### `IntervalSet` — กลุ่มช่วงเวลา

แทน "เวลาว่างของแพทย์ทั้งวัน" ซึ่งมีได้หลายช่วง มันจัดการการรวมช่วงที่ต่อกันให้อัตโนมัติ

### `generate_slot_starts()` — ซอยเป็น slot

```python
generate_slot_starts(
    free_time,             # เวลาว่าง
    duration_minutes=45,   # บริการใช้ 45 นาที
    step_minutes=15,       # เสนอทุก 15 นาที
    not_before=now,        # ไม่เสนอเวลาที่ผ่านไปแล้ว
)
```

## สูตรเต็มอยู่ที่ไหน

เปิด `backend/apps/scheduling/services.py` → `SlotAvailabilityService._doctor_free_time()`

```python
schedule_free_time = DoctorAvailabilityService(doctor).free_intervals_on(date)
booked = self._booked_intervals(self._doctor_appointments_on(date))
return schedule_free_time.subtract(booked)
```

**สามบรรทัด** — เพราะความซับซ้อนถูกซ่อนไว้ในชั้นล่างที่ทดสอบครบแล้ว
นี่คือประโยชน์ของการแยกชั้นที่จับต้องได้จริง

## 🔨 ลองทำ

**แบบฝึกหัดที่ 1 — เล่นกับ interval ใน shell:**

```bash
cd backend && DATABASE_URL= python manage.py shell
```

```python
from datetime import datetime
from apps.common.time_intervals import TimeInterval, IntervalSet, generate_slot_starts

work = TimeInterval(datetime(2026,8,17,9), datetime(2026,8,17,17))
lunch = TimeInterval(datetime(2026,8,17,12), datetime(2026,8,17,13))
free = IntervalSet([work]).subtract([lunch])
print(free)                                    # เห็นสองช่วง
print(len(generate_slot_starts(free, 30, 15))) # นับ slot ที่ได้
```

ลองเปลี่ยน `30` เป็น `240` (บริการ 4 ชั่วโมง) แล้วดูว่าเหลือกี่ slot — เข้าใจไหมว่าทำไม?

**แบบฝึกหัดที่ 2:** อ่าน `backend/apps/common/tests/test_time_intervals.py` ทั้งไฟล์
เทสต์ 18 ตัวนี้คือ "คู่มือการใช้งาน" ที่ดีที่สุดของโมดูลนี้

---

# บทที่ 5: แนวคิดที่ 2 — ห้าม overbook

**เป้าหมาย:** เข้าใจว่าทำไมต้องกันคิวชนถึง 3 ชั้น

## ปัญหาที่มองไม่เห็นด้วยตาเปล่า

สมมติเจ้าหน้าที่สองคนที่สาขาเดียวกัน กดจองเวลา 10:00 ของหมอพลอย **พร้อมกันเป๊ะ ๆ**

```
เวลา    เจ้าหน้าที่ A            เจ้าหน้าที่ B
────────────────────────────────────────────────
t1      ตรวจ: 10:00 ว่างไหม?
t2                              ตรวจ: 10:00 ว่างไหม?
t3      ✅ ว่าง!
t4                              ✅ ว่าง!          ← ทั้งคู่เห็นว่าว่าง
t5      บันทึกคิว
t6                              บันทึกคิว        ← 💥 คิวชนกัน!
```

**นี่คือ race condition** — โค้ดถูกต้องทุกบรรทัด แต่ผลลัพธ์ผิด เพราะ "ตรวจ" กับ "บันทึก" ไม่ได้เกิดพร้อมกัน
และมันเกิดขึ้น **จริง** ในคลินิกที่มีเคาน์เตอร์หลายจุด

## ชั้นที่ 1 — UI แสดงเฉพาะเวลาที่ว่าง

`BookingDialog.tsx` เรียก `availableSlots()` แล้วแสดงเป็นปุ่ม ผู้ใช้กดเวลาที่ไม่ว่างไม่ได้

**⚠️ ชั้นนี้เป็นแค่ UX ไม่ใช่ security** — ใครก็ตามที่เปิด DevTools แล้วยิง request เองก็ข้ามชั้นนี้ได้ทันที
**ห้ามไว้ใจ input จาก client เด็ดขาด**

## ⭐ ชั้นที่ 2 — ล็อกแถว + ตรวจใน transaction เดียวกัน

เปิด `backend/apps/scheduling/services.py` → `AppointmentBookingService.book()`

```python
with transaction.atomic():          # เปิด transaction
    self._lock_resource(doctor)     # ← ล็อกแถวของหมอคนนี้
    if not availability.is_slot_available(interval):
        raise SlotUnavailableError(...)
    self._save_guarding_overlap(appointment)
```

`_lock_resource()` ทำแค่บรรทัดเดียว:
```python
Doctor.objects.select_for_update().get(pk=doctor.pk)
```

**`select_for_update()` แปลว่า "ล็อกแถวนี้ไว้จนกว่า transaction จะจบ"**
ผลคือลำดับเหตุการณ์เปลี่ยนเป็น:

```
t1   A: ล็อกแถวหมอพลอย 🔒
t2   B: ขอล็อก... รอ ⏳
t3   A: ตรวจ → ว่าง → บันทึก → commit → ปลดล็อก
t4   B: ได้ล็อก 🔒 → ตรวจ → ❌ ไม่ว่างแล้ว → 409
```

**เจ้าหน้าที่ B ได้รับข้อความ "ช่วงเวลาที่เลือกไม่ว่างแล้ว" แทนที่จะสร้างคิวชน** ✅

> 💡 **ทำไมล็อกที่แถว `Doctor` ไม่ใช่ `Appointment`?**
> เพราะคิวที่จะสร้างยัง**ไม่มี**อยู่ในตาราง จะล็อกอะไรไม่ได้ เราจึงล็อก "ทรัพยากรที่กำลังถูกแย่ง"
> คือตัวแพทย์ (หรือสาขา ถ้าเป็นบริการที่ไม่ใช้แพทย์) แทน

## ชั้นที่ 3 — ฐานข้อมูลปฏิเสธเอง

เปิด `backend/apps/scheduling/migrations/0002_appointment_overlap_exclusion.py`

```sql
EXCLUDE USING gist (
    doctor_id WITH =,
    tstzrange(scheduled_start, scheduled_end, '[)') WITH &&
) WHERE (doctor_id IS NOT NULL AND status IN ('booked','confirmed',...))
```

อ่านว่า: *"หมอคนเดียวกัน + ช่วงเวลาซ้อนกัน + ยังกินเวลาอยู่ → ห้ามมีเกินหนึ่งแถว"*

**ทำไมต้องมีทั้งที่ชั้น 2 ทำงานอยู่แล้ว?**
เพราะปีหน้าอาจมีใครเขียน script import ข้อมูล หรือ endpoint ใหม่ที่ลืมเรียกผ่าน service layer
ชั้นนี้ป้องกัน **ความผิดพลาดของนักพัฒนา** ไม่ใช่ของผู้ใช้ — และมันไม่มีวันลืม

## สถานะไหนที่ "กินเวลา"

```python
OCCUPYING_STATUSES = (BOOKED, CONFIRMED, CHECKED_IN, IN_PROGRESS, COMPLETED)
# cancelled และ no_show ไม่อยู่ในนี้ → คืนเวลาให้ตารางทันที
```

**ผลที่เห็นได้จริง:** พอเจ้าหน้าที่กด "ยกเลิก" คิว 10:00 เวลานั้นจะกลับมาให้จองได้ทันทีโดยไม่ต้องทำอะไรเพิ่ม
เพราะทุกการคำนวณกรองด้วย `.occupying()` อยู่แล้ว

## 🔨 ลองทำ

**แบบฝึกหัดที่ 1 — พิสูจน์ชั้นที่ 2 ด้วยตัวเอง:**
อ่านเทสต์ `test_exact_duplicate_time_is_rejected` และ `test_back_to_back_booking_is_allowed`
ใน `backend/apps/scheduling/tests/test_booking_service.py`

**แบบฝึกหัดที่ 2 — ทำลายระบบ (แล้วซ่อมคืน):**
ลองคอมเมนต์บรรทัด `self._lock_resource(doctor)` ออก แล้วรันเทสต์

```bash
cd backend && DATABASE_URL= python manage.py test apps.scheduling
```

เทสต์ยังผ่านหมด! **ทำไม?** เพราะเทสต์รันทีละ request ไม่ได้จำลอง concurrent จริง
→ บทเรียน: **บางบั๊กเทสต์จับไม่ได้** ต้องเข้าใจเหตุผลของโค้ด ไม่ใช่พึ่งเทสต์อย่างเดียว
(อย่าลืม uncomment กลับ!)

**แบบฝึกหัดที่ 3:** ลองยิง `POST /api/scheduling/appointments/` จาก Swagger ด้วยเวลาที่มีคิวอยู่แล้ว
→ ควรได้ `409` พร้อม `"code": "slot_unavailable"`

---

# บทที่ 6: แนวคิดที่ 3 — หลายสาขา

**เป้าหมาย:** เข้าใจว่าข้อมูลถูกกั้นระหว่างสาขาอย่างไร

## ปัญหา

ระบบมีหลายสาขา เจ้าหน้าที่สาขาสุขุมวิท **ต้องไม่เห็น** คิวของสาขาเชียงใหม่
ถ้าต้องเขียน `.filter(clinic=user.clinic)` ในทุก view ทั้ง 30 กว่าจุด → สักวันจะมีคนลืม
และการลืมครั้งเดียวคือข้อมูลรั่วข้ามสาขา

## วิธีแก้: เขียนครั้งเดียวใน mixin

เปิด `backend/apps/common/mixins.py`

```python
class BranchScopedQuerySetMixin:
    clinic_lookup = "clinic"

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.can_access_all_branches:        # Super Admin
            requested = self.request.query_params.get("clinic_id")
            return queryset.filter(clinic_id=requested) if requested else queryset

        if user.clinic_id is None:
            return queryset.none()              # ไม่มีสาขา = ไม่เห็นอะไรเลย

        return queryset.filter(clinic_id=user.clinic_id)
```

ViewSet ไหนอยากได้แค่สืบทอด:

```python
class AppointmentViewSet(BranchScopedQuerySetMixin, viewsets.ModelViewSet):
    ...
```

## แล้วตอน "เขียน" ล่ะ?

`perform_create()` ในมิกซินเดียวกันเติม `clinic` และ `created_by` ให้อัตโนมัติ
**โดยไม่เชื่อค่าที่ client ส่งมา** — ต่อให้ยิง `{"clinic": 99}` ก็ถูกทับด้วยสาขาของผู้ใช้เอง

## สองด่านที่ต้องแยกให้ออก

| | ตอบคำถามว่า | อยู่ที่ไหน |
|---|---|---|
| **Permission** | "role นี้ทำ action นี้ได้ไหม" | `common/permissions.py` |
| **Branch scoping** | "เห็นข้อมูลของสาขาไหน" | `common/mixins.py` |

ต้องผ่าน **ทั้งสอง** ถึงจะเข้าถึงข้อมูลได้ เช่น เจ้าหน้าที่สาขา A ผ่าน permission (เป็น staff)
แต่ไม่ผ่าน scoping เมื่อขอข้อมูลสาขา B

## ข้อยกเว้นเดียว: คนไข้

`apps/patients/` **ไม่ใช้** mixin นี้ เพราะข้อกำหนดข้อ 4.8 บอกว่าคนไข้ค้นข้ามสาขาได้
(ลูกค้าคนเดียวกันเดินเข้าได้หลายสาขา ไม่ควรต้องสร้างประวัติซ้ำ)

**แต่การ *สร้าง* คนไข้ยังผูกกับสาขาของผู้ใช้เสมอ** ผ่าน `home_clinic`
→ ข้อยกเว้นถูกจำกัดขอบเขตไว้อย่างชัดเจน ไม่ใช่ปล่อยหลุดทั้งแอป

## 🔨 ลองทำ

1. Login เป็น `staff.bkk@clinic.test` เปิด DevTools → Network
2. ไปหน้าคิว ดู request ไปที่ `/api/proxy/queue/today` — **ไม่มี `clinic_id` ใน query string**
3. แต่ผลลัพธ์มีแค่คิวสาขา BKK → **backend เป็นคนตัดสินใจ ไม่ใช่ frontend** ✅
4. ลองแก้ URL ใส่ `?clinic_id=2` ดู → ยังได้แค่สาขาตัวเอง (mixin ไม่สนใจ param นี้ถ้าไม่ใช่ Super Admin)
5. อ่านเทสต์ `test_staff_cannot_read_other_branch_appointment_directly` ใน `apps/accounts/tests/`

---

# บทที่ 7: แนวคิดที่ 4 — เวลาและ timezone

**เป้าหมาย:** เข้าใจกฎเวลาของโปรเจกต์ ไม่ให้เขียนบั๊กที่หายาก

## กฎเหล็กสองข้อ

> **1. ฐานข้อมูลเก็บ UTC เสมอ**
> **2. คำนวณและแสดงผลด้วยโซนเวลาของสาขา**

`settings.py` ตั้ง `USE_TZ = True` และ `TIME_ZONE = "Asia/Bangkok"`
ส่วน `Clinic.timezone` ให้แต่ละสาขากำหนดโซนของตัวเองได้ (เผื่ออนาคตขยายข้ามประเทศ)

## ทำไมต้องระวัง

**ตัวอย่างบั๊กที่เกิดจริงถ้าไม่ระวัง:**
คิวเวลา 06:00 น. วันที่ 15 (เวลาไทย) = 23:00 น. วันที่ **14** ใน UTC
ถ้าถามว่า "คิววันที่ 15 มีอะไรบ้าง" ด้วยการกรอง UTC ตรง ๆ → **คิวนี้หายไป**

## วิธีแก้: `timezone_utils.py`

```python
from apps.common.timezone_utils import local_day_bounds

day_start, day_end = local_day_bounds(target_date, clinic.timezone)
# ได้ขอบเขต 00:00–24:00 ตามเวลาไทย (เก็บเป็น aware datetime)
```

| ฟังก์ชัน | ใช้เมื่อ |
|---|---|
| `combine_local(date, time, tz)` | ประกอบวัน+เวลานาฬิกา → datetime (เช่น ตารางแพทย์ "09:00") |
| `local_day_bounds(date, tz)` | หาขอบเขตของ "วันนั้น" ตามปฏิทินท้องถิ่น |
| `to_local(dt, tz)` | แปลงไปเวลาท้องถิ่นเพื่อแสดงผล |
| `local_date_of(dt, tz)` | ถามว่า datetime นี้เป็นวันที่เท่าไรตามปฏิทินท้องถิ่น |

## ฝั่ง frontend

`lib/format.ts` ตรึง `timeZone: "Asia/Bangkok"` ในทุก formatter
→ ต่อให้เครื่องเจ้าหน้าที่ตั้งโซนผิด หน้าจอก็ยังแสดงเวลาไทยถูกต้อง

## จุดที่ต้องระวังเป็นพิเศษ

| สถานการณ์ | ต้องใช้ |
|---|---|
| กรองคิว "วันนี้" | `local_day_bounds()` **ห้ามใช้** `date.today()` เฉย ๆ |
| ตารางแพทย์ (เก็บเป็น `TimeField`) | `combine_local()` เพื่อประกอบกับวันที่ |
| รายงานรายวัน/รายชั่วโมง | `TruncDate(..., tzinfo=zone)` เสมอ |
| พักเที่ยงแบบซ้ำ | `TimeBlock.occurrence_on()` ยึดเวลานาฬิกาท้องถิ่น |

## 🔨 ลองทำ

```bash
cd backend && DATABASE_URL= python manage.py shell
```

```python
from datetime import date
from apps.common.timezone_utils import local_day_bounds
start, end = local_day_bounds(date(2026, 8, 15), "Asia/Bangkok")
print(start, end)                          # เวลาไทย
print(start.astimezone(None), end.astimezone(None))  # ลองดูใน UTC/local ของเครื่อง
```

สังเกตว่า "วันที่ 15 ตามเวลาไทย" เริ่มตอน 17:00 ของวันที่ 14 ใน UTC — **นี่คือเหตุผลที่ต้องมีโมดูลนี้**

---

# บทที่ 8: แนวคิดที่ 5 — token ที่ JavaScript แตะไม่ได้

**เป้าหมาย:** เข้าใจการออกแบบ auth ที่ปลอดภัยกว่า `localStorage`

## ปัญหาของวิธีที่คนทำกันทั่วไป

วิธียอดนิยม: เก็บ JWT ใน `localStorage` แล้วแนบใน header เอง

**ช่องโหว่:** ถ้ามี XSS แม้แต่จุดเดียว (เช่นโน้ตคนไข้ที่มี `<script>` แล้วเผลอ render แบบดิบ)
โค้ดของผู้โจมตีเรียก `localStorage.getItem("token")` ได้ทันที → ยึดบัญชีได้เลย

## วิธีของโปรเจกต์นี้

```
เบราว์เซอร์  ──(cookie httpOnly แนบอัตโนมัติ)──►  Next.js server
                                                        │
                                            อ่าน cookie แล้วแนบ Bearer token
                                                        ▼
                                                     Django
```

**JavaScript ในหน้าเว็บไม่เคยเห็น token เลยแม้แต่ครั้งเดียว** เพราะ cookie ตั้ง `httpOnly: true`
ซึ่งแปลว่า `document.cookie` อ่านไม่ได้

## อ่านโค้ด 4 ไฟล์นี้ตามลำดับ

**1️⃣ `frontend/lib/auth/cookies.ts`** — ตั้ง cookie สองใบ
```ts
httpOnly: true,     // ← JS อ่านไม่ได้ (ป้องกัน XSS ขโมย token)
secure: isProduction,
sameSite: "lax",    // ← ลดความเสี่ยง CSRF
```

**2️⃣ `frontend/app/api/auth/login/route.ts`** — login แล้ว **คืนเฉพาะข้อมูลผู้ใช้**
```ts
const response = NextResponse.json({ user: payload.user });   // ไม่มี token!
setSessionCookies(response, { access: payload.access, refresh: payload.refresh });
```

**3️⃣ ★ `frontend/app/api/proxy/[...path]/route.ts`** — พระเอกของเรื่อง
```ts
if (backendResponse.status === 401 && refreshToken) {
  refreshedTokens = await refreshAccessToken(refreshToken);
  if (refreshedTokens) {
    backendResponse = await callBackend(...);   // ยิงซ้ำแบบผู้ใช้ไม่รู้สึก
  } else {
    clearSessionCookies(expiredResponse);       // refresh ตายแล้ว → บังคับ login ใหม่
  }
}
```

**ผลลัพธ์ที่ผู้ใช้สัมผัสได้:** กรอกฟอร์มยาว ๆ แล้ว access token หมดอายุระหว่างนั้น
→ กดบันทึกยังสำเร็จ ไม่โดนเด้งออก ไม่เสียข้อมูลที่พิมพ์

**4️⃣ `backend/apps/accounts/views.py` → `RefreshView`**
```python
old_refresh.blacklist()                    # ยกเลิกใบเก่าทันที
new_refresh = RefreshToken.for_user(user)  # ออกใบใหม่
```
เรียกว่า **token rotation** — ถ้า refresh token รั่วไป ใบนั้นใช้ได้ครั้งเดียวเท่านั้น

## ข้อยกเว้นเดียว: WebSocket

เบราว์เซอร์แนบ header ใน WS handshake **ไม่ได้** จึงต้องส่ง token ผ่าน query string
`ws-token/route.ts` จึงคืน access token (อายุสั้น) ให้ JS ใช้เฉพาะตอนต่อ socket

**ข้อแลกเปลี่ยนที่ยอมรับอย่างมีสติ:** token ใบนี้อายุแค่ 15 นาที ส่วน refresh token
ยังอยู่ใน httpOnly cookie เสมอ — และถ้าไม่ยอมรับความเสี่ยงนี้ ก็ลบ `NEXT_PUBLIC_WS_URL`
แล้วระบบจะใช้ polling แทนทันที

> 💡 **บทเรียนสำคัญ:** งานความปลอดภัยจริงคือการ **ตัดสินใจแลกเปลี่ยนอย่างมีสติและเขียนบันทึกไว้**
> ไม่ใช่การไล่ปิดทุกช่องจนระบบใช้งานไม่ได้ สังเกตว่า docstring ของ `ws-token/route.ts`
> อธิบายข้อแลกเปลี่ยนนี้ไว้ชัดเจน

## 🔨 ลองทำ

1. Login แล้วเปิด DevTools → Console พิมพ์ `document.cookie`
   → **ไม่เห็น `clinic_access` เลย** ✅ (นี่คือ `httpOnly` ทำงาน)
2. เปิด Application → Cookies → เห็นทั้งสองใบพร้อมเครื่องหมาย ✓ ในคอลัมน์ HttpOnly
3. ลบ cookie `clinic_access` ทิ้ง (เหลือ `clinic_refresh`) แล้วกดรีเฟรชหน้าคิว
   → **ยังใช้งานได้ปกติ** เพราะ proxy refresh ให้อัตโนมัติ
4. ลบทั้งสองใบ → กดรีเฟรช → ถูกพากลับหน้า login ✅

---

# บทที่ 9: แนวคิดที่ 6 — realtime

**เป้าหมาย:** เข้าใจ WebSocket ในโปรเจกต์นี้ และทำไมต้องมี polling คู่กัน

## ปัญหา

หน้าเคาน์เตอร์มีจอ 3 เครื่อง ถ้าเครื่อง A รับคิว walk-in แล้วเครื่อง B ยังไม่เห็น
→ B อาจจองเวลาเดียวกันซ้ำ (backend ปฏิเสธก็จริง แต่ประสบการณ์ใช้งานแย่)

## การไหลของ event

```
มีคนจองคิว
   ↓
QueueService → broadcast_appointment_event()
   ↓
QueueBroadcaster.broadcast()
   ↓ transaction.on_commit()  ← สำคัญ!
channel layer (Redis) → group "queue_updates_1"
   ↓
QueueConsumer ทุกตัวที่ต่ออยู่กับสาขา 1
   ↓
useQueueBoard → applyUpdatedAppointment() → หน้าจออัปเดต
```

## จุดออกแบบที่ควรเรียนรู้ 3 ข้อ

### 1️⃣ `transaction.on_commit()` — ส่งหลัง commit เท่านั้น

```python
transaction.on_commit(lambda: cls._send_now(clinic_id, event_type, payload))
```

**ถ้าส่งก่อน commit:** หน้าจออื่นได้รับ event → รีบ fetch ข้อมูล → **ยังไม่เจอคิวที่เพิ่งสร้าง**
เพราะ transaction ยังไม่จบ = bug ที่เกิดเป็นครั้งคราวและ debug ยากมาก

### 2️⃣ ล้มเหลวได้ แต่ต้องไม่พาระบบล้มตาม

```python
try:
    async_to_sync(channel_layer.group_send)(...)
except Exception:
    logger.exception("ส่งอัปเดตคิวแบบเรียลไทม์ไม่สำเร็จ ...")
```

Redis ล่ม → **การจองคิวต้องยังสำเร็จ** เพราะ realtime เป็นฟีเจอร์เสริม ไม่ใช่ฟีเจอร์หลัก
การจับ exception กว้าง ๆ ปกติเป็น anti-pattern แต่ที่นี่ **ถูกต้อง** และมีคอมเมนต์อธิบายไว้

### 3️⃣ Polling ยังทำงานเสมอ

เปิด `frontend/lib/hooks/useQueueBoard.ts`:
```ts
const intervalId = window.setInterval(() => { void refresh(); }, POLLING_INTERVAL_MS);
```

**ทำงานตลอด แม้ WebSocket ต่อติดอยู่** เพราะ socket อาจหลุดเงียบ ๆ โดยที่ `onclose` ไม่ยิง
(เกิดจริงกับ WiFi หน้าร้านที่สัญญาณไม่นิ่ง) — polling ทุก 10 วินาทีคือตาข่ายรอง

**ป้ายบนหน้าจอ** "● เรียลไทม์" / "○ อัปเดตทุก 10 วิ" บอกสถานะให้เจ้าหน้าที่รู้ตัว

## ความปลอดภัยของ WebSocket 🔒

`QueueConsumer.connect()` ปฏิเสธสองกรณี:
- ไม่มี token / token ไม่ถูกต้อง → ปิดด้วยรหัส **4401**
- ขอต่อสาขาที่ไม่มีสิทธิ์ → ปิดด้วยรหัส **4403**

และ **รับแค่ `ping` เท่านั้น** — ไม่รับคำสั่งแก้ไขข้อมูลผ่าน WebSocket
ทุกการเขียนต้องผ่าน REST API ที่มี permission + validation ครบ

## 🔨 ลองทำ

1. เปิดเบราว์เซอร์ **สองหน้าต่าง** login เป็น staff คนเดียวกัน เปิดหน้าคิวทั้งคู่
2. หน้าต่างที่ 1 เปลี่ยนสถานะคิวหนึ่งใบ
3. หน้าต่างที่ 2 → เปลี่ยนตามภายในไม่กี่วินาที ✅
4. ปิด Redis (`docker compose stop redis`) แล้วลองอีกครั้ง
   → ป้ายเปลี่ยนเป็น "○ อัปเดตทุก 10 วิ" แต่ **ระบบยังใช้งานได้ครบทุกฟังก์ชัน**

---

# บทที่ 10: อ่านโค้ด Django ให้เป็น

**เป้าหมาย:** เปิดไฟล์ไหนก็รู้ว่ากำลังดูอะไรอยู่

## โครงเดียวกันทุกแอป

```
apps/<ชื่อแอป>/
├── models.py       ← ข้อมูล + logic ที่ผูกกับข้อมูลนั้น
├── services.py     ← ★ กฎธุรกิจทั้งหมด
├── serializers.py  ← validate + แปลงรูปข้อมูล (JSON ↔ Python)
├── views.py        ← แปลง HTTP ↔ service (ควรบางที่สุด)
├── urls.py         ← จับคู่ path กับ view
├── permissions.py  ← 🔒 ใครทำอะไรได้ (ถ้ามีเฉพาะของแอปนั้น)
├── admin.py        ← หน้า Django admin
├── migrations/     ← ประวัติการเปลี่ยนโครงสร้างฐานข้อมูล
└── tests/          ← เทสต์
```

## ตัวอย่างจริง: อ่าน `Appointment` ทีละชั้น

### ชั้น model — `apps/scheduling/models.py`

```python
class Appointment(AuditableModel):
    patient = models.ForeignKey("patients.Patient", ...)
    scheduled_start = models.DateTimeField(db_index=True)
    status = models.CharField(choices=AppointmentStatus.choices, ...)

    @property
    def interval(self) -> TimeInterval:          # ← logic ที่ผูกกับข้อมูลนี้โดยตรง
        return TimeInterval(self.scheduled_start, self.scheduled_end)

    def apply_status(self, new_status: str) -> None:
        if not self.can_transition_to(new_status):
            raise InvalidStatusTransitionError(...)
        ...
```

**ทำไม `apply_status()` อยู่ใน model ไม่ใช่ service?**
เพราะมันใช้ข้อมูลของ appointment ตัวเองเท่านั้น ไม่ต้องดูข้อมูลรอบข้าง
→ **หลักการ:** logic ที่ใช้แค่ข้อมูลตัวเอง = model, logic ที่ต้องดูข้อมูลอื่น = service

### ชั้น service — `apps/scheduling/services.py`

```python
class AppointmentBookingService:
    def book(self, *, patient, service_type, scheduled_start, ...):
        # ต้องดู: ตารางแพทย์, TimeBlock, คิวอื่น, เวลาทำการสาขา
        # → เป็นงานของ service ชัดเจน
```

### ชั้น serializer — `apps/scheduling/serializers.py`

```python
class AppointmentCreateSerializer(serializers.Serializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.filter(is_active=True))
    scheduled_start = serializers.DateTimeField()
    # ไม่มี scheduled_end / clinic → client กำหนดเองไม่ได้ 🔒
```

**สังเกต:** `queryset=...filter(is_active=True)` = ส่ง id ของคนไข้ที่ถูกปิดใช้งานมาก็ไม่ผ่าน
DRF ตรวจให้อัตโนมัติ

### ชั้น view — `apps/scheduling/views.py`

```python
def create(self, request, *args, **kwargs):
    clinic = resolve_request_clinic(request)          # 1. หาสาขา
    serializer = AppointmentCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)         # 2. validate
    appointment = booking.book(...)                   # 3. เรียก service
    broadcast_appointment_event(...)                  # 4. แจ้งเตือน
    return Response(AppointmentSerializer(appointment).data, status=201)
```

**7 บรรทัด ไม่มีกฎธุรกิจสักบรรทัด** — นี่คือเป้าหมายของทุก view ในโปรเจกต์นี้

## Django ORM ที่ใช้บ่อยในโปรเจกต์นี้

| โค้ด | แปลว่า |
|---|---|
| `.filter(clinic_id=1)` | `WHERE clinic_id = 1` |
| `.select_related("patient")` | JOIN มาด้วยเลย (กัน N+1 query) |
| `.annotate(total=Count("id"))` | เพิ่มคอลัมน์คำนวณ |
| `.aggregate(total=Count("id"))` | สรุปทั้ง queryset เป็นตัวเลขเดียว |
| `Count("id", filter=Q(status="completed"))` | นับแบบมีเงื่อนไข (ใช้เยอะในรายงาน) |
| `.select_for_update()` | 🔒 ล็อกแถวใน transaction |
| `Q(a=1) \| Q(b=2)` | `WHERE a=1 OR b=2` |

**⚠️ โปรเจกต์นี้ใช้ ORM เท่านั้น ห้ามเขียน raw SQL ต่อสตริง** (ป้องกัน SQL injection)
ข้อยกเว้นคือ migration ที่เป็น DDL คงที่ ไม่มีค่าจากผู้ใช้

## 🔨 ลองทำ

**แบบฝึกหัด — จำแนกชั้น:** เปิด `backend/apps/queue/services.py`
ตอบว่าแต่ละ method ควรอยู่ชั้นไหนถ้าออกแบบใหม่ และทำไม:
- `queue_summary()` — ใช้ aggregate ข้ามหลายแถว → service ✅
- `_resolve_walk_in_patient()` — ต้องดูข้อมูลคนไข้ทั้งตาราง → service ✅
- ลองหาว่ามี method ไหนที่ **น่าจะ** ย้ายไป model ได้ไหม? (คำใบ้: ไม่มี — ลองคิดว่าทำไม)

---

# บทที่ 11: อ่านโค้ด Next.js ให้เป็น

**เป้าหมาย:** เข้าใจ App Router และโครงฝั่ง frontend

## Server Component vs Client Component

**กฎง่าย ๆ:** ถ้าไฟล์มี `"use client"` บรรทัดแรก = ทำงานในเบราว์เซอร์ ถ้าไม่มี = ทำงานบน server

| ประเภท | ใช้ทำอะไร | ตัวอย่างในโปรเจกต์ |
|---|---|---|
| **Server Component** | หน้าที่ไม่ต้อง interactive, ตั้ง metadata | `app/(dashboard)/queue/page.tsx` |
| **Client Component** | ต้องใช้ `useState`, event handler, `fetch` จากเบราว์เซอร์ | `components/queue/QueueBoard.tsx` |

**รูปแบบที่ใช้ทั้งโปรเจกต์:** page เป็น Server Component บาง ๆ ที่วาง Client Component ไว้ข้างใน

```tsx
// page.tsx — Server Component
export const metadata = { title: "คิววันนี้ | ..." };
export default function QueuePage() {
  return <div><h1>คิวหน้างาน</h1><QueueBoard /></div>;   // ← QueueBoard เป็น "use client"
}
```

## Route Group: `(auth)` และ `(dashboard)`

โฟลเดอร์ที่ชื่อในวงเล็บ **ไม่ปรากฏใน URL** ใช้แค่จัดกลุ่มเพื่อแชร์ layout
- `app/(auth)/login/page.tsx` → URL คือ `/login`
- `app/(dashboard)/queue/page.tsx` → URL คือ `/queue` (แต่ได้ layout ที่มี sidebar)

## Route Handler = API ของ Next เอง

ไฟล์ `route.ts` (ไม่ใช่ `page.tsx`) = endpoint ฝั่ง server ของ Next
โปรเจกต์นี้ใช้ 4 ตัว: `login`, `logout`, `ws-token`, และ `proxy/[...path]` (catch-all)

## กฎ 2 ข้อของฝั่ง frontend

### 1️⃣ Component ห้ามเรียก `fetch()` เอง

```tsx
// ❌ ผิด
const res = await fetch("/api/proxy/queue/today");

// ✅ ถูก
const data = await queueApi.today({ date });
```

**ทำไม?** เพราะเวลา backend เปลี่ยน path หรือ contract จะต้องไล่แก้ทุก component
ถ้ารวมไว้ใน `lib/api/index.ts` แก้ที่เดียวจบ (และ TypeScript จะบอกทุกจุดที่พัง)

### 2️⃣ หน้าจอห้ามคำนวณเวลาว่างเอง

```tsx
// ✅ ถูก — ถาม backend เสมอ
const response = await schedulingApi.availableSlots({ service_id, date, doctor_id });
setSlots(response.slots);
```

**ทำไม?** เพราะกฎการคำนวณ slot ซับซ้อนมาก (ตาราง + บล็อก + คิว + capacity + เวลาทำการ)
ถ้าเขียนซ้ำฝั่ง UI จะไม่มีวันตรงกับ backend 100% → หน้าจอบอกว่าว่าง แต่จองแล้วได้ 409 = ผู้ใช้สับสน

## จัดการ error ให้ผู้ใช้เข้าใจ

```tsx
try {
  await queueApi.walkIn({...});
} catch (error) {
  setErrorMessage(error instanceof ApiError ? error.message : "รับคิว walk-in ไม่สำเร็จ");
}
```

`ApiError.message` เป็นภาษาไทยที่ backend เขียนไว้แล้ว (เช่น "วันนี้ไม่มีช่วงเวลาว่างเหลือแล้ว
กรุณาเลือกแพทย์ท่านอื่นหรือนัดเป็นวันอื่น") → **ข้อความ error อยู่ที่เดียวคือ backend**

## TypeScript ช่วยยังไง

`types/api.ts` ประกาศ type ที่ตรงกับ serializer ทุกตัว

**สถานการณ์จริง:** backend เพิ่ม field `cancelled_reason` ใน `AppointmentSerializer`
→ เพิ่มใน `types/api.ts` → รัน `npm run typecheck` → TS บอกทุกจุดที่ต้องแก้

```bash
cd frontend && npm run typecheck
```

**⚠️ ห้ามใช้ `any`** — ถ้าใช้ ประโยชน์ทั้งหมดข้างบนหายไปทันที

## 🔨 ลองทำ

1. เปิด `frontend/components/queue/QueueBoard.tsx` หาว่าปุ่มเปลี่ยนสถานะมาจากไหน
   → เจอ `appointment.allowed_next_statuses` ที่ **backend ส่งมา**
2. ตอบคำถาม: ถ้าอยากเพิ่มสถานะใหม่ `rescheduled` ต้องแก้กี่ไฟล์ฝั่ง frontend?
   (คำตอบ: `types/api.ts` + `lib/format.ts` (STATUS_STYLES) = **2 ไฟล์**
   ส่วน logic ว่ากดได้เมื่อไรมาจาก backend อัตโนมัติ)

---

# บทที่ 12: เทสต์

**เป้าหมาย:** อ่านเทสต์เป็น และเขียนเพิ่มได้

## ทำไมเทสต์ในโปรเจกต์นี้กระจุกอยู่ที่ scheduling

จาก 78 เทสต์ มี **38 ตัว** อยู่ที่ `apps/scheduling/` และ 18 ตัวที่ `time_intervals`
เพราะที่นี่คือจุดที่ **พังแล้วเจ็บที่สุด** — คิวชนกันหมายถึงคนไข้สองคนมาเจอกันหน้าห้องตรวจ

**บทเรียน:** เทสต์ไม่ต้องครอบคลุมทุกบรรทัด แต่ต้องครอบคลุม **ส่วนที่พังแล้วเสียหายมากที่สุด**

## อ่านเทสต์ที่ดีสักตัว

```python
def test_back_to_back_booking_is_allowed(self) -> None:
    self.book_at(hour=10)                          # จองคิว 10:00-10:30

    appointment = self.booking.book(               # จองต่อทันที 10:30
        patient=..., service_type=self.service,
        doctor=self.doctor, scheduled_start=bangkok_datetime(self.monday, 10, 30),
    )

    self.assertEqual(appointment.scheduled_start, bangkok_datetime(self.monday, 10, 30))
```

**สังเกต 3 อย่าง:**
1. **ชื่อเทสต์อ่านเป็นประโยคได้** — "back to back booking is allowed"
2. **โครงสร้าง Arrange → Act → Assert** ชัดเจน
3. **ทดสอบ 1 พฤติกรรมต่อ 1 เทสต์** ไม่ยัดหลายอย่างรวมกัน

## Fixture ที่ใช้ซ้ำได้

```python
from apps.scheduling.tests.factories import ClinicTestDataMixin, bangkok_datetime, next_monday

class MyTests(ClinicTestDataMixin, TestCase):
    def setUp(self):
        self.clinic = self.create_clinic()
        self.doctor = self.create_doctor(clinic=self.clinic)   # มาพร้อมตารางจันทร์ 9-17
        self.service = self.create_service(duration_minutes=30)
        self.patient = self.create_patient(clinic=self.clinic)
        self.monday = next_monday()                            # ← วันจันทร์ในอนาคตเสมอ
```

**⚠️ ทำไมต้อง `next_monday()` ไม่ใช่วันที่ hardcode?**
เพราะระบบมีกฎ "ห้ามจองเวลาที่ผ่านไปแล้ว" ถ้า hardcode วันที่ เทสต์จะผ่านวันนี้แต่พังปีหน้า

## 🔨 ลองทำ: เขียนเทสต์ของคุณเอง

**โจทย์:** เขียนเทสต์พิสูจน์ว่า *"คิวที่ถูกทำเครื่องหมาย no_show คืนเวลาให้คนอื่นจองได้"*

เปิด `backend/apps/scheduling/tests/test_booking_service.py` แล้วเพิ่มใน
`class AppointmentBookingTests`:

```python
def test_no_show_appointment_releases_the_slot(self) -> None:
    appointment = self.book_at(hour=10)
    appointment.status = AppointmentStatus.NO_SHOW
    appointment.save(update_fields=["status"])

    # ควรจองเวลาเดิมได้อีกครั้ง
    replacement = self.booking.book(
        patient=self.patient,
        service_type=self.service,
        doctor=self.doctor,
        scheduled_start=bangkok_datetime(self.monday, 10),
    )
    self.assertIsNotNone(replacement.pk)
```

```bash
cd backend && DATABASE_URL= python manage.py test apps.scheduling
```

**คำถามชวนคิด:** เทสต์นี้ผ่านเพราะโค้ดบรรทัดไหน? (คำใบ้: `OCCUPYING_STATUSES` ใน `models.py`)

---

# บทที่ 13: ลงมือเพิ่มฟีเจอร์แรก

**เป้าหมาย:** ทำครบทุกชั้นตั้งแต่ model ถึงหน้าจอ

## โจทย์: เพิ่มช่อง "เหตุผลที่มา" (chief complaint) ในคิว

ให้เจ้าหน้าที่บันทึกได้ว่าคนไข้มาด้วยเรื่องอะไร แล้วแสดงบนหน้าคิว

### ขั้นที่ 1 — Model

`backend/apps/scheduling/models.py` เพิ่มใน `Appointment`:

```python
chief_complaint = models.CharField(
    "เหตุผลที่มา", max_length=255, blank=True,
    help_text='เช่น "ผิวแพ้ง่าย", "ปรึกษาเรื่องฝ้า"',
)
```

```bash
cd backend && python manage.py makemigrations scheduling
```

### ขั้นที่ 2 — Serializer

`serializers.py`:
- เพิ่ม `"chief_complaint"` ใน `AppointmentSerializer.Meta.fields`
- เพิ่มใน `AppointmentCreateSerializer`:
  ```python
  chief_complaint = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
  ```

### ขั้นที่ 3 — Service

`services.py` → `AppointmentBookingService.book()` รับพารามิเตอร์ใหม่แล้วส่งต่อไป `Appointment(...)`

**❓ คำถามสำคัญ:** ทำไมต้องแก้ที่ service ด้วย แก้แค่ serializer ไม่ได้เหรอ?
**คำตอบ:** เพราะ view ไม่ได้เรียก `serializer.save()` แต่เรียก `booking.book(...)` โดยส่งค่าทีละตัว
→ นี่คือราคาของการแยกชั้น service แลกกับความชัดเจนว่า "การจองเกิดขึ้นที่เดียว"

### ขั้นที่ 4 — View

`views.py` ส่งค่าจาก serializer เข้า service:
```python
chief_complaint=serializer.validated_data.get("chief_complaint", ""),
```

### ขั้นที่ 5 — Type ฝั่ง frontend

`frontend/types/api.ts` เพิ่มใน `interface Appointment`:
```ts
chief_complaint: string;
```

```bash
cd frontend && npm run typecheck
```

### ขั้นที่ 6 — API client

`lib/api/index.ts` → `SchedulingApiClient.book()` เพิ่ม `chief_complaint?: string` ใน payload type

### ขั้นที่ 7 — UI

`components/booking/BookingDialog.tsx` เพิ่ม state + `<Field>` แล้วส่งไปกับ `book()`
`components/queue/QueueBoard.tsx` → `QueueRow` แสดงค่าในคอลัมน์ "คนไข้"

### ขั้นที่ 8 — เทสต์

```python
def test_booking_stores_chief_complaint(self) -> None:
    appointment = self.booking.book(
        patient=self.patient, service_type=self.service, doctor=self.doctor,
        scheduled_start=bangkok_datetime(self.monday, 10),
        chief_complaint="ปรึกษาเรื่องฝ้า",
    )
    self.assertEqual(appointment.chief_complaint, "ปรึกษาเรื่องฝ้า")
```

### ✅ เช็คลิสต์

- [ ] มี migration commit คู่กับการแก้ model
- [ ] `python manage.py test` ผ่านทั้ง 78+ ตัว
- [ ] `npm run typecheck` ผ่าน
- [ ] มี type hint ครบ, ไม่มี `any`
- [ ] ไม่มี business logic ใน view
- [ ] เทสต์ใหม่อย่างน้อย 1 ตัว
- [ ] ทดลองใช้จริงบนหน้าเว็บแล้ว

## 🔨 โจทย์ต่อยอด (ยากขึ้นตามลำดับ)

| ระดับ | โจทย์ |
|---|---|
| ⭐ | เพิ่มปุ่ม "ส่งออก CSV" ในหน้ารายงาน |
| ⭐⭐ | เพิ่มตัวกรอง "เฉพาะคิวที่ยังไม่เสร็จ" ในหน้าคิว |
| ⭐⭐⭐ | เพิ่มรายงานใหม่: "คิวเฉลี่ยต่อวันในแต่ละสาขา" (Super Admin เท่านั้น) |
| ⭐⭐⭐⭐ | เพิ่มการแจ้งเตือนครั้งที่สอง 2 ชั่วโมงก่อนนัด (ระวัง unique constraint ของ `SMSLog`!) |

---

# บทที่ 14: กับดักที่มือใหม่ตกบ่อย

## 🚫 1. เขียน business logic ใน view

```python
# ❌ ผิด
def create(self, request):
    if Appointment.objects.filter(doctor=doctor, scheduled_start=start).exists():
        return Response({"error": "ชนกัน"}, status=409)
```
**ปัญหา:** กฎนี้จะไม่ถูกใช้ตอน walk-in, ตอน reschedule, ตอน seed → เกิดช่องโหว่ทันที
**✅ ถูก:** เรียก `AppointmentBookingService` ซึ่งทุกทางเข้าใช้ร่วมกัน

## 🚫 2. ลืม branch scoping

```python
# ❌ ผิด
class MyViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all()      # ทุกสาขาเห็นหมด! 🔥
```
**✅ ถูก:** สืบทอด `BranchScopedQuerySetMixin` เสมอ (ยกเว้น patients ที่ตั้งใจข้ามสาขา)

## 🚫 3. เชื่อค่าที่ client ส่งมา

```python
# ❌ ผิด
clinic = Clinic.objects.get(pk=request.data["clinic_id"])
```
**✅ ถูก:** `resolve_request_clinic(request)` หรือ `resolve_clinic_for_write()`

## 🚫 4. คำนวณเวลาว่างฝั่ง frontend

```tsx
// ❌ ผิด
const slots = generateSlots(doctorSchedule);   // จะไม่มีวันตรงกับ backend
```
**✅ ถูก:** `schedulingApi.availableSlots(...)` เสมอ

## 🚫 5. ใช้ `date.today()` แทน timezone-aware

```python
# ❌ ผิด — คิวหัวค่ำอาจตกวันผิด
Appointment.objects.filter(scheduled_start__date=date.today())
```
**✅ ถูก:** `local_day_bounds(target_date, clinic.timezone)`

## 🚫 6. เก็บ token ใน localStorage

**✅ ถูก:** httpOnly cookie ผ่าน route handler เท่านั้น (บทที่ 8)

## 🚫 7. แก้ model แล้วไม่สร้าง migration

```bash
cd backend && python manage.py makemigrations
```
**ผลถ้าลืม:** เครื่องคุณรันได้ (เพราะ DB เก่ายังอยู่) แต่คนอื่นและ production พังทันที

## 🚫 8. ใช้ `any` ใน TypeScript

**ผลกระทบ:** เมื่อ backend เปลี่ยน contract จะไม่มีอะไรเตือนเลย — bug ไปโผล่ที่หน้าจอผู้ใช้แทน

## 🚫 9. ใส่ mock data ในโค้ดหลัก

ข้อกำหนดข้อ 7 ห้ามเด็ดขาด — ข้อมูลตัวอย่างต้องอยู่ใน `seed_dev_data` เท่านั้น
(fixture ในโฟลเดอร์ `tests/` ใช้ได้ปกติ)

## 🚫 10. log ข้อมูลอ่อนไหว

```python
# ❌ ผิด
logger.info("ส่ง SMS ถึง %s: %s", patient.phone, message)
```
**✅ ถูก:** `patient.masked_phone` และไม่ log เนื้อหาข้อความ (ดู `providers.py`)

---

# บทที่ 15: คำศัพท์และไปต่อ

## คำศัพท์ที่เจอบ่อยในโค้ดนี้

| คำ | ความหมายในบริบทนี้ |
|---|---|
| **slot** | ช่วงเวลาหนึ่งช่องที่จองได้ เช่น 09:00–09:30 |
| **overbook** | รับคิวเกินความจุจริง — **ห้ามเด็ดขาด** |
| **branch scoping** | การจำกัดข้อมูลให้เห็นเฉพาะสาขาตัวเอง |
| **half-open interval** | `[start, end)` — จบ 10:00 กับเริ่ม 10:00 ไม่ชนกัน |
| **occupying status** | สถานะที่ยังกินเวลาในตาราง (ไม่รวม ยกเลิก/ไม่มา) |
| **race condition** | บั๊กที่เกิดเมื่อสองคนทำงานพร้อมกัน |
| **service layer** | ชั้นที่เก็บกฎธุรกิจ (`services.py`) |
| **mixin** | class ที่ใช้ผสมเพื่อแชร์พฤติกรรม |
| **serializer** | ตัวแปลง JSON ↔ Python object + validate |
| **queryset** | คำสั่ง query ของ Django ที่ยังไม่ถูกรัน (lazy) |
| **broadcast** | ส่งเหตุการณ์ให้ทุกหน้าจอในสาขา |
| **idempotent** | ทำซ้ำกี่ครั้งผลลัพธ์เหมือนเดิม (เช่น งานส่ง SMS) |
| **N+1 query** | บั๊กประสิทธิภาพจากการ query ในลูป — แก้ด้วย `select_related()` |

## เช็คว่าเข้าใจจริงไหม

ตอบได้ทุกข้อ = พร้อมดูแลโปรเจกต์นี้แล้ว:

1. ถ้าเจ้าหน้าที่สองคนกดจองเวลาเดียวกันพร้อมกัน จะเกิดอะไร และโค้ดบรรทัดไหนป้องกัน?
2. ทำไม `Appointment` ที่ `cancelled` ถึงคืน slot ให้คนอื่นได้อัตโนมัติ?
3. JavaScript ในหน้าเว็บอ่าน JWT ได้ไหม เพราะอะไร?
4. ถ้า Redis ล่ม ระบบยังจองคิวได้ไหม แล้วหน้าจอจะเป็นอย่างไร?
5. เจ้าหน้าที่สาขา A จะเห็นคิวสาขา B ได้ไหม โค้ดตรงไหนกัน?
6. `availability/` กับ `available-slots/` ต่างกันอย่างไร?
7. ทำไมบริการที่ไม่ต้องมีแพทย์ถึงไม่อยู่ใน exclusion constraint?
8. ถ้าจะเพิ่ม field ใหม่ในคิว ต้องแก้กี่ไฟล์ อะไรบ้าง?

*(เฉลยกระจายอยู่ในบทที่ 5, 5, 8, 9, 6, 5+docs/05, 6, และ 13 ตามลำดับ)*

## เอกสารต่อไป

| ต้องการ | ไปที่ |
|---|---|
| รายละเอียดรายไฟล์ (ไทย/อังกฤษ) | [`docs/README.md`](docs/README.md) |
| ข้อกำหนดต้นทาง | [`CLAUDE.md`](CLAUDE.md) |
| วิธีติดตั้ง/รัน | [`README.md`](README.md) |
| สัญญา API ฉบับเต็ม | http://localhost:8000/api/docs/ |
| แผนที่ endpoint → ไฟล์ | [`docs/12-api-reference.md`](docs/12-api-reference.md) |

## แหล่งเรียนรู้ภายนอก

| หัวข้อ | ลิงก์ |
|---|---|
| Django ORM | https://docs.djangoproject.com/en/stable/topics/db/queries/ |
| DRF ViewSets & Serializers | https://www.django-rest-framework.org/ |
| Django Channels | https://channels.readthedocs.io/ |
| Celery | https://docs.celeryq.dev/ |
| Next.js App Router | https://nextjs.org/docs/app |
| PostgreSQL exclusion constraint | https://www.postgresql.org/docs/current/ddl-constraints.html |

---

## 📌 สามประโยคที่อยากให้จำไปใช้ต่อ

> **1. กฎธุรกิจอยู่ใน `services.py` เท่านั้น** — view บาง model เก็บ logic ของตัวเอง
>
> **2. ห้ามเชื่อ client** — ทั้งเรื่องเวลาว่าง สาขา และสิทธิ์ ตรวจที่ backend เสมอ
>
> **3. ถ้าเขียนกฎเดียวกันสองที่ สักวันมันจะไม่ตรงกัน** — ดึงขึ้นเป็น service/mixin/constant

**ขอให้สนุกกับการดูแลโปรเจกต์นี้ 🎉**
