# 10 — `frontend/` — Next.js (App Router) ทั้งหมด

**TH:** ระบบหลังบ้านล้วน ไม่มีหน้าจองสาธารณะ กฎสองข้อที่ทั้งฝั่ง frontend ยึด:
1. **component ห้ามเรียก `fetch()` เอง** — ต้องผ่าน api client ใน `lib/api/`
2. **หน้าจอไม่คำนวณเวลาว่างเอง** — แสดงเฉพาะ slot ที่ backend ส่งมาเท่านั้น

**EN:** A back-office UI only — no public booking page. Two rules the whole frontend obeys:
components never call `fetch()` directly, and the UI never computes availability itself.

---

# 1. ชั้นการยืนยันตัวตน / Auth layer 🔒

**TH:** ส่วนนี้คือเหตุผลที่ token ไม่เคยหลุดไปอยู่ใน JavaScript ของหน้าเว็บ อ่านสี่ไฟล์นี้ต่อกันจะเห็นภาพครบ

**EN:** This is why tokens never reach page JavaScript. Read these four files in order.

## `lib/auth/cookies.ts`
**TH:** จัดการ cookie สองใบ: `clinic_access` (อายุ 15 นาที) และ `clinic_refresh` (7 วัน)
ทั้งคู่ตั้ง `httpOnly: true` (JS อ่านไม่ได้), `sameSite: "lax"` และ `secure` เมื่อเป็น production
มีสองฟังก์ชัน: `setSessionCookies()` และ `clearSessionCookies()`
**ใช้ได้เฉพาะฝั่ง server ของ Next เท่านั้น**

**EN:** Manages the two cookies, both `httpOnly` (invisible to JS), `sameSite=lax`, and `secure` in
production. Server-side only.

**🔑 อายุ cookie ตั้งให้ตรงกับอายุ token ฝั่ง backend** (`JWT_ACCESS_TOKEN_MINUTES` / `JWT_REFRESH_TOKEN_DAYS`)
ถ้าแก้ที่ backend ต้องแก้ค่าคงที่ในไฟล์นี้ด้วย
**🔑** Cookie lifetimes mirror the backend's JWT settings — change one, change the other.

## `app/api/auth/login/route.ts`
**TH:** รับ email/password จากฟอร์ม → ส่งต่อ Django → **เก็บ token ลง cookie** → คืน **เฉพาะข้อมูลผู้ใช้**
กลับไปให้เบราว์เซอร์ (ไม่ส่ง token กลับไปเลย)
**EN:** Forwards credentials to Django, stores the tokens in cookies, and returns **only the user
profile** — never the tokens.

## ★ `app/api/proxy/[...path]/route.ts`
**TH:** หัวใจของชั้น auth ฝั่ง frontend ทำสี่อย่าง:
1. แปลง `/api/proxy/queue/today` → `/api/queue/today/` (เติม `/` ท้ายตามแบบ Django)
2. แนบ `Authorization: Bearer <access>` จาก cookie
3. **ถ้าได้ 401 → ขอ token ใหม่ด้วย refresh token แล้วยิงซ้ำแบบผู้ใช้ไม่รู้สึก** แล้วเซ็ต cookie ใหม่
4. ถ้า refresh ก็ใช้ไม่ได้ → ล้าง cookie แล้วคืน 401 `session_expired`
รองรับ GET/POST/PATCH/PUT/DELETE ด้วย handler ตัวเดียวกัน

**EN:** The heart of the frontend auth layer: path translation, token attachment, **transparent
refresh-and-retry on 401**, and cookie clearing when the refresh token is dead. One handler serves
all five methods.

**🔑 ผลลัพธ์:** ผู้ใช้ทำงานต่อเนื่องได้แม้ access token หมดอายุระหว่างพิมพ์ฟอร์ม
โดยที่ JavaScript ไม่เคยเห็น token เลยสักครั้ง
**🔑 The payoff:** sessions survive token expiry mid-form, and page JS never touches a token.

## `app/api/auth/logout/route.ts`
**TH:** แจ้ง backend ให้ blacklist refresh token แล้วล้าง cookie
**ต่อให้ backend ล้มเหลวก็ยังล้าง cookie ฝั่งเรา** เพื่อให้ผู้ใช้ออกจากระบบได้เสมอ
**EN:** Blacklists server-side then clears cookies — and clears them **even if the backend call fails**,
so logout always works.

