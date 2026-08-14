# 03 — `backend/apps/common/` — โครงสร้างพื้นฐานร่วม / shared infrastructure

**TH:** แอปนี้ **ไม่พึ่งพาแอปอื่นเลย** ทุกแอปพึ่งพามัน ถ้าเห็น logic ซ้ำในสองแอป มันควรย้ายมาที่นี่
**EN:** This app **depends on nothing**; everything depends on it. Logic duplicated across two apps
belongs here.

---

## ★ `time_intervals.py` — คณิตศาสตร์ของช่วงเวลา / interval math

**TH:** Pure Python ล้วน ไม่แตะ Django หรือฐานข้อมูลเลย จึงทดสอบได้เร็วมากและนำไปใช้ซ้ำได้ทุกที่
ประกอบด้วยสามส่วน:

| ส่วน | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `TimeInterval` | ช่วงเวลาหนึ่งช่วงแบบ half-open `[start, end)` มี `overlaps_with()`, `contains()`, `subtract()`, `clamped_to()` | One half-open interval with overlap/contains/subtract/clamp operations |
| `IntervalSet` | กลุ่มช่วงเวลาที่ไม่ทับกันและเรียงแล้ว (รวมช่วงที่ต่อกันอัตโนมัติ) แทน "เวลาว่างของแพทย์ทั้งวัน" | A merged, sorted set of non-overlapping intervals = "a doctor's free time for the day" |
| `generate_slot_starts()` | ซอยเวลาว่างเป็น slot ทีละ `step_minutes` และรับเฉพาะที่ยาวครบ `duration_minutes` | Slices free time into bookable slots every `step_minutes`, keeping only full-length ones |

**EN:** Pure Python — no Django, no database. That makes it fast to test and reusable everywhere.

**⬅️ ใครใช้ / Used by:** `doctors/services.py`, `doctors/models.py`, `scheduling/services.py`,
`scheduling/models.py` (`Appointment.interval`), `clinics/models.py` (`opening_interval_on`)
**➡️ ใช้:** ไม่มี / nothing (stdlib only)

**🔑 half-open `[start, end)`** — คิวที่จบ 10:00 กับคิวที่เริ่ม 10:00 **ไม่ชนกัน** เป็นข้อตกลงที่ทั้งระบบยึด
รวมถึง exclusion constraint ใน PostgreSQL (`tstzrange(..., '[)')`)
**🔑** An appointment ending at 10:00 does **not** clash with one starting at 10:00 — the same
convention as the PostgreSQL exclusion constraint (`tstzrange(..., '[)')`).

**🔑 `subtract()` คืนได้ 0/1/2 ช่วง** — 2 ช่วงเกิดเมื่อถูกเจาะตรงกลาง เช่น พักเที่ยงคั่นเวลาทำงาน
**🔑** `subtract()` returns 0, 1, or 2 intervals — two when punched in the middle, e.g. a lunch break.

---

## `timezone_utils.py` — แปลงเวลา / timezone helpers

**TH:** ฐานข้อมูลเก็บ UTC เสมอ แต่ตารางแพทย์และเวลาเปิด-ปิดเป็น "เวลานาฬิกาท้องถิ่น"
ไฟล์นี้เป็นสะพานเชื่อมสองโลกนั้น: `combine_local()` (วัน+เวลา → aware datetime),
`local_day_bounds()` (ขอบเขต 00:00–24:00 ของวันตามเวลาท้องถิ่น), `to_local()`, `local_date_of()`

**EN:** The DB always stores UTC, while doctor schedules and opening hours are *local wall-clock*
times. This module bridges the two: `combine_local()`, `local_day_bounds()`, `to_local()`, `local_date_of()`.

**⬅️ ใช้โดย / Used by:** `clinics/models.py`, `doctors/models.py`, `doctors/services.py`,
`scheduling/services.py`, `queue/services.py`, `reports/services.py`, `notifications/services.py`

**🔑** ถ้าคำนวณ "วันนี้" ด้วย UTC ตรง ๆ คิวช่วงหัวค่ำ/เช้ามืดจะตกวันผิด — ต้องผ่าน `local_day_bounds()` เสมอ
**🔑** Computing "today" straight from UTC misfiles evening/early-morning appointments — always
go through `local_day_bounds()`.

---

## `permissions.py` — 🔒 สิทธิ์ตาม role / role-based permissions

**TH:** ประกาศ role ที่อนุญาตไว้ใน class attribute เดียวแล้วสืบทอด ไม่ต้องเขียน `if user.role == ...` ซ้ำ

**EN:** Allowed roles are declared as a single class attribute and inherited — no repeated
`if user.role == ...` checks.

