# 05 — `apps/doctors/` + `apps/services/` — แพทย์, ตาราง, บริการ

---

# ส่วนที่ 1 — `apps/doctors/`

**TH:** แอปนี้เก็บ "ข้อมูลตั้งต้น" ของการคำนวณเวลาว่าง — ตารางออกตรวจคือฝั่ง **บวก** (เวลาที่มี)
และ TimeBlock คือฝั่ง **ลบ** (เวลาที่ถูกตัดออก)

**EN:** This app holds the *inputs* of availability math — schedules are the **positive** side (time
that exists) and time blocks the **negative** side (time removed).

---

## `doctors/models.py`

### `Weekday`
**TH:** `IntegerChoices` จันทร์=0 … อาทิตย์=6 — ใช้เลขเดียวกับ `date.weekday()` ของ Python
เพื่อให้เทียบตรง ๆ ได้โดยไม่ต้องแปลง
**EN:** Monday=0 … Sunday=6, matching Python's `date.weekday()` so comparison needs no conversion.

**🔑 ระวังสับสน:** รายงานใช้ `ExtractIsoWeekDay` (จันทร์=**1**) คนละฐานกัน — ดู `docs/09`
**🔑 Careful:** reports use `ExtractIsoWeekDay` (Monday=**1**) — a different base. See `docs/09`.

### `Doctor`
**TH:** โปรไฟล์แพทย์ผูก 1-1 กับบัญชี `User` ที่ role=doctor มี `display_name`, `specialties`,
`color` (ใช้ระบายสีในปฏิทิน) และ `is_active`
`clean()` บังคับว่า **สาขาของแพทย์ต้องตรงกับสาขาของบัญชีผู้ใช้** ไม่งั้น branch scoping สองฝั่งจะขัดกัน
(login เห็นสาขาหนึ่ง แต่คิวไปโผล่อีกสาขา)

**EN:** A doctor profile 1-1 with a `User` whose role is doctor. `clean()` enforces that the doctor's
clinic matches the user's clinic, otherwise the two scoping paths disagree (you log into one branch
but your queue appears in another).

**🔑 `is_active=False` → ไม่มี slot เลย** (เช็คที่ `DoctorAvailabilityService.working_intervals_on()`)
**🔑** An inactive doctor yields zero slots.

### `DoctorSchedule`
**TH:** หนึ่งแถว = หนึ่งช่วงเวลาของหนึ่งวันในสัปดาห์ (แบบ recurring รายสัปดาห์)
เช่น แพทย์ที่ออกตรวจเช้า-บ่ายวันจันทร์ = 2 แถว (09:00–12:00 และ 13:00–17:00)

**EN:** One row = one weekly recurring window. A doctor working Monday morning and afternoon has two rows.

| กฎ / Rule | เหตุผล (TH) | Why (EN) |
|---|---|---|
| CheckConstraint `end_time > start_time` | ป้องกันช่วงเวลาติดลบระดับ DB | Prevents negative windows at the DB level |
| UniqueConstraint `(doctor, day_of_week, start_time)` | กันแถวซ้ำเป๊ะ | Blocks exact duplicates |
| `_overlaps_existing_schedule()` | กันตารางของแพทย์คนเดียวกันในวันเดียวกันทับกัน — ถ้าทับ เวลาว่างจะถูกนับซ้ำ | Prevents same-day overlaps that would double-count free time |
| `save()` / `clean()` เติม `clinic` จาก doctor | สาขาต้องตามแพทย์เสมอ | Clinic always follows the doctor |

**Method:** `interval_on(date, tz)` → แปลงตารางประจำสัปดาห์เป็น `TimeInterval` ของวันจริง
*Converts the weekly pattern into a concrete `TimeInterval` for a given date.*

