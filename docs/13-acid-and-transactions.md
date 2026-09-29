# 13 — ACID & Transactions — ระบบรักษาความถูกต้องของข้อมูลอย่างไร / How the system keeps data correct

**TH:** เอกสารนี้สรุปว่าระบบจองคิวทำตามหลัก ACID (Atomicity, Consistency, Isolation, Durability)
ไว้ที่จุดไหนบ้าง และใช้กลไกอะไร

**EN:** This page maps each ACID property to the exact code that enforces it.

> สถานะ ณ วันที่ 2026-09-29 — ถ้าแก้โค้ดส่วน transaction ให้อัปเดตเอกสารนี้ด้วย

---

## สรุปภาพรวม / Summary

| หลัก / Property | สถานะ / Status | กลไกหลัก / Main mechanism |
|---|---|---|
| **A**tomicity | ✅ ครบในจุดสำคัญ | `transaction.atomic()` + savepoint |
| **C**onsistency | ✅ สองชั้น (app + DB) | `CheckConstraint`, `UniqueConstraint`, exclusion constraint, state machine |
| **I**solation | ✅ ครบทั้งจอง/เลื่อน/เปลี่ยนสถานะ/ยกเลิก | `select_for_update()` ล็อกแถวคิว + แถวทรัพยากร |
| **D**urability | ✅ | PostgreSQL 16 (WAL) + Docker named volume |

