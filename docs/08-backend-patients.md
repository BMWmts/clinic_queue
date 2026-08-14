# 08 — `apps/patients/` — ฐานข้อมูลคนไข้ / patient database

**TH:** แอปนี้มีข้อยกเว้นสำคัญข้อเดียวที่ต้องรู้ก่อนอ่านโค้ด: **คนไข้ค้นหาข้ามสาขาได้โดยตั้งใจ**
(ข้อกำหนดข้อ 4.8) เพราะลูกค้าคนเดียวกันเดินเข้าได้หลายสาขา จึงเป็นแอปเดียวที่ **ไม่ใช้**
`BranchScopedQuerySetMixin` แต่การ *สร้าง* คนไข้ใหม่ยังผูกกับสาขาของผู้ใช้เสมอผ่าน `home_clinic`

**EN:** One exception governs this app: **patient lookup is deliberately cross-branch** (spec §4.8),
because the same customer visits multiple branches. It is therefore the only app that does **not**
use `BranchScopedQuerySetMixin` — though *creating* a patient still binds them to the creator's
branch via `home_clinic`.

---

## `patients/models.py`

### `Patient`

**TH:** คนไข้หนึ่งคนใช้ record เดียวทั้งเครือ

**EN:** One record per person across the whole chain.

| Field | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `patient_code` | รหัสอ่านง่าย เช่น `BKK-000123` ระบบสร้างให้ (unique) | Human-readable auto-generated code (unique) |
| `phone` | 🔑 **ตัวจับคู่ข้อมูลเดิม** — มี index เพื่อค้นเร็ว | 🔑 **The matching key** for existing records; indexed |
| `home_clinic` | สาขาที่ลงทะเบียนครั้งแรก (ไม่จำกัดว่าจองได้แค่สาขานี้) | Branch of first registration (not a booking restriction) |
| `date_of_birth`, `gender` | ข้อมูลพื้นฐาน | Basic demographics |
| `is_active` | ปิดใช้งานโดยไม่ลบประวัติ | Deactivate without deleting history |

| Property | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `full_name` | ชื่อ + นามสกุล | Concatenated name |
| 🔒 `masked_phone` | เบอร์แบบปิดบัง `081xxx678` — ใช้ทุกที่ที่ไม่จำเป็นต้องเห็นเบอร์เต็ม (log SMS, admin list) | Masked phone for anywhere the full number isn't needed (SMS logs, admin list) |

**Constraint สำคัญ / Key constraint:**
`UniqueConstraint(fields=["phone", "first_name", "last_name"])`
— เบอร์เดียวกัน + ชื่อเดียวกัน = คนเดียวกัน กันการสร้างซ้ำจากคนละสาขา
*Same phone + same name = the same person, blocking duplicate creation from different branches.*

**🔑 ทำไมไม่ใช้เบอร์โทรอย่างเดียวเป็น unique:** ครอบครัวเดียวกันใช้เบอร์เดียวกันได้ (พ่อ-แม่-ลูก)
**🔑 Why phone alone isn't unique:** family members legitimately share one phone number.

**Index:** `phone` (ค้นเร็ว) และ `(last_name, first_name)` (เรียง/ค้นตามชื่อ)

### `PatientNote`

**TH:** โน้ตสะสมของคนไข้ เช่น "แพ้ยาชา", "ขอหมอคนเดิม" ผูกกับ `appointment` ได้ถ้าเกิดจากการมาครั้งนั้น
(nullable) มี `is_pinned` สำหรับโน้ตสำคัญที่ต้องเห็นทุกครั้ง
`ordering = ["-is_pinned", "-created_at"]` → โน้ตที่ปักหมุดขึ้นก่อนเสมอ

**EN:** Accumulated notes, optionally tied to the visit that produced them. `is_pinned` marks
critical notes; ordering puts pinned notes first.