### `TimeBlock` + `TimeBlockReason` + `RecurrenceType`
**TH:** ช่วงเวลาที่แพทย์ไม่รับคิว (พักเที่ยง/ประชุม/เคสด่วน/ลา)
รองรับการซ้ำ (`daily`/`weekly`) โดย **เก็บแถวเดียว** แล้ว "แผ่" ออกตอนคำนวณด้วย `occurrence_on()`
— ไม่งั้นพักเที่ยงทุกวันจะกลายเป็นหลายพันแถวในฐานข้อมูล

**EN:** Windows where the doctor takes no queue. Recurrence (`daily`/`weekly`) is stored as **one row**
and expanded at compute time by `occurrence_on()` — otherwise a daily lunch break would balloon into
thousands of rows.

**★ `occurrence_on(target_date, tz)` — เมธอดที่ต้องเข้าใจให้ดี / the method to understand:**

| กรณี / Case | พฤติกรรม (TH) | Behaviour (EN) |
|---|---|---|
| ไม่ซ้ำ / non-recurring | ตัดเฉพาะส่วนที่ตกในวันนั้น (รองรับการลายาวข้ามวัน) | Clamps to that day (supports multi-day leave) |
| `weekly` | ตรงกับวันในสัปดาห์เดียวกันเท่านั้น | Only on the same weekday |
| `daily` | ทุกวันตั้งแต่วันเริ่ม | Every day from the start date |
| เกิน `recurrence_end_date` | คืน `None` | Returns `None` |

**🔑 ยึด "เวลานาฬิกาท้องถิ่น"** — พักเที่ยง 12:00–13:00 ต้องเป็นเที่ยงวันไทยเสมอ ไม่เลื่อนตาม UTC
**🔑** Anchored to *local wall-clock* time — a 12:00–13:00 lunch stays at Thai noon regardless of UTC.

**🔑 `clean()` กันบล็อก recurring ที่ยาวเกิน 1 วัน** — ไม่งั้นแต่ละ occurrence จะซ้อนกันเอง
**🔑** Recurring blocks longer than a day are rejected, since occurrences would overlap each other.

---

## ★ `doctors/services.py` — `DoctorAvailabilityService`

**TH:** ชั้น business logic ของฝั่งแพทย์ ตอบคำถามเดียว: *"แพทย์คนนี้ว่างช่วงไหนบ้างในวันนั้น (ยังไม่นับคิว)"*

**EN:** The doctor-side business layer answering one question: *"when is this doctor free that day,
before considering booked appointments?"*

| Method | คืนอะไร (TH) | Returns (EN) |
|---|---|---|
| `working_intervals_on(date)` | เวลาออกตรวจ **ตัดให้อยู่ในเวลาเปิด-ปิดของสาขาแล้ว** (แพทย์ไม่ active → ว่างเปล่า) | Schedule clamped to clinic opening hours (inactive doctor → empty) |
| `blocked_intervals_on(date)` | ช่วงที่ถูกบล็อกของวันนั้น (แผ่ recurring ออกแล้ว) | Blocked windows for that day, recurrence expanded |
| `free_intervals_on(date)` | `working − blocked` | `working − blocked` |
| `_relevant_time_block_filter(date)` | Q object ดึงเฉพาะ TimeBlock ที่ *อาจ* เกี่ยวข้อง | Q object narrowing candidate blocks |

**🔑 กลยุทธ์ "กรองกว้างไว้ก่อน"** — `_relevant_time_block_filter()` ดึงแบบหลวม ๆ ในฐานข้อมูล
แล้วให้ `occurrence_on()` ตัดช่วงจริงใน Python เพราะกฎ recurrence ซับซ้อนเกินกว่าจะเขียนเป็น SQL ที่อ่านรู้เรื่อง
แต่ก็ไม่โหลดทั้งตารางมาทิ้ง
**🔑 "Filter wide, refine in Python"** — the DB query is deliberately loose and `occurrence_on()` does
the exact cut, because recurrence rules are too intricate for readable SQL — yet it never loads the
whole table.