## `app/api/auth/ws-token/route.ts`
**TH:** คืน access token ระยะสั้นให้เบราว์เซอร์ใช้ **เฉพาะตอน handshake ของ WebSocket**
(ถ้าหมดอายุแล้วจะ refresh ให้ก่อน) ข้อแลกเปลี่ยนถูกอธิบายไว้ใน docstring ของไฟล์:
token ใบนี้อายุสั้น ส่วน refresh token ยังอยู่ใน httpOnly cookie เสมอ
**ถ้าไม่ต้องการเปิดช่องนี้ ให้ลบ `NEXT_PUBLIC_WS_URL` แล้วระบบจะใช้ polling แทน**

**EN:** Issues a short-lived access token used **only** for the WS handshake, refreshing first if
needed. The trade-off is documented in the file; dropping `NEXT_PUBLIC_WS_URL` disables it entirely
in favour of polling.

## `middleware.ts`
**TH:** ตรวจ **แค่ว่ามี refresh cookie อยู่ไหม** ก่อนเข้าหน้า dashboard ถ้าไม่มี → redirect ไป `/login?next=...`
และถ้ามี session อยู่แล้วแต่เปิด `/login` → พาไป `/queue`
**🔑 นี่คือ UX ไม่ใช่ security** — ตัวตรวจสิทธิ์จริงคือ backend เสมอ ที่นี่แค่กันไม่ให้เห็นโครงหน้าจอแล้วเด้งออก

**EN:** Only checks that a refresh cookie exists before dashboard routes. **This is UX, not security**
— the backend remains the real authority; this just avoids a flash of empty UI.

## `lib/api/backend.ts`
**TH:** ตัวเรียก Django จากฝั่ง server ของ Next (`BACKEND_INTERNAL_URL`) ไม่มี logic ต่ออายุ token
(ผู้เรียกเป็นคนจัดการ) ตั้ง `cache: "no-store"` เพราะข้อมูลคิวเปลี่ยนตลอดเวลา
**EN:** The server-side Django caller. No refresh logic (callers own that) and `cache: "no-store"`
because queue data changes constantly.

---

# 2. ชั้น API client / API layer

## `lib/api/http.ts` — `HttpClient` + `ApiError`

**TH:** ตัวขนส่งกลาง ทุกคำขอวิ่งไป `/api/proxy` เสมอ
- `buildQueryString()` — ตัด `null`/`undefined`/`""` ออก ไม่ให้ส่ง param ว่างไปกวน backend
- `toApiError()` — แปลง response ที่ผิดพลาดเป็น `ApiError` โดยรองรับสองรูปแบบ:
  รูปแบบกลางของเรา (`{"error":{code,message}}`) และ validation error ของ DRF (`{field: [msg]}`)
- `ApiError.isSlotConflict` — `true` เมื่อ code เป็น `slot_unavailable` หรือ `booking_conflict`
- `ApiError.isSessionExpired` — `true` เมื่อ status = 401

**EN:** The shared transport. It strips empty params, normalises both error shapes into `ApiError`,
and exposes two convenience flags used by the dialogs.

**🔑 `httpClient` เป็น instance เดียวที่ api client ทุกโดเมนใช้ร่วมกัน**

## `lib/api/index.ts` — API client แยกตามโดเมน / one class per domain

**TH:** หนึ่ง class ต่อหนึ่งกลุ่มงาน สืบทอดจาก `BaseApiClient` ที่ถือ `HttpClient` ไว้
เวลา backend เปลี่ยนสัญญา แก้ที่ไฟล์นี้ไฟล์เดียว

**EN:** One class per domain, all extending `BaseApiClient`. A backend contract change is a
single-file edit here.