**🔑 การเชื่อมโยงที่มองไม่เห็น:** `PatientSerializer.pinned_notes` ส่งโน้ตที่ปักหมุด (สูงสุด 5)
ไปกับข้อมูลคนไข้ทุกครั้ง → หน้าค้นหาและหน้า walk-in เตือนเจ้าหน้าที่เรื่องแพ้ยาได้ทันทีโดยไม่ต้องยิง API เพิ่ม
**🔑 A non-obvious link:** pinned notes ride along with every patient payload (max 5), so search and
walk-in screens can warn staff about allergies without an extra request.

---

## `patients/services.py`

### `PatientCodeGenerator`

**TH:** สร้างรหัสรูปแบบ `<รหัสสาขา>-<ลำดับ 6 หลัก>` โดยหาเลขสูงสุดของสาขานั้นแล้ว +1
ลำดับนับ **แยกตามสาขา** เพื่อให้พนักงานอ่านแล้วรู้ทันทีว่าลงทะเบียนที่ไหน

**EN:** Generates `<BRANCH>-<6 digits>` by taking the branch's current maximum and adding one.
Sequences are per-branch so staff can tell at a glance where someone registered.

**🔑 ทำไมไม่ใช้ตารางนับแยก:** จะต้อง lock แถวนั้นทุกครั้งที่ลงทะเบียน กลายเป็นคอขวด
วิธีนี้ใช้ unique constraint + retry แทน ซึ่งแข่งกันน้อยกว่ามาก
**🔑 Why no counter table:** it would need a row lock on every registration — a bottleneck. Here a
unique constraint plus retry does the same job with far less contention.

### `PatientRegistrationService`

| Method | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `create_patient(**fields)` | สร้างคนไข้พร้อมรหัสไม่ซ้ำ — **retry สูงสุด 5 ครั้ง** เมื่อชนกับ transaction อื่น | Create with a unique code, **retrying up to 5 times** on collision |
| `find_existing_by_phone(phone)` | หาคนไข้เดิมจากเบอร์ (ข้ามสาขา) | Find existing patients by phone, across branches |

**🔑 การ retry ต้องอยู่ใน `transaction.atomic()` แต่ละรอบ** ไม่งั้น `IntegrityError` รอบแรก
จะทำให้ transaction ทั้งก้อนใช้ต่อไม่ได้ (เหตุผลเดียวกับ `_save_guarding_overlap` ใน scheduling)
**🔑** Each retry needs its own `atomic()` block, otherwise the first `IntegrityError` poisons the
transaction — the same reason as `_save_guarding_overlap` in scheduling.

**⬅️ ใช้โดย / Used by:** `patients/views.PatientViewSet.perform_create()`,
`queue/services.QueueService._resolve_walk_in_patient()`, `seed_dev_data.py`

### `PatientSearchService`

**TH:** เลือกวิธีค้นตาม **รูปแบบของคำค้น** เพื่อให้ใช้ index ได้และผลลัพธ์ตรงใจ

**EN:** Picks a strategy from the **shape of the query** so indexes are used and results feel right.

| คำค้นหน้าตาแบบ / Query looks like | วิธีค้น (TH) | Strategy (EN) |
|---|---|---|
| ตัวเลขล้วน 3–10 หลัก | `phone__startswith` (ใช้ index ได้) | Phone prefix match (index-friendly) |
| มีขีดกลาง + ตรงรูปแบบรหัส | `patient_code__istartswith` | Patient-code prefix |
| อื่น ๆ | ชื่อ **หรือ** นามสกุล **หรือ** รหัส | Name or surname or code |

**🔑 คำค้นสั้นกว่า 2 ตัวอักษร → คืนผลว่าง** กันการ scan ทั้งตารางเพราะพิมพ์ตัวเดียว
**🔑** Queries under two characters return nothing, preventing a full-table scan from a single keystroke.

**🔑 `limit` เพดาน 100** (view บังคับอีกชั้น) กัน response ใหญ่เกินจำเป็น

---

## `patients/views.py` — `PatientViewSet`