**⬅️ ใช้โดย / Used by:** `scheduling/services.SlotAvailabilityService._doctor_free_time()`,
`doctors/views.DoctorViewSet.availability()`
**➡️ ใช้:** `common/time_intervals`, `common/timezone_utils`, `doctors/models`

---

## `doctors/views.py`

| ViewSet / action | Endpoint | หน้าที่ (TH) | Role (EN) |
|---|---|---|---|
| `DoctorViewSet` | `/api/doctors/` | CRUD แพทย์ + กรอง `?is_active=` | Doctor CRUD + `?is_active=` filter |
| `DoctorViewSet.availability` | `GET /api/doctors/{id}/availability/?date=` | เวลาทำงาน + ช่วงที่ถูกบล็อกของวันนั้น (หน้าปฏิทินใช้วาดพื้นหลัง) | Working + blocked windows; the calendar paints its background from this |
| `DoctorScheduleViewSet` | `/api/doctors/schedules/` | CRUD ตารางประจำสัปดาห์ + กรอง `?doctor_id=` | Weekly schedule CRUD |
| `TimeBlockViewSet` | `/api/doctors/time-blocks/` | CRUD ช่วงบล็อก + กรอง `?doctor_id=&date_from=&date_to=` | Time block CRUD with date filters |

**Helper ที่ใช้ซ้ำทั้งโปรเจกต์ / Project-wide helper:**
`parse_date_param(raw, field)` — แปลง `YYYY-MM-DD` (ค่าเริ่มต้น = วันนี้) และโยน ValidationError ถ้ารูปแบบผิด
ถูก import ไปใช้ใน `scheduling/views.py`, `queue/views.py`, `reports/views.py`
*Parses `YYYY-MM-DD` (defaulting to today); reused by scheduling, queue and reports views.*

**`DoctorDerivedClinicMixin`** — 🔒 สำหรับข้อมูลที่ "สาขาต้องตามแพทย์" ตรวจก่อนเสมอว่าแพทย์ที่ระบุ
อยู่ในขอบเขตที่ผู้ใช้จัดการได้ กันการสร้างตารางให้แพทย์ของสาขาอื่น
*🔒 For records whose clinic follows the doctor: verifies the doctor is in the user's scope, blocking
schedule creation for another branch's doctor.*

**➡️ ใช้:** `common/mixins`, `common/permissions.IsBranchManagerOrReadOnly`, `doctors/services`

**🔑 ความต่างที่สำคัญ / Important distinction:**
`/api/doctors/{id}/availability/` = ตารางดิบ (ยัง **ไม่หัก** คิวที่จองแล้ว) ใช้วาดพื้นหลังปฏิทิน
`/api/scheduling/available-slots/` = เวลาที่ **จองได้จริง** (หักคิวแล้ว) ใช้ตอนจอง — **ห้ามสลับกัน**
*The former is raw schedule (background painting); the latter is genuinely bookable time. Never swap them.*

---

## `doctors/serializers.py`

**TH:** สามตัว: `DoctorSerializer` (มี `validate_user` บังคับว่าบัญชีที่เลือกต้อง role=doctor),
`DoctorScheduleSerializer`, `TimeBlockSerializer` ทั้งสามใช้ `ModelCleanValidationMixin`
เพื่อให้กฎใน `Model.clean()` (เช่น ตารางห้ามทับกัน) มีผลกับ API ด้วย
`clinic` เป็น read-only — ระบบเติมให้จาก doctor เสมอ 🔒

**EN:** Three serializers; all use `ModelCleanValidationMixin` so model-level rules (e.g. no
overlapping schedules) apply through the API. `clinic` is read-only and always derived server-side. 🔒

---

## `doctors/urls.py`

**TH:** mount ที่ `/api/doctors/` — ลงทะเบียน `schedules/` และ `time-blocks/` **ก่อน** แล้วค่อยลง
route ว่าง `""` ของ `DoctorViewSet` ท้ายสุด ถ้าสลับลำดับ `/api/doctors/schedules/` จะถูกตีความเป็น
"แพทย์ id=schedules" แล้วพัง

