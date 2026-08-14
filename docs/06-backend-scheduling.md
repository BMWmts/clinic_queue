# 06 — ★ `apps/scheduling/` — หัวใจของระบบ / the core

**TH:** ถ้าอ่านได้แค่แอปเดียว ให้อ่านแอปนี้ ทุกการจองในระบบ — จองล่วงหน้า, walk-in, เลื่อนคิว, seed data —
ผ่านโค้ดในนี้ทั้งหมด **ไม่มีทางลัดใด ๆ**

**EN:** If you read only one app, read this one. Every booking in the system — advance bookings,
walk-ins, reschedules, even seeded data — flows through this code. **There is no bypass.**

---

## `scheduling/models.py`

### `AppointmentStatus` — สถานะคิว / appointment states

| ค่า / Value | ความหมาย (TH) | Meaning (EN) | กินเวลา? / Occupies? |
|---|---|---|---|
| `booked` | จองแล้ว | Booked | ✅ |
| `confirmed` | ยืนยันแล้ว | Confirmed | ✅ |
| `checked_in` | รอพบแพทย์ | Checked in | ✅ |
| `in_progress` | กำลังรักษา | In progress | ✅ |
| `completed` | เสร็จสิ้น | Completed | ✅ |
| `cancelled` | ยกเลิก | Cancelled | ❌ คืนเวลา / frees the slot |
| `no_show` | ไม่มาตามนัด | No-show | ❌ คืนเวลา / frees the slot |

### `OCCUPYING_STATUSES`
**TH:** ทูเพิลที่บอกว่าสถานะไหน "ยังกินเวลาในตาราง" ใช้ทั้งตอนคำนวณ slot ว่างและตอนกันคิวชน
**เป็นแหล่งความจริงเดียว** — ถ้าเพิ่มสถานะใหม่ต้องแก้ที่นี่ **และ** ในไฟล์ migration 0002 (SQL ของ constraint)

**EN:** The single source of truth for "still consumes a slot", used by both availability math and
collision checks. Adding a status means updating this tuple **and** the SQL in migration 0002.

### `ALLOWED_STATUS_TRANSITIONS` — state machine
**TH:** dict ที่ระบุว่าจากสถานะหนึ่งไปสถานะไหนได้บ้าง ป้องกันการข้ามขั้นตอนหน้างาน
เช่น `booked → completed` **ไม่ได้** ต้องผ่าน `checked_in → in_progress` ก่อน
`completed`, `cancelled`, `no_show` เป็นสถานะปลายทาง (ไปไหนต่อไม่ได้)

**EN:** Declares legal transitions, blocking front-desk step-skipping: `booked → completed` is
**illegal**; you must pass through `checked_in → in_progress`. The last three are terminal.

```
booked ──► confirmed ──► checked_in ──► in_progress ──► completed
   │           │              │
   └───────────┴──────────────┴──► cancelled / no_show
```

**🔑** `AppointmentSerializer.allowed_next_statuses` ส่งรายการนี้ไปให้ frontend
หน้าจอจึงแสดง **เฉพาะปุ่มที่กดได้จริง** ไม่ต้องเขียนกฎซ้ำฝั่ง UI
**🔑** The serializer ships this list to the frontend, so the UI renders only legal buttons — the
rule is never duplicated in the UI.

### `AppointmentQuerySet`
**TH:** query ที่ใช้ซ้ำบ่อยรวมไว้ที่เดียว: `.occupying()`, `.overlapping(start, end)`,
`.for_clinic_day(clinic, day_start, day_end)`
`.overlapping()` ใช้เงื่อนไข `scheduled_start__lt=end, scheduled_end__gt=start` = half-open ตรงกับ `TimeInterval`

**EN:** Reusable queries in one place. `.overlapping()` uses `start < end AND end > start`, matching
the half-open convention of `TimeInterval`.

### `Appointment`
**TH:** เอนทิตีกลางของทั้งระบบ `source` มีแค่ `staff_created` / `walk_in` (ไม่มี `online` เพราะไม่มีหน้าจองสาธารณะ)

**EN:** The system's central entity. `source` is only `staff_created` / `walk_in` — there is no
public booking page, hence no `online`.