| Class | ใครผ่าน (TH) | Who passes (EN) |
|---|---|---|
| `RoleBasedPermission` | base: `allowed_roles` ทำได้ทุก method, `read_only_roles` ทำได้เฉพาะ GET/HEAD | Base: full access vs read-only role sets |
| `IsSuperAdmin` | Super Admin เท่านั้น | Super Admin only |
| `IsBranchManager` | Super Admin + Admin | Super Admin + branch manager |
| `IsBranchManagerOrReadOnly` | ผู้จัดการแก้ได้, Staff/Doctor อ่านได้ | Managers write; staff/doctors read |
| `CanOperateQueue` | Super Admin/Admin/Staff แก้ได้, Doctor อ่านได้ | Queue operators write; doctors read |
| `IsClinicMember` | ทุก role ที่ login แล้ว | Any authenticated role |

**⬅️ ใช้โดย / Used by:** `accounts/views.py`, `doctors/views.py`, `services/views.py`,
`scheduling/views.py`, `queue/views.py`, `patients/views.py`, `reports/views.py`, `notifications/views.py`

**🔑** permission ตอบแค่ "role นี้ทำ action นี้ได้ไหม" ส่วน "เห็นข้อมูลสาขาไหน" เป็นหน้าที่ของ mixin ข้างล่าง
**🔑** Permissions answer *"may this role do this action?"*; *"which branch's data?"* is the mixin's job.

---

## ★ `mixins.py` — 🔒 `BranchScopedQuerySetMixin` (multi-branch)

**TH:** กฎเหล็กของระบบอยู่ที่ไฟล์นี้ไฟล์เดียว: Admin/Staff/Doctor เห็นเฉพาะสาขาตัวเอง
มีเพียง Super Admin ที่ข้ามสาขาได้ (และเลือกเจาะสาขาด้วย `?clinic_id=` ได้)
มีสาม method:
- `get_queryset()` — เติม `.filter(clinic_id=...)` อัตโนมัติ (ผู้ใช้ที่ไม่มีสาขา → `queryset.none()`)
- `resolve_clinic_for_write()` — หา clinic ที่จะใช้ตอนเขียน และปฏิเสธถ้าพยายามข้ามสาขา
- `perform_create()` — เติม `clinic` และ `created_by` ให้อัตโนมัติ **โดยไม่เชื่อค่าที่ client ส่งมา**

**EN:** The system's hard rule lives in this one file: admins/staff/doctors see only their own
branch; only Super Admin crosses branches (optionally narrowing with `?clinic_id=`). Three methods:
auto-filtering `get_queryset()`, write-side `resolve_clinic_for_write()`, and `perform_create()`
that fills `clinic` and `created_by` server-side, **never trusting client input**.

**⬅️ ใช้โดย / Used by:** `accounts.UserViewSet`, `doctors.{Doctor,DoctorSchedule,TimeBlock}ViewSet`,
`scheduling.AppointmentViewSet`, `notifications.SMSLogViewSet`
**➡️ ใช้:** `common/exceptions.BranchAccessDeniedError`, `clinics.Clinic` (ผ่าน `apps.get_model` เพื่อเลี่ยง import วน)

**🔑 `clinic_lookup`** ปรับได้เมื่อ model ไม่มี FK ชื่อ `clinic` ตรง ๆ (เช่น `doctor__clinic`)
**🔑** Override `clinic_lookup` when a model reaches Clinic through another path (e.g. `doctor__clinic`).

**🔑 ทำไมไม่ใช้กับ `patients`:** คนไข้ค้นข้ามสาขาได้โดยตั้งใจ (ข้อกำหนดข้อ 4.8) ดู `docs/08`
**🔑 Why patients skip it:** cross-branch patient lookup is intentional (spec §4.8) — see `docs/08`.

---

## `exceptions.py` — ข้อผิดพลาดเชิงธุรกิจ / domain errors

**TH:** service raise exception เหล่านี้แทนการคืน error code ดิบ ๆ แล้ว `api_exception_handler`
(ตั้งไว้ใน `settings.REST_FRAMEWORK`) แปลงเป็น response รูปแบบเดียวกันทั้งระบบ:
`{"error": {"code": "...", "message": "...", "details": {...}}}`

**EN:** Services raise these instead of returning raw error codes; `api_exception_handler`
(registered in `settings.REST_FRAMEWORK`) renders one consistent shape system-wide.

| Exception | code | HTTP | เมื่อไร (TH) | When (EN) |
|---|---|---|---|---|
| `DomainError` | `domain_error` | 400 | base class | Base class |
| `SlotUnavailableError` | `slot_unavailable` | **409** | ไม่มีเวลาว่างจริง | No genuinely free slot |
| `BookingConflictError` | `booking_conflict` | **409** | ชนกับคิวที่มีอยู่ / DB ปฏิเสธ | Clashes with an existing appointment / DB rejected |
| `InvalidStatusTransitionError` | `invalid_status_transition` | 409 | เปลี่ยนสถานะข้ามขั้น | Illegal status jump |
| `BranchAccessDeniedError` | `branch_access_denied` | **403** | แตะข้อมูลข้ามสาขา 🔒 | Cross-branch access attempt 🔒 |