| Class | Method หลัก | ยิงไปที่ / Talks to |
|---|---|---|
| `AuthApiClient` | `me()`, `login()`, `logout()`, `changePassword()` | `/auth/*` (login/logout ยิงไป route handler ของ Next โดยตรง) |
| `ClinicApiClient` | `list()`, `create()`, `update()` | `/clinics` |
| `DoctorApiClient` | `list()`, `schedules()`, `timeBlocks()`, `availability()` | `/doctors/*` |
| `ServiceApiClient` | `list(onlyActive)` — ส่ง `page_size: 200` | `/services` |
| `SchedulingApiClient` | ★ `availableSlots()`, `listAppointments()`, `book()` | `/scheduling/*` |
| `QueueApiClient` | `today()`, `walkIn()`, `changeStatus()`, `reschedule()` | `/queue/*` |
| `PatientApiClient` | `search()`, `retrieve()`, `create()`, `history()`, `notes()`, `addNote()` | `/patients/*` |
| `ReportApiClient` | `summary()`, `noShowRate()` | `/reports/*` |

**🔑 ท้ายไฟล์ export instance สำเร็จรูป** (`queueApi`, `patientApi`, …) component จึง `import { queueApi }`
แล้วใช้ได้เลยโดยไม่ต้อง `new` เอง
**🔑** Ready-made singletons are exported so components import and use them directly.

**🔑 `login()`/`logout()` ไม่ผ่าน `/api/proxy`** เพราะต้องให้ route handler ตั้ง cookie เอง

## `types/api.ts`

**TH:** type ทั้งหมดที่ตรงกับ serializer ฝั่ง Django รวมถึง `Paginated<T>` และ `ApiErrorPayload`
**ห้ามใช้ `any`** — ถ้า backend เพิ่ม field ต้องมาเพิ่มที่นี่ แล้ว `npm run typecheck` จะบอกทุกจุดที่ต้องแก้

**EN:** Types mirroring the Django serializers, including `Paginated<T>` and `ApiErrorPayload`.
No `any` allowed — `npm run typecheck` then points at every place a contract change affects.

**🔑 ตรวจสอบสัญญาได้ที่ `/api/schema/`** (OpenAPI จาก drf-spectacular)

---

# 3. Hooks

## ★ `lib/hooks/useQueueBoard.ts`

**TH:** จัดการข้อมูลคิวของหน้าจอหน้างานทั้งหมด มีสามกลไกทำงานพร้อมกัน:

**EN:** Owns all queue-board data through three concurrent mechanisms:

| กลไก / Mechanism | รายละเอียด (TH) | Detail (EN) |
|---|---|---|
| โหลดครั้งแรก + polling | ยิง `queueApi.today()` ทุก **10 วินาที** — ทำงาน **เสมอ** แม้ WebSocket ต่อติด | Refetch every **10s**, running **even when** the socket is live |
| WebSocket | ขอ token จาก `/api/auth/ws-token` แล้วต่อไป `ws://…/ws/queue/{clinicId}/` | Fetches a WS token then connects |
| `applyUpdatedAppointment()` | แทนที่คิวเดิมในรายการ (หรือเพิ่มใหม่แล้วเรียงตามเวลา) | Replace-or-insert, keeping time order |

**🔑 ทำไม polling ยังทำงานทั้งที่มี WebSocket:** กันข้อมูลค้างเมื่อ socket หลุดเงียบ ๆ
โดยที่ event `onclose` ไม่ยิง (เกิดได้จริงกับ WiFi หน้าร้าน)
**🔑 Why keep polling:** it covers silently dropped sockets where `onclose` never fires — a real
occurrence on shop-floor WiFi.

**🔑 `isLive`** บอกสถานะการเชื่อมต่อ → หน้าจอแสดง "● เรียลไทม์" หรือ "○ อัปเดตทุก 10 วิ" ให้เจ้าหน้าที่รู้ตัว
**🔑 ถ้าไม่ตั้ง `NEXT_PUBLIC_WS_URL`** ส่วน WebSocket จะไม่ทำงานเลย เหลือแต่ polling — ระบบยังใช้งานได้ครบ

## `lib/hooks/useSession.tsx`

**TH:** `SessionProvider` โหลด `/auth/me` ครั้งเดียวตอนเปิด dashboard แล้วแชร์ผ่าน React context
คำนวณสิทธิ์ที่ใช้บ่อยไว้ให้เลย (`canManageBranch`, `canViewReports`, `canOperateQueue`, `isSuperAdmin`)
เพื่อไม่ต้องเช็ค role ซ้ำในแต่ละหน้า ถ้า `/auth/me` ล้มเหลว = เซสชันหมดอายุ → พาไป `/login`