| Method / property | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `interval` | คืน `TimeInterval` ให้คำนวณร่วมกับตารางแพทย์ได้ | Exposes the appointment as a `TimeInterval` |
| `occupies_slot` | สถานะนี้ยังกินเวลาไหม | Whether this status consumes a slot |
| `overlaps_with(other)` | คิวสองคิวชนกันไหม (นับเฉพาะที่ยังกินเวลา) | Do two appointments clash? |
| `can_transition_to(status)` | เปลี่ยนไปสถานะนี้ได้ไหม | Is this transition legal? |
| ★ `apply_status(status)` | เปลี่ยนสถานะ **พร้อมบันทึก timestamp จริง** (`checked_in_at`, `started_at`, `completed_at`) — ยังไม่ save | Change status **and stamp real timestamps** (not saved yet) |
| `waiting_minutes` | เวลารอจริง = เริ่มรักษา − เช็คอิน (ใช้ในรายงาน) | Real waiting time, used by reports |
| `clean()` | บริการที่ต้องมีแพทย์ต้องระบุแพทย์; แพทย์ต้องอยู่สาขาเดียวกัน 🔒 | Doctor required when the service demands it; doctor must be in the same branch 🔒 |

**🔑 ทำไม `apply_status()` อยู่ใน model:** ทุกทางเข้า (หน้าคิว, แพทย์, งานอัตโนมัติ) จะได้ timestamp ครบเหมือนกัน
ถ้าเขียนใน view จะต้องเขียนซ้ำและลืมบางที่แน่นอน
**🔑 Why `apply_status()` lives on the model:** every entry point (front desk, doctor, automation)
gets identical timestamps. Putting it in a view would guarantee drift.

**Index:** `(clinic, scheduled_start)`, `(doctor, scheduled_start)`, `(status, scheduled_start)`
— ตรงกับ query ที่ใช้จริงในหน้าคิวและรายงาน / matching the queries the queue and reports actually run.

---

## ★★ `scheduling/services.py` — ไฟล์ที่สำคัญที่สุดในโปรเจกต์ / the most important file

แบ่งเป็นสอง class ตามความรับผิดชอบ / Two classes split by responsibility:

| Class | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `SlotAvailabilityService` | **อ่านอย่างเดียว** — "ว่างเมื่อไรบ้าง" | **Read-only** — "when is it free?" |
| `AppointmentBookingService` | **เขียน** — "จอง/เลื่อน/ยกเลิก" พร้อมตรวจกฎ | **Write** — book/reschedule/cancel with rule enforcement |

---

### `SlotAvailabilityService`

**TH:** มีสองโหมดตามชนิดบริการ ตัดสินจาก `service_type.requires_doctor`

**EN:** Two modes chosen by `service_type.requires_doctor`.

#### โหมด 1 — บริการที่ต้องมีแพทย์ / doctor-based

```
free = DoctorAvailabilityService(doctor).free_intervals_on(date)   # ตาราง − บล็อก
     − คิวที่ยังกินเวลาของแพทย์คนนั้นในวันนั้น                        # Appointment.occupying()
slots = generate_slot_starts(free, duration_minutes, clinic.slot_interval_minutes, not_before)
```

#### โหมด 2 — บริการที่ไม่ต้องมีแพทย์ / capacity-based

```
candidates = ทุก slot ในเวลาทำการของสาขา
keep slot ถ้า (จำนวนคิวไม่ใช้แพทย์ที่ซ้อนกับ slot นี้) < clinic.non_doctor_service_capacity
```

**🔑** โหมด 2 นับ **ทุกบริการที่ไม่ใช้แพทย์รวมกัน** เพราะใช้ทรัพยากรหน้างานชุดเดียวกัน (เตียง/เจ้าหน้าที่)
**🔑** Mode 2 counts *all* doctor-less services together — they share the same physical resources.

#### Public API