> ⚠️ **สำคัญ:** การรับประกันทั้งหมดนี้ใช้ได้เต็มรูปแบบ **บน PostgreSQL เท่านั้น**
> ถ้าไม่ได้ตั้ง `DATABASE_URL` ระบบจะ fallback ไปใช้ SQLite ([settings.py](../backend/config/settings.py))
> ซึ่งจะ **ไม่มี** exclusion constraint (migration ถูกข้ามด้วย `PostgresOnlySQL`) และ `select_for_update()` ไม่มีผล
> — ดูหัวข้อ [ข้อจำกัดของ SQLite](#ข้อจำกัดของ-sqlite--sqlite-caveats)

---

## A — Atomicity (ทำครบทั้งหมด หรือไม่ทำเลย)

**TH:** งานที่ประกอบด้วยหลายขั้นตอนต้องสำเร็จพร้อมกันทั้งก้อน ถ้าขั้นใดล้มเหลว ทุกอย่างต้อง rollback

| งาน / Operation | ไฟล์ / File | รายละเอียด |
|---|---|---|
| จองคิว `book()` | [scheduling/services.py](../backend/apps/scheduling/services.py) | ล็อกทรัพยากร → เช็ค slot ว่าง → บันทึก อยู่ใน `transaction.atomic()` เดียว |
| เลื่อนคิว `reschedule()` | [scheduling/services.py](../backend/apps/scheduling/services.py) | ล็อกแถวคิว → ตรวจสถานะ → ล็อกแพทย์ → เช็คชน (ยกเว้นตัวเอง) → บันทึก ใน transaction เดียว |
| เปลี่ยนสถานะ `change_status()` / ยกเลิก `cancel()` | [scheduling/services.py](../backend/apps/scheduling/services.py) | ล็อกแถวคิว → ตรวจ state machine กับค่าล่าสุด → บันทึก |
| บันทึกคิว `_save_guarding_overlap()` | [scheduling/services.py](../backend/apps/scheduling/services.py) | `atomic()` ซ้อนอีกชั้น = **savepoint** เพื่อให้จับ `IntegrityError` แล้ว transaction หลักยังใช้ต่อได้ |
| รับแพทย์ใหม่ `create_doctor()` | [doctors/services.py](../backend/apps/doctors/services.py) | สร้าง `User` + `Doctor` ใน transaction เดียว — ไม่มีทางเหลือบัญชีค้างที่ไม่มีโปรไฟล์แพทย์ |
| ลงทะเบียนคนไข้ `create_patient()` | [patients/services.py](../backend/apps/patients/services.py) | แต่ละรอบของการ retry รหัสคนไข้อยู่ใน `atomic()` ของตัวเอง |
| สร้าง SMS log `create_reminder_log()` | [notifications/services.py](../backend/apps/notifications/services.py) | `atomic()` + จับ `IntegrityError` เพื่อกันส่งซ้ำ |
| Seed data | [seed_dev_data.py](../backend/apps/common/management/commands/seed_dev_data.py) | `@transaction.atomic` — seed ล้มกลางทางจะไม่เหลือข้อมูลครึ่ง ๆ กลาง ๆ |

### ทำไมต้องมี savepoint? / Why the nested `atomic()`?

```python
try:
    with transaction.atomic():          # ← savepoint
        appointment.full_clean()
        appointment.save()
except IntegrityError as exc:           # exclusion constraint ปฏิเสธ
    raise BookingConflictError(...)     # → HTTP 409 แทน 500
```

**TH:** บน PostgreSQL เมื่อคำสั่งหนึ่งใน transaction error ทั้ง transaction จะอยู่ในสถานะ "aborted"
ใช้ต่อไม่ได้จนกว่าจะ rollback — savepoint ทำให้ rollback เฉพาะส่วนที่พัง แล้วแปลง error ให้ผู้ใช้เข้าใจได้

**EN:** A failed statement poisons the whole PostgreSQL transaction; the savepoint limits the
rollback so we can translate the error into a clean 409.

### ผลข้างเคียงภายนอก / Side effects outside the DB

**TH:** การ broadcast คิวผ่าน WebSocket ใช้ `transaction.on_commit()` ([queue/realtime.py](../backend/apps/queue/realtime.py))
→ หน้าจอหน้างานจะได้รับ event **เฉพาะเมื่อ commit สำเร็จแล้ว** ไม่มีทางเห็นคิว "ผี" ที่ถูก rollback ไป

**EN:** Realtime events fire only after commit, so clients never see rolled-back appointments.

---

## C — Consistency (ข้อมูลถูกต้องตามกฎเสมอ)

**TH:** ระบบบังคับกฎทางธุรกิจสองชั้น — ชั้น application (อ่านง่าย, error message ดี) และชั้นฐานข้อมูล
(ตาข่ายสุดท้าย ต่อให้มีโค้ดในอนาคตเขียนข้าม service layer ก็หลุดไม่ได้)

### Constraint ระดับฐานข้อมูล / Database constraints

| Constraint | Model | กฎ |
|---|---|---|
| `appointment_end_after_start` | `Appointment` | `scheduled_end > scheduled_start` |
| **`appointment_no_overlap_per_doctor`** | `Appointment` | ★ แพทย์คนเดียวกันห้ามมีคิวเวลาซ้อนกัน (exclusion constraint) |
| `doctor_schedule_end_after_start` | `DoctorSchedule` | `end_time > start_time` |
| `doctor_schedule_unique_start_per_day` | `DoctorSchedule` | แพทย์ + วัน + เวลาเริ่ม ห้ามซ้ำ |
| `time_block_end_after_start` | `TimeBlock` | `end_datetime > start_datetime` |
| `clinic_closing_time_after_opening_time` | `Clinic` | เวลาปิด > เวลาเปิด |
| `user_non_super_admin_requires_clinic` | `User` | ทุก role ยกเว้น Super Admin ต้องสังกัดสาขา |
| `patient_unique_phone_and_name` | `Patient` | เบอร์ + ชื่อ + สกุล ห้ามซ้ำ |
| `patient_code` unique | `Patient` | รหัสคนไข้ไม่ซ้ำ |
| `sms_unique_reminder_per_appointment` | `SMSLog` | 1 นัด ส่ง reminder ได้ครั้งเดียว (ยกเว้นครั้งที่ failed) |

### ★ Exclusion constraint — กันคิวชนที่ระดับ DB

ไฟล์: [scheduling/migrations/0002_appointment_overlap_exclusion.py](../backend/apps/scheduling/migrations/0002_appointment_overlap_exclusion.py)

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE scheduling_appointment
    ADD CONSTRAINT appointment_no_overlap_per_doctor
    EXCLUDE USING gist (
        doctor_id WITH =,
        tstzrange(scheduled_start, scheduled_end, '[)') WITH &&
    )
    WHERE (doctor_id IS NOT NULL AND status IN
           ('booked','confirmed','checked_in','in_progress','completed'));
```

**TH อ่านว่า:** "ห้ามมีสองแถวที่ `doctor_id` เท่ากัน **และ** ช่วงเวลาทับกัน (`&&`)"
- `'[)'` = รวมเวลาเริ่ม ไม่รวมเวลาจบ → คิว 10:00–10:30 กับ 10:30–11:00 **ไม่ถือว่าชน**
- นับเฉพาะสถานะที่ยังกินเวลา — คิวที่ `cancelled`/`no_show` คืนเวลาให้คนอื่นจองได้
- บริการที่ไม่ใช้แพทย์ (`doctor_id IS NULL`) ถูกคุมด้วยเพดานจำนวนเคสของสาขาที่ชั้น application แทน
  (เป็นกฎเชิงจำนวน constraint แบบนี้เขียนไม่ได้)

> ถ้าเพิ่มสถานะใหม่ใน `OCCUPYING_STATUSES` ต้องแก้ SQL ของ constraint นี้ด้วย (ผ่าน migration ใหม่)

### กฎระดับ application / Application-level rules

| กฎ | ที่อยู่ |
|---|---|
| ห้าม overbook (ต้องอยู่ในตารางออกตรวจ, ไม่ทับ `TimeBlock`, ไม่ทับคิวอื่น, ไม่เกิน capacity) | `SlotAvailabilityService.is_slot_available()` |
| `scheduled_end` คำนวณจาก `duration_minutes` เสมอ ไม่รับจาก client | `AppointmentBookingService._build_interval()` |
| สถานะเปลี่ยนได้ตามเส้นทางที่กำหนดเท่านั้น (state machine) | `ALLOWED_STATUS_TRANSITIONS` + `Appointment.apply_status()` |
| คิวที่เสร็จ/ยกเลิกแล้วเลื่อนไม่ได้ | `AppointmentBookingService.reschedule()` |
| validate ทุก field ก่อน save | `full_clean()` ใน service ทุกตัว |

---

## I — Isolation (การทำงานพร้อมกันไม่รบกวนกัน)

### ✅ ตอนจอง / เลื่อนคิว — Pessimistic locking

**TH:** ปัญหาคลาสสิก: พนักงาน 2 คนกดจองคิวเวลาเดียวกันพร้อมกัน ทั้งคู่เช็คแล้ว "ว่าง" ทั้งคู่ → คิวชน
ระบบแก้ด้วยการล็อกแถวของ **ทรัพยากร** ที่ถูกจองก่อนเช็คเวลาว่าง:

```python
def _lock_resource(self, doctor):
    if doctor is not None:
        Doctor.objects.select_for_update().get(pk=doctor.pk)      # SELECT ... FOR UPDATE
    else:
        Clinic.objects.select_for_update().get(pk=self.clinic.pk) # บริการไม่ใช้แพทย์ → ล็อกทั้งสาขา
```

```
 พนักงาน A                          พนักงาน B
 ─────────                          ─────────
 BEGIN                              BEGIN
 LOCK doctor #5  ✔                  LOCK doctor #5  ⏳ (รอ)
 เช็ค 10:00 → ว่าง
 INSERT คิว 10:00
 COMMIT → ปล่อยล็อก                  ✔ ได้ล็อก
                                    เช็ค 10:00 → ไม่ว่างแล้ว
                                    raise SlotUnavailableError → 409
                                    ROLLBACK
```

**ทำไมล็อกแถว Doctor แทนแถว Appointment?** เพราะคิวใหม่ยังไม่มีแถวให้ล็อก (phantom row)
การล็อก "เจ้าของตาราง" ทำให้ทุกการจองของแพทย์คนนั้นต้องต่อคิวทีละราย ส่วนแพทย์คนอื่นยังจองขนานกันได้

**Walk-in:** `book_walk_in()` หา slot ว่างนอก transaction (เร็ว, ไม่ถือล็อกนาน) แล้วส่งต่อให้ `book()`
ซึ่งเช็คซ้ำภายใต้ล็อก — ถ้า slot หายไประหว่างนั้นจะได้ 409 ไม่ใช่คิวชน

**ชั้นที่สอง:** ถ้ามีโค้ดในอนาคตลืมล็อก exclusion constraint ก็ยังปฏิเสธคิวชนที่ระดับ DB

**ระดับ isolation:** ใช้ค่า default ของ PostgreSQL คือ `READ COMMITTED` — เพียงพอ เพราะความถูกต้อง
มาจาก row lock + constraint ไม่ได้พึ่ง isolation level

### ✅ รหัสคนไข้ / SMS — Optimistic (constraint + retry)

- `PatientCodeGenerator` หาเลขล่าสุด +1 โดยไม่ล็อก ถ้าชนกับ transaction อื่น unique constraint จะปฏิเสธ
  แล้ว service retry ด้วยเลขใหม่ (เลือกแบบนี้เพื่อไม่ต้องมีตารางนับที่เป็นคอขวด)
- SMS reminder สองงานรันพร้อมกัน → unique constraint ให้สร้าง log ได้แค่ตัวเดียว อีกตัวได้ `None` และข้ามไป

### ✅ ตอนเปลี่ยนสถานะ / ยกเลิก / เลื่อนคิว — ล็อกแถวคิว

**TH:** ปัญหาเดิม (lost update): view โหลดคิวไว้ก่อนเข้า transaction ถ้าพนักงานสองคนแก้คิวเดียวกันพร้อมกัน
ทั้งคู่จะตรวจ state machine กับสถานะเก่า แล้วคน save ทีหลังชนะ เช่น คิวที่ถูกยกเลิกแล้วถูกเขียนทับเป็น `checked_in`

ตอนนี้ `change_status()`, `cancel()` และ `reschedule()` ล็อกแถวคิวก่อนตรวจทุกครั้งผ่าน `_lock_appointment()`:

```python
@staticmethod
def _lock_appointment(appointment: Appointment) -> None:
    Appointment.objects.select_for_update().only("pk").get(pk=appointment.pk)  # รอจนได้ล็อก
    appointment.refresh_from_db()  # โหลดค่าที่ commit ล่าสุดกลับเข้า instance เดิม
```

```
 พนักงาน A (ยกเลิก)                  พนักงาน B (เช็คอิน, instance เก่า)
 BEGIN + LOCK คิว #42  ✔
                                     BEGIN + LOCK คิว #42  ⏳ (รอ)
 booked → cancelled, COMMIT
                                     ✔ ได้ล็อก → refresh → status = cancelled
                                     cancelled → checked_in ❌ InvalidStatusTransitionError
```

- refresh เข้า **instance เดิม** (ไม่สร้างตัวใหม่) เพื่อให้ view ใช้ instance นั้นสร้าง response ต่อได้
- `reschedule()` ตรวจ "เสร็จ/ยกเลิกแล้วเลื่อนไม่ได้" **หลัง** ล็อก และเลือกแพทย์จากค่าล่าสุด
- **ลำดับการล็อกคงที่: คิว → แพทย์/สาขา** (`book()` ล็อกแค่แพทย์, `change_status()` ล็อกแค่คิว)
  ไม่มีเส้นทางไหนล็อกแพทย์ก่อนคิว จึงไม่เกิด deadlock

### เทสต์ที่ยืนยัน / Tests

ไฟล์: [scheduling/tests/test_concurrent_updates.py](../backend/apps/scheduling/tests/test_concurrent_updates.py)

| ชุดเทสต์ | รันบน | ตรวจอะไร |
|---|---|---|
| `StaleInstanceTests` | sqlite + PostgreSQL | ส่ง instance เก่าเข้า service → ต้องถูกตรวจกับสถานะล่าสุดใน DB |
| `RowLockConcurrencyTests` | PostgreSQL เท่านั้น | สองเธรดแย่งแถวเดียวกันจริง: เธรดรองต้อง **รอ** ล็อก แล้วถูกปฏิเสธหลังเธรดหลักยกเลิกคิว |

เทสต์ชุดนี้ถูกยืนยันแล้วว่า **ล้มกับโค้ดก่อนแก้** (5 จาก 6 เคส) และผ่านทั้งหมดหลังแก้

---

## D — Durability (commit แล้วต้องไม่หาย)

| ชั้น | กลไก |
|---|---|
| ฐานข้อมูล | PostgreSQL 16 — Write-Ahead Log (WAL), `fsync`/`synchronous_commit` เปิดตาม default |
| Container | ข้อมูลอยู่ใน named volume `postgres_data` ([docker-compose.yml](../docker-compose.yml)) → ลบ/สร้าง container ใหม่ข้อมูลยังอยู่ |
| Application | ไม่มี cache ที่ถือข้อมูลหลักแทน DB — ทุก endpoint อ่าน/เขียน PostgreSQL ตรง (ตาม CLAUDE.md หมวด 7) |
| Audit trail | `created_by`, `created_at`, `updated_at` บนตารางสำคัญ + `SMSLog` ย้อนตรวจได้ |

**ข้อควรระวังสำหรับ production:** durability ระดับ "เครื่องพัง/ดิสก์เสีย" ต้องมี backup แยก
(เช่น `pg_dump` ตามรอบ หรือ WAL archiving) — ยังไม่มีใน docker-compose ของ dev

---

## ข้อจำกัดของ SQLite / SQLite caveats

**TH:** SQLite ใช้ได้เฉพาะรัน unit test ของ logic ล้วน ๆ เท่านั้น

| กลไก | PostgreSQL | SQLite |
|---|---|---|
| `transaction.atomic()` | ✅ | ✅ |
| `CheckConstraint` / `UniqueConstraint` | ✅ | ✅ |
| Exclusion constraint กันคิวชน | ✅ | ❌ migration ถูกข้าม (`PostgresOnlySQL`) |
| `select_for_update()` | ✅ ล็อกระดับแถว | ❌ ไม่มีผล (SQLite ล็อกทั้งไฟล์ตอนเขียนแทน) |
| ทดสอบ race condition ได้จริง | ✅ | ❌ |

→ **เทสต์เรื่อง concurrency / คิวชนพร้อมกัน ต้องรันบน PostgreSQL (`docker compose`) เสมอ**

---

## เช็คลิสต์เมื่อเขียนโค้ดใหม่ / Checklist for new code

- [ ] งานที่เขียนหลายแถว/หลายตาราง → ห่อด้วย `transaction.atomic()` ใน service class
- [ ] อ่าน → ตรวจ → เขียน แถวที่คนอื่นอาจแก้พร้อมกัน → `select_for_update()` ภายใน transaction
- [ ] ล็อกหลายแถว → ตามลำดับ "คิว → แพทย์/สาขา" เสมอ (กัน deadlock)
- [ ] สร้าง/แก้คิว → ผ่าน `AppointmentBookingService` เท่านั้น ห้าม `Appointment.objects.create()` ตรง
- [ ] จับ `IntegrityError` → ต้องอยู่ใน `atomic()` ชั้นในเสมอ (savepoint)
- [ ] ส่ง WebSocket / Celery task / SMS → ใช้ `transaction.on_commit()` หรือ `delay_on_commit()`
- [ ] กฎใหม่ที่ DB บังคับได้ → เพิ่มเป็น constraint + migration ด้วย ไม่ใช่เช็คแค่ใน Python