**⬅️ ใช้โดย / Used by:** ทุก `services.py`, `mixins.py`, และ frontend (`lib/api/http.ts` อ่าน `code` นี้)
**🔑** `ApiError.isSlotConflict` ฝั่ง frontend เช็ค `slot_unavailable`/`booking_conflict` — เปลี่ยนชื่อ code
ต้องแก้สองที่ / renaming a code requires updating the frontend too.

---

## `models.py` — abstract base models

**TH:** `TimeStampedModel` (`created_at`, `updated_at`) และ `AuditableModel` (เพิ่ม `created_by`)
เป็นฐานของทุกตารางสำคัญ ตอบข้อกำหนด audit trail — ใช้ `SET_NULL` เพื่อไม่ให้ประวัติคิวหายเมื่อลบผู้ใช้

**EN:** `TimeStampedModel` and `AuditableModel` back every important table, satisfying the audit-trail
requirement. `created_by` uses `SET_NULL` so appointment history survives user deletion.

**⬅️ สืบทอดโดย / Inherited by:** `Clinic`, `Doctor`, `DoctorSchedule`, `TimeBlock`, `ServiceType`,
`SMSLog` (TimeStamped); `Appointment`, `Patient`, `PatientNote` (Auditable)

---

## `serializers.py` — `ModelCleanValidationMixin`

**TH:** DRF **ไม่** เรียก `Model.clean()` ให้อัตโนมัติ กฎที่เขียนไว้ใกล้ข้อมูล (เช่น "เวลาเลิกต้องหลังเวลาเริ่ม",
"ตารางออกตรวจห้ามทับกัน") จึงถูกข้ามเวลาเรียกผ่าน API mixin นี้ดึงกฎเดิมกลับมาใช้ โดยประกอบค่าที่ส่งเข้ามา
ลง instance ชั่วคราว เรียก `clean()` แล้ว **คืนค่าเดิม** เพื่อไม่ให้ค่าที่ยังไม่บันทึกค้างอยู่

**EN:** DRF does **not** call `Model.clean()`, so model-level rules would be skipped by the API.
This mixin re-applies them: it temporarily writes incoming values onto the instance, calls `clean()`,
then **restores** the originals so unsaved values don't linger.

**⬅️ ใช้โดย / Used by:** `DoctorSerializer`, `DoctorScheduleSerializer`, `TimeBlockSerializer`

---

## `pagination.py` — `DefaultPagination`

**TH:** page-number pagination, ค่าเริ่มต้น 25 ต่อหน้า, ปรับได้ด้วย `?page_size=` สูงสุด 200
frontend รับผลลัพธ์เป็น `Paginated<T>` (`count/next/previous/results`)

**EN:** Page-number pagination: 25 per page by default, `?page_size=` up to 200. The frontend
consumes it as `Paginated<T>`.

**🔑** `ServiceApiClient.list()` ส่ง `page_size: 200` เพื่อโหลดแคตตาล็อกบริการครบในครั้งเดียว
**🔑** `ServiceApiClient.list()` passes `page_size: 200` to fetch the whole catalog at once.

---

## `roles.py` — บทบาทผู้ใช้ / user roles

**TH:** `UserRole` (super_admin/admin/staff/doctor) และกลุ่มสำเร็จรูป `CROSS_BRANCH_ROLES`,
`MANAGEMENT_ROLES`, `QUEUE_OPERATION_ROLES` อยู่ใน `common` เพราะทั้ง `accounts` (นิยาม User)
และ permission/mixin ส่วนกลางต้องใช้ค่าเดียวกัน — ป้องกันค่าไม่ตรงกันระหว่างแอป

**EN:** `UserRole` plus the ready-made role sets. It lives in `common` because both `accounts`
(which defines User) and the shared permissions/mixins need the same values — preventing drift.

**⬅️ ใช้โดย / Used by:** `accounts/models.py`, `accounts/serializers.py`, `common/permissions.py`,
`queue/permissions.py`, `seed_dev_data.py`, test factories

---

## `websocket_auth.py` — 🔒 JWT สำหรับ WebSocket

**TH:** เบราว์เซอร์แนบ `Authorization` header ใน WS handshake ไม่ได้ จึงรับ access token ผ่าน `?token=`
middleware นี้แปลง token เป็น `scope["user"]` (หรือ `AnonymousUser` ถ้าไม่ถูกต้อง) โดย **ไม่ log ค่า token**

**EN:** Browsers can't send an `Authorization` header during a WS handshake, so the token arrives as
`?token=`. This middleware resolves it into `scope["user"]` (or `AnonymousUser`) and **never logs the token**.

