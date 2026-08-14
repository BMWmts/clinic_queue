# 04 — `apps/accounts/` + `apps/clinics/` — ผู้ใช้, JWT, สาขา / users, JWT, branches

---

# ส่วนที่ 1 — `apps/accounts/` (ผู้ใช้และการยืนยันตัวตน / users & auth)

## `accounts/models.py` — `User` + `UserManager`

**TH:** บัญชีของ **เจ้าหน้าที่ภายในคลินิกเท่านั้น** (ไม่มีบัญชีลูกค้า) ใช้ `email` เป็น username
และผูกทุกบัญชีกับ **สาขา** เพื่อให้ระบบ scope ข้อมูลได้ตั้งแต่ระดับ auth

**EN:** Accounts for **clinic staff only** (no customer accounts). `email` is the username, and every
account is bound to a **branch** so data scoping starts at the auth layer.

| สมาชิก / Member | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `UserManager.create_user()` | บังคับมี email, normalize เป็นตัวพิมพ์เล็ก, hash รหัสผ่าน, เรียก `full_clean()` | Requires email, lowercases it, hashes the password, runs `full_clean()` |
| `UserManager.create_superuser()` | บังคับ role เป็น `super_admin` เท่านั้น 🔒 | Forces `super_admin` role 🔒 |
| `can_access_all_branches` | property — Super Admin เท่านั้นที่ query ข้ามสาขาได้ | Only Super Admin queries across branches |
| `is_branch_manager` | property — จัดการตาราง/บริการ/ผู้ใช้ในสาขาได้ | May manage schedules/services/users in the branch |
| `is_doctor` | property — ใช้กรองคิวให้แพทย์เห็นเฉพาะของตัวเอง | Used to narrow queues to the doctor's own |
| `can_access_clinic(id)` | ตรวจว่าแตะข้อมูลสาขานี้ได้ไหม | Checks branch access |
| CheckConstraint | 🔒 role ที่ไม่ใช่ super_admin **ต้อง** มีสาขา ไม่งั้น branch scoping ไร้ความหมาย | 🔒 Non-super-admin roles **must** have a clinic, otherwise scoping is meaningless |

**⬅️ ใช้โดย / Used by:** ทุกที่ที่มี `request.user`, `settings.AUTH_USER_MODEL`, `Doctor.user` (OneToOne)
**➡️ ใช้:** `common/roles.py`

**🔑** `phone_validator` บังคับรูปแบบเบอร์ไทย `^0\d{8,9}$` — ใช้ pattern เดียวกับ `patients/models.py`
**🔑** `save()` บังคับ lowercase email ทุกครั้ง เพื่อให้ login ไม่พลาดเพราะพิมพ์ตัวใหญ่

---

## `accounts/serializers.py`

| Serializer | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `UserSerializer` | แสดงผลผู้ใช้ — **ไม่มี** field password และเพิ่ม `role_display`, `clinic_name` ให้ frontend ใช้ตรง ๆ | Read view — **no** password field, adds display labels |
| `UserWriteSerializer` | สร้าง/แก้บัญชี, password เป็น `write_only` และผ่าน `validate_password()` ของ Django | Create/update; password is `write_only` and validated by Django |
| `LoginSerializer` | ตรวจ email/password ผ่าน `authenticate()` | Authenticates credentials |
| `ChangePasswordSerializer` | เปลี่ยนรหัสผ่านตัวเอง — **ต้องยืนยันรหัสเดิมก่อน** 🔒 | Self-service change — **current password required** 🔒 |

**🔒 จุดความปลอดภัยสำคัญ / Security highlights:**
- `LoginSerializer` คืน **ข้อความ error เดียวกันทุกกรณี** ("อีเมลหรือรหัสผ่านไม่ถูกต้อง")
  ทั้งกรณีอีเมลไม่มีจริงและรหัสผิด → ผู้โจมตีแยกไม่ได้ว่าอีเมลไหนมีอยู่ในระบบ
  *One identical error message for both "no such email" and "wrong password" — attackers cannot
  enumerate valid emails.*
- `UserWriteSerializer.validate()` กัน privilege escalation: ผู้จัดการสาขา **สร้าง/แก้บัญชี super_admin ไม่ได้**
  *Branch managers cannot create or modify `super_admin` accounts.*
- ผู้ใช้ทั่วไปไม่ต้องส่ง `clinic` มา — ระบบเติมสาขาของตัวเองให้ (ไม่เชื่อ client)
  *Regular users don't send `clinic`; the server fills in their own.*

---

## `accounts/views.py`