| Method | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `available_slots(date, include_past=False)` | รายการ slot ที่จองได้จริง เรียงตามเวลา | Bookable slots, ordered |
| ★ `is_slot_available(interval, exclude_appointment_id=None)` | **ด่านสุดท้ายก่อนบันทึกทุกครั้ง** | **The gate before every write** |
| `find_next_available_slot(from_moment, search_days)` | slot ว่างที่เร็วที่สุด (ใช้กับ walk-in) | Earliest free slot (for walk-ins) |

**🔑 `exclude_appointment_id`** จำเป็นตอน **เลื่อนคิว** — ไม่งั้นคิวเดิมจะถูกนับว่าชนกับตัวเอง
**🔑** Needed when rescheduling, otherwise the appointment collides with itself.

**🔑 `_earliest_bookable_moment()`** — วันในอดีตคืนรายการว่าง, วันนี้เริ่มนับจาก "ตอนนี้",
วันอนาคตไม่จำกัด → ระบบไม่เสนอเวลาที่ผ่านไปแล้ว
**🔑** Past dates yield nothing, today starts from "now", future dates are unrestricted — the system
never offers a time that has already passed.

**🔑 `is_slot_available()` ตรวจเวลาเปิด-ปิดสาขาก่อนเสมอ** (`opening_interval_on().contains()`)
ต่อให้ตารางแพทย์กว้างกว่าก็จองนอกเวลาทำการไม่ได้
**🔑** It always checks clinic opening hours first, so a wider doctor schedule still can't book
outside business hours.

**🔑 `MAX_SEARCH_DAYS = 30`** — เพดานกันการวนหา slot ไม่รู้จบเมื่อไม่มีตารางแพทย์เลย
**🔑** A cap preventing an endless search when no schedule exists at all.

---

### ★ `AppointmentBookingService`

#### `book(...)` — จองคิวใหม่ / create a booking

```python
interval = self._build_interval(service_type, scheduled_start)   # end = start + duration
with transaction.atomic():
    self._lock_resource(doctor)                    # 1) ล็อกทรัพยากร / lock the resource
    if not availability.is_slot_available(interval):
        raise SlotUnavailableError(...)            # 2) ★ ด่านห้าม overbook / the anti-overbook gate
    self._save_guarding_overlap(appointment)       # 3) บันทึก + จับ IntegrityError / save, catching DB rejection
```

**TH:** สังเกตว่า **ทั้งสามขั้นอยู่ใน transaction เดียวกัน** — ล็อกก่อนตรวจ ตรวจก่อนเขียน
ถ้าตรวจนอก transaction จะมีช่องว่างให้คนอื่นแทรกจองได้ (race condition)

**EN:** All three steps share one transaction — lock, then check, then write. Checking outside the
transaction would leave a race window.

#### `book_walk_in(...)`
**TH:** หา slot ว่างที่เร็วที่สุดของ **วันนี้เท่านั้น** (`search_days=1`) แล้วเรียก `book()` ต่อ
ถ้าไม่เจอ → `SlotUnavailableError` **ห้ามยัดคิวเกินไม่ว่ากรณีใด** (ข้อกำหนดข้อ 5.2/11)

**EN:** Finds the earliest free slot **today only**, then delegates to `book()`. If none exists it
raises `SlotUnavailableError` — **overbooking is never permitted** (spec §5.2/§11).

#### `reschedule(...)`
**TH:** ปฏิเสธคิวที่ `completed`/`cancelled` แล้วทำเหมือน `book()` แต่ส่ง `exclude_appointment_id`
รองรับการเปลี่ยนแพทย์พร้อมกัน (ล็อกแพทย์ **คนใหม่**)

**EN:** Rejects completed/cancelled appointments, then repeats the `book()` dance with
`exclude_appointment_id`. Supports switching doctors (it locks the **new** doctor).

#### `change_status(...)` / `cancel(...)`
**TH:** เรียก `appointment.apply_status()` (state machine) แล้ว save เฉพาะ field ที่เปลี่ยน
`cancel()` เก็บเหตุผลไว้ด้วย และ **เวลาที่คืนมาจะถูกเสนอให้คิวอื่นทันที** เพราะ `cancelled` ไม่อยู่ใน `OCCUPYING_STATUSES`

**EN:** Delegates to the model's state machine and saves only changed fields. `cancel()` stores a
reason, and the freed time is immediately offered to others because `cancelled` isn't an occupying status.

