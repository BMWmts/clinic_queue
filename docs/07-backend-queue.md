# 07 — `apps/queue/` — หน้าจอคิวหน้างาน + realtime

**TH:** แอปนี้คือ "หน้าเคาน์เตอร์" — ดูคิววันนี้, รับ walk-in, เปลี่ยนสถานะ, เลื่อนคิว
**สำคัญ:** มันไม่ได้เขียนกฎการจองใหม่เลย แต่ยืมทั้งหมดมาจาก `apps.scheduling.services`
ถ้าเจอโค้ดที่นี่พยายามสร้าง `Appointment` ตรง ๆ ถือว่าผิด

**EN:** This app is "the front desk" — today's queue, walk-ins, status changes, reschedules.
**Crucially** it writes no booking rules of its own; it borrows all of them from
`apps.scheduling.services`. Any code here creating an `Appointment` directly is a bug.

**🔑 หมายเหตุชื่อแอป:** `apps.py` ตั้ง `label = "clinic_queue"` เพราะ `queue` เป็นชื่อโมดูลมาตรฐานของ Python
**🔑 App label note:** it's `clinic_queue` because `queue` is a Python stdlib module name.

---

## `queue/services.py` — `QueueService`

**TH:** ห่องานที่หน้าเคาน์เตอร์ใช้บ่อยไว้ในที่เดียว โดยมี `AppointmentBookingService` เป็นสมาชิกภายใน

**EN:** Wraps the common front-desk operations, holding an `AppointmentBookingService` internally.

### ฝั่งอ่าน / Read side

| Method | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `queue_for_date(date, doctor_id)` | คิวของวันนั้นเรียงตามเวลา **รวมคิวที่ยกเลิก/ไม่มาด้วย** เพื่อให้เจ้าหน้าที่เห็นภาพครบ | The day's queue in time order, **including cancelled/no-show** so staff see the full picture |
| `queue_summary(date, doctor_id)` | นับจำนวนแยกตามสถานะด้วย aggregate **ครั้งเดียว** | Per-status counts in a **single** aggregate query |

**🔑 ทำไมนับด้วย aggregate ไม่ใช่ Python:** ไม่ต้องโหลดทุกแถวมานับ — สาขาที่มีคิววันละหลายร้อยจะรู้สึกได้
**🔑 Why aggregate instead of Python:** it avoids loading every row — noticeable on busy branches.

**🔑 การหา "วันนี้"** ใช้ `local_date_of(timezone.now(), clinic.timezone)` ไม่ใช่ `date.today()`
เพื่อให้ตรงกับวันตามปฏิทินของสาขา
**🔑** "Today" is resolved in the branch's timezone, not the server's.

### ฝั่งเขียน / Write side

| Method | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `add_walk_in(...)` | หา/สร้างคนไข้ → เรียก `booking.book_walk_in()` → broadcast | Resolve patient → delegate to booking → broadcast |
| `change_status(...)` | ยกเลิกใช้ `booking.cancel()` (เก็บเหตุผล), อื่น ๆ ใช้ `booking.change_status()` → broadcast | Cancel keeps a reason; others go through the state machine → broadcast |
| `reschedule(...)` | เรียก `booking.reschedule()` → broadcast | Delegate → broadcast |
| `_resolve_walk_in_patient(...)` | หาคนไข้เดิมจาก **เบอร์โทร + ชื่อ** ก่อน ถ้าไม่มีจึงสร้างใหม่ | Find by **phone + first name** before creating |

**🔑 ทำไมต้องหาคนไข้เดิมก่อน:** ลูกค้าประจำที่เดินเข้ามาแบบไม่ได้นัดจะได้ไม่มีประวัติซ้ำหลาย record
(ตรงกับ unique constraint `(phone, first_name, last_name)` ใน `Patient`)
**🔑 Why find-first:** returning customers who walk in shouldn't spawn duplicate records — matching
the `(phone, first_name, last_name)` unique constraint on `Patient`.

**🔑 ทุก method ฝั่งเขียนจบด้วย `broadcast_appointment_event()`** → หน้าจออื่นในสาขาเห็นทันที
**🔑** Every write ends with a broadcast, so other screens in the branch update immediately.

**➡️ ใช้:** `scheduling/services.AppointmentBookingService`, `patients/services.PatientRegistrationService`,
`scheduling/broadcast.py`, `common/timezone_utils`

---

## `queue/views.py`