| View | Endpoint | หน้าที่ (TH) | Role (EN) |
|---|---|---|---|
| `LoginView` | `POST /api/auth/login/` | ตรวจรหัสผ่าน → คืน access + refresh + ข้อมูลผู้ใช้ 🔒 มี rate limit (`throttle_scope = "login"`) | Verify credentials → tokens + profile; 🔒 rate-limited |
| `RefreshView` | `POST /api/auth/refresh/` | ออก access ใบใหม่ และ **blacklist ใบเก่า** ทันที (token rotation) 🔒 | Issue a new pair and **blacklist the old refresh** 🔒 |
| `LogoutView` | `POST /api/auth/logout/` | blacklist refresh token (token หมดอายุแล้วถือว่า logout สำเร็จเช่นกัน) | Blacklist the refresh token; already-expired counts as success |
| `MeView` | `GET /api/auth/me/` | ข้อมูลผู้ใช้ปัจจุบัน — frontend ใช้ตัดสินใจแสดงเมนูตาม role | Current user; drives role-based menus |
| `ChangePasswordView` | `POST /api/auth/change-password/` | เปลี่ยนรหัสผ่านตัวเอง | Self-service password change |
| `UserViewSet` | `/api/auth/users/` | CRUD บัญชีในสาขา (ผู้จัดการขึ้นไป) + branch scoping | Branch-scoped user CRUD for managers |

**🔑 backend คืน token เป็น JSON เฉย ๆ** — คนที่เก็บลง httpOnly cookie คือ Next.js
(`frontend/app/api/auth/login/route.ts`) นี่คือจุดเชื่อมสำคัญที่สุดระหว่างสองฝั่ง
**🔑** The backend just returns tokens as JSON; **Next.js** is what stores them in httpOnly cookies
(`frontend/app/api/auth/login/route.ts`) — the most important seam between the two halves.

**🔑 `UserViewSet.perform_create/perform_update`** override เพราะ `User` ไม่ใช่ `AuditableModel`
จึงเติมเฉพาะ `clinic` (และยกเว้น super_admin ที่ไม่ต้องมีสาขา)

**➡️ ใช้:** `common/mixins.BranchScopedQuerySetMixin`, `common/permissions.IsBranchManager`, `simplejwt`

---

## `accounts/urls.py`

**TH:** mount ที่ `/api/auth/` — 5 path เดี่ยว + router สำหรับ `users/`
**EN:** Mounted at `/api/auth/` — five explicit paths plus a router for `users/`.

---

## `accounts/admin.py`

**TH:** หน้า Django admin สำหรับ **ตั้งค่าบัญชีเริ่มต้นเท่านั้น** (งานประจำวันใช้หน้าเว็บของระบบ)
สืบทอด `BaseUserAdmin` และปรับ fieldsets ให้ตรงกับ field จริงของโมเดลนี้ (ไม่มี `username`)

**EN:** Django admin for **initial account setup only** (day-to-day work happens in the app UI).
Extends `BaseUserAdmin` with fieldsets matching this model (no `username` field).

---

## `accounts/migrations/0001_initial.py`

**TH:** สร้างตาราง `User` พร้อม CheckConstraint "role ที่ไม่ใช่ super_admin ต้องมีสาขา"
**EN:** Creates the `User` table with the "non-super-admin requires a clinic" check constraint.

---

## `accounts/tests/test_auth_and_scoping.py`

**TH:** 12 เทสต์ แบ่งสองกลุ่ม
- `AuthenticationApiTests` — login คืน token + profile, **ไม่มี field password หลุดออกไปเลย**,
  รหัสผิดได้ข้อความกลาง ๆ, บัญชีที่ปิดใช้งาน login ไม่ได้, `/me` ต้อง auth
- `BranchScopingApiTests` — 🔒 staff เห็นคิวเฉพาะสาขาตัวเอง, เปิดคิวสาขาอื่นตรง ๆ ไม่ได้,
  Super Admin เห็นทุกสาขาและกรองด้วย `?clinic_id=` ได้, staff สร้างสาขาไม่ได้

**EN:** 12 tests in two groups: authentication behaviour (tokens, no password leakage, generic error
message, inactive users blocked) and 🔒 branch scoping (staff confined to their branch, Super Admin
cross-branch with optional filtering, staff cannot create clinics).

---

# ส่วนที่ 2 — `apps/clinics/` (สาขา / branches)

## `clinics/models.py` — `Clinic` + `SmsProvider`

**TH:** หนึ่งแถว = หนึ่งสาขา ค่าที่เก็บไว้ **มีผลโดยตรงต่อการคำนวณคิว** จึงถือว่าไฟล์นี้เป็นส่วนหนึ่งของ core

**EN:** One row per branch. Several fields **directly drive slot math**, making this part of the core.