**EN:** Loads the current user once and shares it via context, precomputing the role flags screens
need so no page re-derives them. A failure means the session expired → redirect to `/login`.

**🔑 flag เหล่านี้ใช้ซ่อน/แสดง UI เท่านั้น** 🔒 การตรวจสิทธิ์จริงอยู่ที่ backend เสมอ
**🔑** These flags only shape the UI; the backend remains the authority. 🔒
**🔑 `useSession()` โยน error ถ้าเรียกนอก Provider** — จับ bug ได้ตั้งแต่ตอน dev

## `lib/format.ts`

**TH:** ฟังก์ชันจัดรูปแบบทั้งหมด แยกจาก UI เพื่อให้ใช้ซ้ำและทดสอบได้
ทุกตัวใช้ `Intl.DateTimeFormat` ที่ตรึง `timeZone: "Asia/Bangkok"` → หน้าจอแสดงเวลาไทยเสมอ
ไม่ว่าเครื่องผู้ใช้จะตั้งโซนอะไรไว้

**EN:** All formatting helpers, kept out of the UI. Every one pins `timeZone: "Asia/Bangkok"`, so the
display is Thai time regardless of the workstation's setting.

| Export | หน้าที่ | Role |
|---|---|---|
| `formatTime` / `formatDate` / `formatDateTime` / `formatWeekday` | จัดรูปเวลา/วันที่แบบไทย | Thai time/date formatting |
| `formatTimeRange` | `"09:30 - 10:00"` | Time range |
| `formatBaht` / `formatPercent` | สกุลเงินบาท / เปอร์เซ็นต์ | Currency / percentage |
| `todayIsoDate()` / `isoDateOf()` / `shiftIsoDate()` | `YYYY-MM-DD` ตามเวลาไทย (ใช้ส่งเป็น query param) | Thai-local ISO dates for query params |
| `STATUS_STYLES` | สี + ป้ายชื่อของแต่ละสถานะ **ใช้ตรงกันทุกหน้าจอ** | Per-status colour and label, shared everywhere |
| `ISO_WEEKDAY_LABELS` | ชื่อวัน (จันทร์=1) ให้ตรงกับ `ExtractIsoWeekDay` ของรายงาน | Weekday labels matching the reports' ISO base |

**🔑 `shiftIsoDate()` ประกอบวันที่ด้วย `+07:00` ชัดเจน** เพื่อไม่ให้ปุ่ม "วันก่อน/วันถัดไป" เพี้ยนข้ามเที่ยงคืน
**🔑** It anchors to `+07:00` explicitly so the prev/next-day buttons don't drift across midnight.

---

# 4. หน้าจอและ component / Pages & components

## `app/layout.tsx` / `app/page.tsx` / `app/globals.css`
**TH:** root layout ตั้ง `lang="th"` + metadata; `page.tsx` redirect ไป `/queue`;
`globals.css` โหลด Tailwind + สี `brand-*` + class `table-scroll` (ตารางกว้างเลื่อนแนวนอนได้บนจอเล็ก)
**EN:** Root layout, a redirect to `/queue`, and global styles including the `table-scroll` helper.

## `app/(auth)/login/page.tsx` + `LoginForm.tsx`
**TH:** หน้า login — page เป็น **Server Component** บาง ๆ ที่ห่อ `LoginForm` (Client Component) ไว้ใน `<Suspense>`
เพราะฟอร์มใช้ `useSearchParams()` เพื่ออ่าน `?next=`
ฟอร์มยิงไป `authApi.login()` → route handler ของ Next → Django
**EN:** A thin server component wrapping the client form in `<Suspense>` (the form reads `?next=`
via `useSearchParams()`).

## `app/(dashboard)/layout.tsx`
**TH:** ห่อทุกหน้าด้วย `SessionProvider` แล้วตามด้วย `AppShell`
**EN:** Wraps every dashboard page in `SessionProvider`, then `AppShell`.