| View | Endpoint | หน้าที่ (TH) | Role (EN) |
|---|---|---|---|
| `TodayQueueView` | `GET /api/queue/today/` | คิวของวัน + สรุปจำนวน + timezone ของสาขา | The day's queue, summary counts, branch timezone |
| `WalkInView` | `POST /api/queue/walk-in/` | รับคิว walk-in (409 ถ้าไม่มี slot) | Add a walk-in (409 when full) |
| `AppointmentStatusUpdateView` | `PATCH /api/queue/appointments/{id}/status/` | เปลี่ยนสถานะตาม state machine | Change status via the state machine |
| `AppointmentRescheduleView` | `PATCH /api/queue/appointments/{id}/reschedule/` | เลื่อน/สลับเวลา (หน้าจอลากวางเรียกอันนี้) | Reschedule (drag-and-drop calls this) |

**Mixin สองตัว / Two mixins:**

- `QueueServiceMixin.get_queue_service(request)` — สร้าง `QueueService` ของสาขาที่ผู้ใช้ทำงานด้วย
  (ใช้ `resolve_request_clinic` ที่ยืมมาจาก `scheduling/views.py`)
- 🔒 `AppointmentQueueActionView.get_appointment()` — ดึงคิวใบเดียว **พร้อมกรองสาขา**
  แล้วเรียก `check_object_permissions()` รวมไว้ที่เดียวเพื่อไม่ให้ view ไหนลืมตรวจ

*The first builds the service for the caller's branch; the second fetches a single appointment
**with branch filtering** and object-level permission checks, centralised so no view forgets.*

**🔑 แพทย์ที่ login เข้ามา `TodayQueueView` จะบังคับ `doctor_id` เป็นตัวเอง** 🔒
ต่อให้ส่ง `?doctor_id=` ของคนอื่นมาก็ถูกทับ
**🔑** For a logged-in doctor, `doctor_id` is forced to their own profile — a supplied value is overridden. 🔒

---

## `queue/permissions.py` — 🔒 `CanUpdateAppointmentStatus`

**TH:** permission พิเศษของการเปลี่ยนสถานะ มีสองระดับ
- `has_permission` — เจ้าหน้าที่/ผู้จัดการ/Super Admin **หรือ** แพทย์ ผ่านได้
- `has_object_permission` — เจ้าหน้าที่ขึ้นไปแตะได้ทุกคิวในสาขา ส่วน **แพทย์แตะได้เฉพาะคิวที่ตัวเองเป็นผู้ตรวจ**

**EN:** A two-level permission: queue operators (or any doctor) pass the view check, but at object
level a doctor may only touch appointments where they are the attending doctor.

**🔑 ทำไมต้องแยกจาก `CanOperateQueue`:** แพทย์ต้องอัปเดตสถานะคนไข้ที่กำลังตรวจได้
แต่ต้องไม่ไปแตะคิวของแพทย์ท่านอื่น — `CanOperateQueue` ให้แพทย์อ่านอย่างเดียว จึงไม่พอ
**🔑 Why a separate class:** doctors must update their own patients' status without touching other
doctors' queues; `CanOperateQueue` makes doctors read-only, which is too strict here.

---

## `queue/serializers.py`

| Serializer | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `NewWalkInPatientSerializer` | ข้อมูลคนไข้ใหม่หน้าเคาน์เตอร์ (เบอร์โทรบังคับรูปแบบ `^0\d{8,9}$`) | New-patient fields with Thai phone validation |
| `WalkInCreateSerializer` | รับคิว walk-in — **บังคับเลือกอย่างใดอย่างหนึ่ง** ระหว่าง `patient` (คนเดิม) กับ `new_patient` (คนใหม่) | Walk-in payload — **exactly one** of `patient` / `new_patient` |
| `QueueSummarySerializer` | สรุปจำนวนคิวแยกตามสถานะ (การ์ดด้านบนหน้าจอ) | Per-status counts for the summary cards |

**🔑 `validate()` ใช้ `has_existing == has_new` เพื่อจับทั้งสองกรณีผิดพร้อมกัน**
(ส่งมาทั้งคู่ = ผิด, ไม่ส่งเลย = ผิด)
**🔑** The equality check catches both errors at once: supplying both, or neither.

**🔑 ตรวจ `requires_doctor` ซ้ำที่นี่อีกรอบ** เพื่อให้ผู้ใช้ได้ error ราย field ก่อนเข้าไปถึง service layer
**🔑** `requires_doctor` is re-validated here so users get a field-level error before the service layer.

---

## `queue/realtime.py` — `QueueBroadcaster` + `QueueEvent`