| Field | ผลต่อระบบ (TH) | Effect on the system (EN) |
|---|---|---|
| `opening_time` / `closing_time` | ขอบเขตนอกสุดของทุก slot — ต่อให้แพทย์ตั้งตารางกว้างกว่าก็ถูกตัด | Outer bound of every slot; wider doctor schedules get clamped |
| `timezone` | ใช้แปลง UTC ↔ เวลาท้องถิ่นทุกจุด | Drives every UTC ↔ local conversion |
| `slot_interval_minutes` | ความละเอียดของตาราง เช่น เสนอเวลาทุก 15 นาที | Slot granularity (e.g. offer times every 15 min) |
| `non_doctor_service_capacity` | เพดานคิวพร้อมกันของบริการที่ไม่ต้องมีแพทย์ (เช่น จำนวนเตียงดริป) | Concurrency cap for doctor-less services (e.g. drip beds) |
| `code` | prefix ของรหัสคนไข้ เช่น `BKK-000123` | Prefix for patient codes |
| `sms_provider` / `sms_sender_name` | ให้แต่ละสาขาใช้ผู้ให้บริการ SMS คนละเจ้าได้ | Per-branch SMS provider selection |

**Method สำคัญ / Key method:** `opening_interval_on(date)` → คืน `TimeInterval` ของเวลาทำการวันนั้น
พร้อม timezone — เป็นตัวที่ `SlotAvailabilityService` ใช้ตัดขอบทุกครั้ง
*Returns the day's opening hours as a timezone-aware `TimeInterval`, used by `SlotAvailabilityService`
to clamp every calculation.*

**⬅️ ใช้โดย / Used by:** `User.clinic`, `Doctor.clinic`, `Appointment.clinic`, `Patient.home_clinic`,
`SMSLog.clinic`, `scheduling/services.py`, `doctors/services.py`, `reports/services.py`
**➡️ ใช้:** `common/models.TimeStampedModel`, `common/time_intervals.TimeInterval`, `common/timezone_utils.combine_local`

**🔑** `save()` บังคับ `code` เป็นตัวพิมพ์ใหญ่, CheckConstraint บังคับ "เวลาปิดหลังเวลาเปิด"
**🔑 credential ของ SMS ไม่ได้เก็บที่นี่** — เก็บใน environment variable เท่านั้น ที่นี่เก็บแค่ *ตัวเลือก* 🔒
*SMS credentials are **not** stored here — only the provider *choice*; secrets live in env vars. 🔒*

---

## `clinics/serializers.py` — `ClinicSerializer`

**TH:** แปลง `Clinic` ↔ JSON พร้อม validate เพิ่มสองอย่าง: `timezone` ต้องเป็นชื่อโซนที่ `ZoneInfo` รู้จักจริง
และเวลาปิดต้องหลังเวลาเปิด (validate ซ้ำที่ serializer เพื่อให้ error กลับไปเป็นราย field ที่ frontend แสดงได้)
**ไม่มี field secret ของ SMS gateway** 🔒

**EN:** Serialises `Clinic` with two extra validations: `timezone` must be a real `ZoneInfo` name, and
closing must follow opening (re-validated here so errors come back per-field for the UI). No SMS
secrets are exposed. 🔒

---

## `clinics/views.py` — `ClinicViewSet` + `ClinicAccessPermission`

**TH:** 🔒 Super Admin จัดการได้ทุกสาขา, role อื่น **อ่านได้อย่างเดียว** และเห็นเฉพาะสาขาตัวเอง
(หน้าจอใช้ข้อมูลนี้แสดงเวลาทำการ)

**⚠️ จุดที่ต่างจากแอปอื่น:** ไม่ใช้ `BranchScopedQuerySetMixin` เพราะ `Clinic` **คือ** ตัวสาขาเอง
ไม่มี FK ชื่อ `clinic` ไปหาตัวเอง จึง filter ด้วย `pk=user.clinic_id` ตรง ๆ

**EN:** 🔒 Super Admin manages every branch; other roles get **read-only** access to their own.
**Differs from other apps:** it does not use `BranchScopedQuerySetMixin` because `Clinic` *is* the
branch — there's no `clinic` FK to itself — so it filters on `pk=user.clinic_id`.

---

## `clinics/urls.py` / `clinics/admin.py` / `migrations/0001_initial.py`

**TH:** `urls.py` mount router ที่ `/api/clinics/`; `admin.py` แสดงรายการสาขา (list_display มีเวลาทำการ
และ timezone); migration สร้างตารางพร้อม CheckConstraint เวลาเปิด-ปิด
**EN:** Router mounted at `/api/clinics/`; a simple admin list including opening hours and timezone;
the initial migration creates the table with the opening/closing check constraint.