## `components/AppShell.tsx`
**TH:** โครงหน้าจอ: sidebar (desktop) / แถบเมนูแนวนอน (mobile) + แถบบนแสดงชื่อผู้ใช้, role, สาขา และปุ่มออกจากระบบ
เมนู "รายงาน" กับ "สาขา" แสดงเฉพาะผู้จัดการขึ้นไป (`requiresBranchManager`)
**EN:** The shell: responsive navigation plus a header with the user, role, branch, and logout.
Reports and Branches appear only for managers.

## `components/ui.tsx`
**TH:** ชิ้นส่วน UI พื้นฐานทั้งหมดในไฟล์เดียว: `Button` (4 variant), `Card`, `StatCard`, `StatusBadge`,
`Field`, `TextInput`, `Select`, `Alert` (3 โทน), `EmptyState`, `LoadingRow`, `Modal`
รวมสไตล์ไว้ที่เดียวเพื่อให้หน้าตาสม่ำเสมอและเปลี่ยนธีมทั้งระบบได้จากไฟล์เดียว

**EN:** Every primitive in one file, so the look stays consistent and the theme changes in one place.

**🔑 `StatusBadge` ดึงสีจาก `STATUS_STYLES`** ใน `lib/format.ts` → เพิ่มสถานะใหม่แก้ที่เดียว

---

### หน้าคิว / Queue screen

## ★ `components/queue/QueueBoard.tsx`
**TH:** หน้าจอหลักที่เจ้าหน้าที่ใช้ทั้งวัน ประกอบด้วย: ตัวเลือกวัน (พร้อมปุ่มวันก่อน/วันนี้/วันถัดไป),
ตัวกรองแพทย์, ป้ายสถานะการเชื่อมต่อ, การ์ดสรุป 5 ใบ, ตารางคิว และปุ่มเปิดกล่อง walk-in/เลื่อนคิว

**EN:** The screen staff live in: date navigation, doctor filter, live-status pill, five summary
cards, the queue table, and the walk-in / reschedule dialogs.

**🔑 `QueueRow` แสดงปุ่มจาก `appointment.allowed_next_statuses` ที่ backend ส่งมา**
→ ไม่มีการเขียน state machine ซ้ำฝั่ง UI ถ้าแก้กฎที่ backend ปุ่มเปลี่ยนตามทันที
**🔑** Buttons come straight from the backend's `allowed_next_statuses` — the state machine is never
duplicated in the UI; change the backend rule and the buttons follow.

**🔑 `activeCount`** นับเฉพาะคิวที่ยังต้องดูแล (`booked`/`confirmed`/`checked_in`/`in_progress`)
เพื่อให้เห็น "งานค้าง" ชัด ๆ ต่างจาก `summary.total` ที่รวมทุกอย่าง

**🔑 ปุ่ม walk-in แสดงเฉพาะ "วันนี้"** เพราะ walk-in คือคนที่ยืนอยู่ตรงหน้าเคาน์เตอร์ตอนนี้

## `components/queue/WalkInDialog.tsx`
**TH:** ฟอร์มรับคิว walk-in: เลือกบริการ → (เลือกแพทย์ถ้าบริการต้องมี) → ค้นหาคนไข้เดิม **หรือ** กรอกคนใหม่ → โน้ต
ระบบจัดเวลาให้อัตโนมัติ ถ้าไม่มีเวลาว่างจริง backend ตอบ 409 แล้วหน้าจอแจ้งให้เลือกแพทย์ท่านอื่น/นัดวันอื่น

**EN:** Service → doctor (if required) → existing-or-new patient → note. The system assigns the time;
a 409 surfaces as "pick another doctor or day".

**🔑 ช่องแพทย์แสดงเฉพาะเมื่อ `selectedService.requires_doctor`** — ตรงกับ validation ฝั่ง backend
ทำให้ผู้ใช้ไม่กรอกสิ่งที่จะถูกปฏิเสธอยู่ดี

## `components/queue/RescheduleDialog.tsx`
**TH:** เลือกวัน + แพทย์ → เรียก `availableSlots()` → แสดงเป็นปุ่มเวลา กดแล้วเลื่อนทันที
**🔑 ถ้าเลื่อนไม่สำเร็จ (มีคนแย่งจองพอดี) จะ `loadSlots()` ใหม่อัตโนมัติ** เพื่อให้รายการตรงกับความจริง