#### Helper สามตัวที่ต้องเข้าใจ / three helpers worth understanding

| Helper | ทำอะไร (TH) | What it does (EN) |
|---|---|---|
| `_build_interval()` | คำนวณ `end` จาก duration ของบริการเสมอ — **ไม่รับจาก client** | Always derives `end` from service duration — never client input |
| ★ `_lock_resource(doctor)` | `select_for_update()` บนแถวแพทย์ (หรือสาขาถ้าไม่ใช้แพทย์) → การจองทรัพยากรเดียวกันเข้าคิวทีละราย | Row lock on the doctor (or clinic) so concurrent bookings serialise |
| `_save_guarding_overlap()` | ห่อ `transaction.atomic()` **ซ้อนอีกชั้น** เพื่อสร้าง savepoint แล้วจับ `IntegrityError` → แปลงเป็น 409 | Nested `atomic()` creates a savepoint so `IntegrityError` becomes a clean 409 |

**🔑 ทำไมต้อง savepoint ใน `_save_guarding_overlap()`:** ถ้าจับ `IntegrityError` โดยไม่มี savepoint
transaction ทั้งก้อนจะเข้าสถานะ aborted และใช้งานต่อไม่ได้เลย
**🔑 Why the savepoint:** catching `IntegrityError` without one poisons the entire transaction.

**⬅️ ใช้โดย / Used by:** `scheduling/views.py`, `queue/services.py`, `seed_dev_data.py`, tests
**➡️ ใช้:** `doctors/services`, `common/time_intervals`, `common/timezone_utils`, `common/exceptions`

---

## `scheduling/views.py`

| View | Endpoint | หน้าที่ (TH) | Role (EN) |
|---|---|---|---|
| `AppointmentViewSet` | `GET/POST /api/scheduling/appointments/` | รายการ + สร้างคิว (ไม่มี PUT/DELETE — งานหน้างานอยู่ที่ `/api/queue/`) | List + create (no PUT/DELETE; front-desk actions live under `/api/queue/`) |
| `AvailableSlotsView` | `GET /api/scheduling/available-slots/` | ★ เวลาที่จองได้จริง | ★ Genuinely bookable times |

**`resolve_request_clinic(request)` — helper ที่ใช้ทั้ง scheduling และ queue:**
**TH:** ผู้ใช้ทั่วไป = สาขาของตัวเองเสมอ; Super Admin **ต้องระบุ** `?clinic_id=` เพราะไม่ได้สังกัดสาขาใด
*Regular users always get their own branch; Super Admin **must** supply `?clinic_id=`.*

**🔑 การกรองใน `AppointmentViewSet.get_queryset()`:** รองรับ `doctor_id`, `patient_id`, `status`
(คั่นด้วย comma), `date_from`, `date_to` และ **แพทย์เห็นเฉพาะคิวของตัวเอง** (ซ้อนบน branch scoping) 🔒

**🔑 `AvailableSlotsView` แปลงเวลาเป็นโซนของสาขาก่อนส่งออก** — ค่าที่ frontend ได้รับอ่านแล้วตรงกับ
นาฬิกาหน้าร้าน (ยังเป็นช่วงเวลาเดียวกันเป๊ะ แค่เขียนคนละรูป)
**🔑** Slots are converted to the branch's timezone before serialisation, so the values read like the
clock on the wall — the same instant, written differently.

**🔑 `_get_doctor()` บังคับ `clinic=clinic`** 🔒 กันการส่องตารางแพทย์ข้ามสาขา
**🔑** Doctor lookup is constrained to the branch, preventing cross-branch schedule peeking. 🔒

---

## `scheduling/serializers.py`