**⬅️ ใช้โดย / Used by:** `config/asgi.py`
**➡️ คู่กับ / Pairs with:** `frontend/app/api/auth/ws-token/route.ts` (ผู้ออก token ระยะสั้น)

**🔑** ตัดสินใจโดยเจตนา: token ใบนี้อายุสั้น (นาที) ส่วน refresh token ยังอยู่ใน httpOnly cookie เสมอ
ถ้าไม่อยากเปิดช่องนี้เลย ให้ลบ `NEXT_PUBLIC_WS_URL` แล้วระบบจะใช้ polling แทน
**🔑** A deliberate trade-off: this token is short-lived; the refresh token never leaves the httpOnly
cookie. Drop `NEXT_PUBLIC_WS_URL` to disable the channel entirely and fall back to polling.

---

## `db_operations.py` — `PostgresOnlySQL`

**TH:** migration operation ที่ทำงานเฉพาะบน PostgreSQL และ **ข้ามเงียบ ๆ** บน sqlite
ใช้กับ exclusion constraint กันคิวชน และ extension สำหรับค้นหาคนไข้
เหตุผล: production ใช้ PostgreSQL เสมอ แต่บางเครื่อง dev/CI รัน sqlite เพื่อทดสอบ logic ล้วน ๆ

**EN:** A migration operation that runs only on PostgreSQL and **silently skips** on sqlite. Used for
the anti-overlap exclusion constraint and patient-search extensions. Production is always PostgreSQL;
some dev/CI machines run sqlite for pure-logic tests.

**⬅️ ใช้โดย / Used by:** `scheduling/migrations/0002_appointment_overlap_exclusion.py`,
`patients/migrations/0003_patient_search_indexes.py`

**🔑 ข้อควรระวัง:** บน sqlite ตาข่ายชั้นฐานข้อมูลไม่ทำงาน — เหลือแค่การกันชนระดับแอปพลิเคชัน (ซึ่งครบทุกกรณี)
**ก่อนขึ้น production ต้องใช้ PostgreSQL เสมอ**
**🔑 Caveat:** on sqlite the DB-level safety net is absent — only the (complete) application-level
guard remains. **Always use PostgreSQL in production.**

---

## `management/commands/seed_dev_data.py`

**TH:** สร้างข้อมูลตัวอย่างสำหรับ dev: 2 สาขา (BKK/CNX), 5 บริการ (มีหนึ่งตัวที่ `requires_doctor=False`),
super admin + ผู้จัดการ/เจ้าหน้าที่ของแต่ละสาขา, แพทย์ 3 คนพร้อมตารางเช้า-บ่ายและพักเที่ยงแบบซ้ำทุกวัน,
คนไข้ 4 คน และคิวตัวอย่างของวันพรุ่งนี้
**สำคัญ:** จองคิวตัวอย่างผ่าน `AppointmentBookingService` **จริง** ข้อมูลที่ได้จึงผ่านกฎกันคิวชนเหมือนของจริง

**EN:** Seeds dev data: 2 branches, 5 services (one not requiring a doctor), a super admin plus
manager/staff per branch, 3 doctors with morning/afternoon schedules and a recurring lunch block,
4 patients, and sample appointments for tomorrow. **Crucially** it books through the real
`AppointmentBookingService`, so seeded data obeys the same anti-collision rules as production.

**🔑 ปฏิเสธการรันเมื่อ `DEBUG=False`** เว้นแต่ใส่ `--force` — ตอบข้อกำหนดข้อ 7 (ห้าม mock data ในระบบจริง)
**🔑** Refuses to run when `DEBUG=False` unless `--force` — satisfying spec §7 (no mock data in production).
**🔑 `--reset`** ลบข้อมูลตัวอย่างเดิมก่อนสร้างใหม่ / wipes previous seed data first.
**🔑 `_ensure_utf8_console()`** แก้ปัญหาคอนโซล Windows (cp1252) พิมพ์ภาษาไทยแล้ว error / fixes Thai output on Windows consoles.

---

## `apps.py`, `__init__.py`, `tests/`

**TH:** `apps.py` = AppConfig (`verbose_name` ภาษาไทย), `tests/test_time_intervals.py` = เทสต์ของ
`time_intervals.py` แบบ `SimpleTestCase` (ไม่แตะ DB จึงเร็วมาก) ครอบคลุม overlap, subtract, merge,
clamp, การสร้าง slot และการยืนยันว่า UTC กับเวลาท้องถิ่นอ้างถึงช่วงเวลาเดียวกัน

**EN:** `apps.py` is the AppConfig; `tests/test_time_intervals.py` covers `time_intervals.py` with
`SimpleTestCase` (no DB, very fast): overlap, subtract, merge, clamp, slot generation, and that UTC
and local time describe the same instant.