**EN:** Order matters: `schedules/` and `time-blocks/` are registered **before** the empty `""` route,
otherwise `/api/doctors/schedules/` would be parsed as "doctor with id=schedules".

---

## `doctors/admin.py` / `migrations/0001_initial.py`

**TH:** admin ของสามโมเดลพร้อม filter ตามสาขา; migration สร้างสามตารางพร้อม index และ constraint
**EN:** Admin for all three models with branch filters; the migration creates the tables, indexes and constraints.

---

# ส่วนที่ 2 — `apps/services/`

## `services/models.py` — `ServiceType`

**TH:** แคตตาล็อกบริการกลาง **ใช้ร่วมกันทุกสาขา** (จงใจไม่ผูก FK กับ clinic) เพื่อให้คนไข้ที่ย้ายสาขา
ได้รับบริการชื่อเดียวกัน และรายงานข้ามสาขาเทียบกันได้

**EN:** A central catalog **shared by all branches** (deliberately no clinic FK) so patients moving
between branches see the same service names and cross-branch reports are comparable.

| Field | ผลต่อระบบ (TH) | Effect (EN) |
|---|---|---|
| ★ `duration_minutes` | กำหนดความยาวคิว — ระบบคำนวณ `scheduled_end` จากค่านี้เสมอ | Defines appointment length; `scheduled_end` is always derived from it |
| `requires_doctor` | สลับโหมดคำนวณ slot: ตามตารางแพทย์ vs ตามเพดานของสาขา | Switches slot mode: doctor schedule vs branch capacity |
| `price` | ใช้รวมรายได้ในรายงาน (นับเฉพาะคิวที่เสร็จสิ้น) | Feeds revenue reporting (completed only) |
| `is_active` | ปิดบริการโดยไม่ลบประวัติเดิม | Retire a service without deleting history |

**🔑 `duration_minutes` ไม่รับจาก client เด็ดขาด** — `AppointmentCreateSerializer` ไม่มี field `scheduled_end`
ป้องกันคิวที่ยาว/สั้นกว่าบริการจริง ซึ่งจะทำให้ตารางเหลื่อม
**🔑** The client never supplies duration or `scheduled_end`, preventing mismatched appointment
lengths that would skew the whole schedule.

**⬅️ ใช้โดย / Used by:** `Appointment.service_type`, `scheduling/services.py`, `queue/services.py`,
`reports/services.py` (breakdown + revenue)

---

## `services/views.py` — `ServiceTypeViewSet`

**TH:** CRUD บริการ 🔒 เจ้าหน้าที่/แพทย์ **อ่านได้** (ต้องใช้ตอนจอง) แต่แก้ไขได้เฉพาะผู้จัดการขึ้นไป
รองรับกรอง `?is_active=`, `?category=`, `?q=` (ค้นชื่อ)
**ไม่ใช้ branch scoping** เพราะเป็นแคตตาล็อกกลาง

**EN:** Service CRUD. 🔒 Staff and doctors can read (needed for booking); only managers may write.
Supports `?is_active=`, `?category=`, `?q=`. No branch scoping — it's a shared catalog.

**🔑** หน้าจอจองเรียกด้วย `?is_active=true` เสมอ เพื่อไม่ให้เลือกบริการที่ปิดใช้งานแล้ว
**🔑** Booking screens always pass `?is_active=true` so retired services can't be selected.

---

## `services/serializers.py` / `urls.py` / `admin.py` / `migrations/`

**TH:** serializer ตรงไปตรงมา (ทุก field ยกเว้น `id` แก้ได้), router mount ที่ `/api/services/`,
admin มี filter ตาม category/requires_doctor, migration สร้างตารางพร้อม validator ของ duration (5–600 นาที)
**EN:** A straightforward serializer, a router at `/api/services/`, an admin with category filters,
and a migration creating the table with the 5–600 minute duration validators.