| Serializer | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `AppointmentSerializer` | แสดงคิว **แนบชื่อ/สี/ระยะเวลาของ relation มาด้วย** เพื่อไม่ให้หน้าจอต้องยิง API ซ้ำ; `read_only_fields = fields` (อ่านอย่างเดียวทั้งหมด) | Read view with denormalised labels/colours so the UI needs no extra calls; entirely read-only |
| `AppointmentCreateSerializer` | รับเฉพาะ `patient`, `service_type`, `doctor`, `scheduled_start`, `note` — **ไม่รับ** `scheduled_end` และ `clinic` 🔒 | Accepts only those five fields — **never** `scheduled_end` or `clinic` 🔒 |
| `AppointmentRescheduleSerializer` | เวลาใหม่ + แพทย์ใหม่ (ถ้าเปลี่ยน) | New time + optional new doctor |
| `AppointmentStatusUpdateSerializer` | สถานะใหม่ + เหตุผลกรณียกเลิก | New status + cancellation reason |
| `AvailableSlotSerializer` | หนึ่ง slot (`start`, `end`) — ใช้ประกาศ schema ให้ OpenAPI | One slot; declares the OpenAPI shape |

**🔑 `validate_scheduled_start()` ปัดวินาที/ไมโครวินาทีทิ้ง** เพื่อให้เทียบกับ slot ที่ระบบเสนอได้ตรง ๆ
**🔑** Seconds/microseconds are zeroed so the value matches the offered slots exactly.

**🔑 `validate()` กันสองกรณี:** บริการที่ต้องมีแพทย์แต่ไม่ส่งแพทย์มา และบริการที่ไม่ใช้แพทย์แต่ส่งแพทย์มา
(กรณีหลังอันตรายกว่า เพราะระบบไม่ได้กันเวลาแพทย์ไว้ให้ แต่ตารางจะดูเหมือนถูกจอง)
**🔑** Both mismatches are rejected; the second is subtler — the doctor's time wouldn't actually be
reserved even though the calendar would look booked.

---

## `scheduling/broadcast.py`

**TH:** ฟังก์ชันเล็ก ๆ ตัวเดียว `broadcast_appointment_event(appointment, event_type)`
แยกเป็นไฟล์ต่างหากเพื่อให้ทั้ง `scheduling` และ `queue` เรียกตัวเดียวกันได้ **โดยไม่เกิด import วนกัน**
(import `AppointmentSerializer` แบบ lazy ข้างในฟังก์ชัน)

**EN:** A single small function so both apps share one broadcaster **without a circular import**
(`AppointmentSerializer` is imported lazily inside the function).

**🔑** payload ที่ส่งผ่าน WebSocket ใช้ `AppointmentSerializer` ตัวเดียวกับ REST API
→ frontend เอาไปแทนที่ในรายการได้ทันทีโดยไม่ต้องแปลงรูป
**🔑** The WS payload uses the same serializer as REST, so the frontend can swap it into its list directly.

---

## `scheduling/migrations/0002_appointment_overlap_exclusion.py`

**TH:** ตาข่ายรองสุดท้ายระดับฐานข้อมูล — exclusion constraint ของ PostgreSQL

```sql
EXCLUDE USING gist (
    doctor_id WITH =,
    tstzrange(scheduled_start, scheduled_end, '[)') WITH &&
) WHERE (doctor_id IS NOT NULL AND status IN ('booked','confirmed','checked_in','in_progress','completed'))
```

อ่านว่า: *"คิวของแพทย์คนเดียวกัน ที่ช่วงเวลาซ้อนทับกัน และยังกินเวลาอยู่ — ห้ามมีเกินหนึ่ง"*

**EN:** The database-level safety net: *"for the same doctor, no two occupying appointments may have
overlapping time ranges."*

**🔑 `'[)'`** = half-open ตรงกับ `TimeInterval` ในโค้ด Python เป๊ะ ๆ / matches the Python convention exactly.
**🔑 ทำไมมีทั้งที่แอปตรวจแล้ว:** ถ้าอนาคตมีโค้ดใหม่เขียนคิวลงตารางโดยข้าม service layer
ฐานข้อมูลจะปฏิเสธเอง — เป็นการป้องกันความผิดพลาดของนักพัฒนา ไม่ใช่ของผู้ใช้
**🔑 Why duplicate the check:** future code that bypasses the service layer still cannot corrupt the
schedule — it protects against developer error, not user error.
**🔑 บริการที่ไม่ใช้แพทย์ไม่อยู่ใน constraint นี้** เพราะเป็นกฎเชิงจำนวน (capacity) ซึ่ง exclusion constraint
แสดงไม่ได้ จึงตรวจที่ชั้นแอปพลิเคชันแทน
**🔑** Doctor-less services are excluded because theirs is a *counting* rule an exclusion constraint
cannot express; it is enforced in the application layer.