**TH:** ตัวกลางส่งเหตุการณ์ผ่าน Django Channels แต่ละสาขามี group ของตัวเอง
`queue_updates_{clinic_id}` เพื่อไม่ให้ข้อมูลคิวข้ามสาขาไปถึงหน้าจอที่ไม่มีสิทธิ์เห็น 🔒

**EN:** The Channels broadcaster. Each branch has its own group `queue_updates_{clinic_id}` so queue
data never reaches screens that shouldn't see it. 🔒

**ชนิดเหตุการณ์ / Event types:** `appointment_created`, `appointment_updated`,
`appointment_status_changed`, `appointment_rescheduled`

**🔑 สองการตัดสินใจสำคัญ / two important decisions:**

1. **`transaction.on_commit()`** — ส่ง event **หลัง** transaction commit เท่านั้น
   ถ้าส่งก่อน หน้าจออาจ fetch กลับมาแล้วยังไม่เจอคิวที่เพิ่งสร้าง
   *Events fire only after commit; firing earlier would let a screen refetch before the row is visible.*
2. **จับ `Exception` ทั้งหมดแล้ว log** — realtime เป็นฟีเจอร์เสริม Redis ล่มต้องไม่ทำให้ **การจองคิวล้มเหลว**
   frontend ยัง fallback ไป polling ได้อยู่แล้ว
   *All exceptions are swallowed and logged — realtime is optional; a Redis outage must never fail a
   booking, and the frontend already falls back to polling.*

---

## `queue/consumers.py` — `QueueConsumer`

**TH:** WebSocket consumer ของหน้าจอคิว รับการเชื่อมต่อที่ `ws://<host>/ws/queue/<clinic_id>/?token=...`

**EN:** The queue WebSocket consumer, accepting connections at `ws://<host>/ws/queue/<clinic_id>/?token=…`

| ขั้นตอน / Step | พฤติกรรม (TH) | Behaviour (EN) |
|---|---|---|
| `connect()` | ไม่ auth → ปิดด้วยรหัส **4401** 🔒 | Unauthenticated → close **4401** 🔒 |
| `connect()` | สาขาไม่ตรง (และไม่ใช่ Super Admin) → ปิดด้วยรหัส **4403** 🔒 | Wrong branch → close **4403** 🔒 |
| `connect()` | ผ่าน → เข้า group + ส่ง `{"event":"connected"}` | Otherwise join the group and greet |
| `receive_json()` | รองรับเฉพาะ `ping` → ตอบ `pong` | Only `ping` is accepted |
| `queue_event()` | รับจาก channel layer แล้วส่งต่อให้เบราว์เซอร์ | Relay channel-layer messages to the browser |

**🔑 อ่านอย่างเดียวโดยเจตนา** — ไม่รับคำสั่งแก้ไขข้อมูลทาง WebSocket ทุกการเขียนต้องผ่าน REST API
ที่มี permission + validation ครบ
**🔑 Deliberately read-only** — no mutations over WebSocket; every write goes through the REST API
with its full permission and validation stack.

---

## `queue/routing.py`

**TH:** `websocket_urlpatterns` = `ws/queue/<int:clinic_id>/` → `QueueConsumer`
ถูก import โดย `config/asgi.py`
**EN:** Maps the WS path to the consumer; imported by `config/asgi.py`.

---

## `queue/urls.py`

**TH:** สี่ path ตรง ๆ (ไม่ใช้ router เพราะเป็น action ไม่ใช่ resource CRUD)
**EN:** Four explicit paths — no router, because these are actions rather than resource CRUD.

---

## `queue/tests/test_queue_api.py` (10 เทสต์)

**TH:** เทสต์ระดับ API (`APITestCase`) สองกลุ่ม

- `QueueApiTests` — `/today/` คืนคิว + summary, เปลี่ยนสถานะตาม state machine,
  ข้ามขั้นตอนได้ **409**, เลื่อนไปเวลาที่มีคนจองแล้วได้ **409**,
  🔒 **แพทย์แก้คิวของแพทย์ท่านอื่นไม่ได้** แต่แก้ของตัวเองได้
- `WalkInApiTests` — walk-in ลงทะเบียนคนไข้ใหม่แล้วสร้างคิว, **ใช้คนไข้เดิมซ้ำเมื่อเบอร์โทรตรงกัน**,
  ถูกปฏิเสธเมื่อไม่มี slot เหลือ, และบังคับเลือกแพทย์สำหรับบริการที่ต้องมีแพทย์

**EN:** API-level tests in two groups: queue reads/status/reschedule (including 🔒 doctor isolation)
and walk-in behaviour (new patient, patient reuse, rejection when full, doctor requirement).