| Action | Endpoint | หน้าที่ (TH) | Role (EN) |
|---|---|---|---|
| list/retrieve/create/update | `/api/patients/` | CRUD คนไข้ + กรอง `?phone=`, `?home_clinic_id=` | Patient CRUD with filters |
| `search` | `GET /api/patients/search/?q=&limit=` | ค้นหาข้ามสาขา | Cross-branch search |
| `notes` | `GET/POST /api/patients/{id}/notes/` | อ่าน/เพิ่มโน้ต | Read/add notes |
| `history` | `GET /api/patients/{id}/history/` | ประวัติการจองทั้งหมด (ใหม่สุดก่อน) + ข้อมูลคนไข้ | Full booking history plus the patient record |

**🔑 `perform_create()` ไม่ใช้ `serializer.save()` ตรง ๆ** แต่เรียกผ่าน `PatientRegistrationService`
เพื่อให้ได้รหัสคนไข้ที่ไม่ซ้ำ แล้วค่อยเซ็ต `serializer.instance` กลับไป
**🔑** Creation delegates to the registration service (for a unique code) and then assigns
`serializer.instance` back.

**🔑 ผู้ใช้ที่ยังไม่ผูกสาขา ลงทะเบียนคนไข้ไม่ได้** → `BranchAccessDeniedError` (403)
เพราะไม่รู้จะตั้ง `home_clinic` เป็นอะไร
**🔑** A user without a clinic cannot register patients — there'd be no `home_clinic` to assign.

**🔑 `history()` import `AppointmentSerializer` แบบ lazy** เพื่อเลี่ยง circular import
(`scheduling` อ้างถึง `patients` ผ่าน FK อยู่แล้ว)
**🔑** The appointment serializer is imported lazily to avoid a circular import.

**🔒 permission = `CanOperateQueue`** — Super Admin/Admin/Staff แก้ได้, แพทย์อ่านได้อย่างเดียว

---

## `patients/serializers.py`

| Serializer | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `PatientSerializer` | ข้อมูลคนไข้ + `full_name`, `home_clinic_name`, `pinned_notes` — `patient_code` และ `home_clinic` เป็น **read-only** 🔒 | Patient payload with derived fields; code and home clinic are **read-only** 🔒 |
| `PatientNoteSerializer` | โน้ต — `patient` และ `created_by` มาจาก backend เสมอ, `validate_note_text()` กันโน้ตว่าง | Notes; owner and author always set server-side, blank text rejected |

**🔑 ทำไม `patient_code` read-only:** ถ้าแก้ได้จะชนกับรหัสของคนอื่นและทำลายความหมายของ prefix สาขา
**🔑 Why the code is read-only:** editing it could collide with another patient and destroy the
branch-prefix meaning.

---

## `patients/urls.py` / `admin.py`

**TH:** router mount ที่ `/api/patients/`; admin แสดง `masked_phone` ในรายการ 🔒 (แต่ยังค้นด้วยเบอร์เต็มได้
เพราะเจ้าหน้าที่ต้องใช้งานจริง)
**EN:** Router at `/api/patients/`; the admin list shows the **masked** phone 🔒 while still allowing
search by the full number, which staff genuinely need.

---

## `patients/migrations/`

| Migration | ทำอะไร (TH) | What it does (EN) |
|---|---|---|
| `0001_initial.py` | สร้างตาราง `Patient` + index + unique constraint | Creates `Patient` with indexes and the unique constraint |
| `0002_initial.py` | เพิ่ม FK ที่ต้องรอแอปอื่น (`created_by` → User, `appointment` → Appointment) | Adds FKs that depend on other apps |
| `0003_patient_search_indexes.py` | 🔑 index สำหรับค้นหาแบบ trigram (**PostgreSQL เท่านั้น** ผ่าน `PostgresOnlySQL`) | 🔑 Trigram search indexes (**PostgreSQL only**, via `PostgresOnlySQL`) |

**🔑 ทำไมต้องแยก `0002`:** Django ต้องสร้างตารางทั้งสองฝั่งก่อนจึงจะผูก FK ข้ามแอปได้
**🔑 Why `0002` is separate:** Django must create both tables before wiring cross-app FKs.