---

## `scheduling/tests/` — 38 เทสต์ที่คุ้มค่าที่สุดในโปรเจกต์

### `factories.py`
**TH:** `ClinicTestDataMixin` สร้างสาขา/แพทย์/บริการ/คนไข้ให้ TestCase ใช้ซ้ำ + `next_monday()`
(วันจันทร์ **ในอนาคตเสมอ** เพื่อไม่ให้กฎ "ห้ามจองย้อนหลัง" มารบกวน) + `bangkok_datetime()`
**🔑 นี่คือ test fixture ไม่ใช่ mock data** — อยู่ใต้ `tests/` เท่านั้น ตามข้อกำหนดข้อ 7

**EN:** Shared test data builders, `next_monday()` (always in the future so the no-past-booking rule
doesn't interfere) and `bangkok_datetime()`. **These are test fixtures, not mock data** — confined to
`tests/`, as spec §7 requires.

### `test_slot_availability.py` (18 เทสต์)
**TH:** ครอบคลุมทั้งสองโหมด: slot อยู่ในตารางแพทย์, เว้นระยะตาม `slot_interval_minutes`,
วันที่ไม่มีตาราง = ไม่มี slot, เวลาทำการของสาขาตัดตารางแพทย์, TimeBlock ตัด slot ที่ทับ,
บล็อกแบบ recurring มีผลกับสัปดาห์ถัดไป, คิวที่จองแล้วหายไปจากรายการ,
**คิวที่ยกเลิก/ไม่มา คืน slot กลับมา**, บริการยาวลงท้ายวันไม่ได้, วันในอดีตไม่มี slot,
`is_slot_available()` สอดคล้องกับ `available_slots()`, แพทย์ที่ปิดใช้งานไม่มี slot,
และโหมด capacity (เต็มแล้วหาย / เพิ่มเพดานแล้วกลับมา)

**EN:** Both modes covered: clamping, spacing, empty days, time blocks, recurrence, booked slots
disappearing, **cancelled/no-show returning slots**, long services not fitting at day's end, past
dates, consistency between the two public methods, inactive doctors, and capacity behaviour.

### `test_booking_service.py` (20 เทสต์)
**TH:** สามกลุ่ม
- `AppointmentBookingTests` — end time คำนวณจาก duration, จองซ้ำเวลาเดิมถูกปฏิเสธ, จองซ้อนบางส่วนถูกปฏิเสธ,
  **จองต่อกันพอดี (back-to-back) ทำได้** (พิสูจน์ half-open), จองนอกตาราง/ในช่วงบล็อก/ล้นเวลาปิดถูกปฏิเสธ,
  ยกเลิกแล้วคนอื่นจองต่อได้, แพทย์คนละคนจองเวลาเดียวกันได้
- `WalkInBookingTests` — walk-in ได้ slot ที่เร็วที่สุด, เลื่อนไป slot ถัดไปถ้าอันแรกถูกจอง,
  **ถูกปฏิเสธเมื่อวันนั้นเต็ม**
- `RescheduleAndStatusTests` — เลื่อนสำเร็จ/ชนแล้วถูกปฏิเสธ, เลื่อนเวลานิดเดียวไม่นับว่าชนกับตัวเอง,
  เปลี่ยนแพทย์ได้, สถานะบันทึก timestamp ครบ, ข้ามขั้นตอนถูกปฏิเสธ, คิวที่เสร็จแล้วเลื่อนไม่ได้

**EN:** Three groups covering booking rules, walk-in behaviour (including rejection when full), and
reschedule/status transitions.

**🔑 เทสต์ที่สำคัญที่สุดสองตัว / the two most valuable tests:**
`test_back_to_back_booking_is_allowed` (ยืนยัน half-open) และ
`test_walk_in_is_rejected_when_the_day_is_full` (ยืนยันว่าห้าม overbook จริง)