**EN:** Pick a day and doctor, fetch real slots, click to move. **On failure it reloads the slot list**
so the UI resyncs with reality.

---

### หน้าปฏิทินและการจอง / Calendar & booking

## `components/calendar/CalendarBoard.tsx`
**TH:** ตารางรายวัน คอลัมน์ละแพทย์ แถวละ 30 นาที แต่ละช่องมีสี่สถานะ:
`appointment` (มีคิว) / `blocked` (ถูกบล็อก) / `free` (ว่าง กดจองได้) / `off` (นอกเวลาออกตรวจ)
ช่วงเวลาที่แสดงคำนวณจากตารางแพทย์จริง (ถ้าไม่มีข้อมูลใช้ 08:00–20:00 เป็นค่าเริ่มต้น)

**EN:** A day grid: one column per doctor, 30-minute rows, four cell states. The visible time range
is derived from the actual schedules (falling back to 08:00–20:00).

**🔑 `describeCell()` เป็น logic ที่อ่านยากที่สุดในฝั่ง frontend** — ทำงานตามลำดับ:
หาคิวที่ทับช่องนี้ก่อน → ถ้าไม่มีดูว่าถูกบล็อกไหม → ถ้าไม่ดูว่าอยู่ในเวลาออกตรวจไหม
`isFirstRow` ใช้ตัดสินว่าจะพิมพ์ชื่อคนไข้ในช่องนี้ไหม (คิวยาวหลายแถวจะพิมพ์แค่แถวแรก)

**🔑** โหลดข้อมูลสองก้อนพร้อมกันด้วย `Promise.all` (availability ของแพทย์ทุกคน + คิวของวันนั้น)

## `components/booking/BookingDialog.tsx`
**TH:** กล่องจองล่วงหน้า ใช้ได้ทั้งจากหน้าปฏิทินและหน้าประวัติคนไข้ (รับ `initialPatient`/`initialDate`/`initialDoctorId`)
ขั้นตอน: เลือกคนไข้ → เลือกบริการ/แพทย์/วัน → **ระบบแสดงเฉพาะเวลาที่ว่างจริง** → กดยืนยัน
ถ้ามีคนแย่งจองไปก่อน จะได้ 409 แล้วโหลดเวลาว่างใหม่ให้อัตโนมัติ

**EN:** The advance-booking dialog, reused by the calendar and the patient page. It only ever offers
backend-provided slots and reloads them after a 409.

**🔑 `loadSlots()` ไม่ยิง API ถ้ายังเลือกบริการ/แพทย์ไม่ครบ** — ประหยัด request และแสดงข้อความแนะนำแทน

---

### หน้าคนไข้ / Patient screens

## `components/patients/PatientDirectory.tsx`
**TH:** ค้นหาคนไข้ (ข้ามสาขา) + ฟอร์มลงทะเบียนคนไข้ใหม่แบบพับเก็บได้
ผลการค้นหาแสดง **โน้ตที่ปักหมุดใบแรก** ด้วย 📌 เพื่อเตือนเรื่องแพ้ยาตั้งแต่หน้าค้นหา
**EN:** Cross-branch search plus a collapsible new-patient form; results surface the first pinned
note so allergy warnings appear immediately.

**🔑 บังคับพิมพ์อย่างน้อย 2 ตัวอักษร** ตรงกับกฎของ `PatientSearchService` ฝั่ง backend

## `components/patients/PatientDetail.tsx`
**TH:** สามส่วน: ข้อมูลติดต่อ + ปุ่มจองคิวให้คนไข้นี้, `NotesSection` (เพิ่ม/ดูโน้ต พร้อม checkbox ปักหมุด),
และประวัติการจองทั้งหมดพร้อม `StatusBadge`
โหลดสามอย่างพร้อมกันด้วย `Promise.all` (history + notes + รายชื่อแพทย์สำหรับกล่องจอง)

**EN:** Contact card with a booking action, a notes section with pin support, and full booking
history — all three fetched in parallel.

---

### หน้าสาขาและรายงาน / Branches & reports

## `components/branches/BranchManager.tsx`
**TH:** 🔒 Super Admin เพิ่ม/แก้ได้ทุกสาขา, role อื่นเห็นเฉพาะสาขาตัวเองแบบอ่านอย่างเดียว
ฟอร์มเพิ่มสาขาอธิบาย **ผลของแต่ละค่า** ไว้ข้างช่องกรอก (เช่น "ความละเอียดของตาราง" มีผลต่อการเสนอเวลา,
"เพดานคิวไม่ใช้แพทย์" = จำนวนเตียงดริป) เพราะค่าเหล่านี้กระทบการคำนวณคิวโดยตรง

**EN:** 🔒 Super Admin manages all branches; others get read-only access to theirs. The form explains
what each setting *does*, because these values drive slot math directly.

## `components/reports/ReportDashboard.tsx`
**TH:** เลือกช่วงวันที่ + รายวัน/รายเดือน แล้วโหลดสองรายงานพร้อมกัน (`summary` + `noShowRate`)
แสดง: การ์ดสรุป 4 ใบ, กราฟแท่งยอดจอง, heatmap ช่วงเวลาที่คนแน่น, ตารางแยกตามบริการ (พร้อมรายได้),
และตารางอัตราผิดนัดรายแพทย์

**EN:** Date range + granularity, two reports fetched in parallel, rendered as summary cards, a bar
chart, a peak-hour heatmap, a per-service table with revenue, and a per-doctor no-show table.

**🔑 วาดกราฟด้วย CSS ล้วน** (ความสูง % สำหรับแท่ง, `rgba()` ไล่ความเข้มสำหรับ heatmap)
ไม่พึ่งไลบรารีกราฟภายนอก → bundle เล็ก โหลดเร็วบนเครื่องหน้าร้าน
**🔑 Charts are pure CSS** — percentage heights and `rgba()` intensity — so no charting library
bloats the bundle on front-desk machines.

**🔑 `PeakHourHeatmap` ใช้ `Map` เป็น lookup** `"{weekday}-{hour}"` แทนการวน `find()` ทุกช่อง (7×24 = 168 ช่อง)

## `app/(dashboard)/*/page.tsx` (queue, calendar, patients, patients/[id], branches, reports)
**TH:** ทุกหน้าเป็น **Server Component บาง ๆ** — ตั้ง `metadata.title`, ใส่หัวข้อ แล้ววาง Client Component
ที่ทำงานจริง หน้า `patients/[id]` เพิ่มการ validate id (ไม่ใช่จำนวนเต็มบวก → `notFound()`)
ตามแบบของ Next 15 ที่ `params` เป็น Promise

**EN:** All pages are thin server components: title, heading, and the client component that does the
work. `patients/[id]` additionally validates the id (Next 15 delivers `params` as a Promise).

---

# 5. ไฟล์ตั้งค่าของ frontend / config files

| ไฟล์ / File | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `package.json` | scripts: `dev`, `build`, `start`, `lint`, **`typecheck`** — dependency น้อยมาก (next/react เท่านั้น) | Scripts and a deliberately tiny dependency list |
| `tsconfig.json` | strict mode + path alias `@/*` | Strict TS + `@/*` alias |
| `next.config.ts` | `reactStrictMode` + `poweredByHeader: false` 🔒 (ลดข้อมูลที่เปิดเผย) | Strict mode; hides the framework header 🔒 |
| `postcss.config.mjs` | โหลด Tailwind v4 ผ่าน `@tailwindcss/postcss` | Tailwind v4 via PostCSS |
| `.env.example` | `BACKEND_INTERNAL_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_APP_NAME` พร้อมคำอธิบาย | Documented environment template |
| `Dockerfile` / `.dockerignore` | image ของ frontend | Frontend image |

**🔑 ตัวแปรที่ขึ้นต้นด้วย `NEXT_PUBLIC_` จะถูกฝังลง bundle และเห็นได้จากเบราว์เซอร์** 🔒
ห้ามใส่ secret ในตัวแปรเหล่านี้เด็ดขาด — สังเกตว่า `BACKEND_INTERNAL_URL` **ไม่มี** prefix นี้
**🔑** `NEXT_PUBLIC_*` values are baked into the bundle and visible to anyone. Never put secrets
there — note that `BACKEND_INTERNAL_URL` deliberately lacks the prefix.
