# 09 — `apps/reports/` + `apps/notifications/`

---

# ส่วนที่ 1 — `apps/reports/` (รายงานเชิงบริหาร / management reports)

**TH:** แอปนี้ **ไม่มี model เลย** ทุกตัวเลขคำนวณสด ๆ จากตาราง `Appointment` ด้วย ORM aggregation
ผลคือไม่มีข้อมูลสรุปที่ค้างเก่า และไม่ต้องดูแลงาน sync ใด ๆ

**EN:** This app has **no models**. Every number is computed live from `Appointment` via ORM
aggregation — no stale summary tables and no sync jobs to maintain.

---

## `reports/services.py`

### `ReportPeriod` (dataclass)
**TH:** ช่วงวันที่ที่สนใจ (รวมวันเริ่มและวันสิ้นสุด) `as_datetime_bounds(tz)` แปลงเป็นขอบเขต datetime
ตามเวลาท้องถิ่นของสาขา — ไม่งั้นรายงาน "วันที่ 1–7" จะกินคิวหัวค่ำของวันที่ 7 ไม่ครบ

**EN:** An inclusive date range; `as_datetime_bounds(tz)` converts it into local-time datetime bounds,
otherwise a "1st–7th" report would miss the 7th's evening appointments.

### `AppointmentReportService`

**TH:** รับ `clinic=None` ได้สำหรับ Super Admin ที่ดูภาพรวมทุกสาขา (ใช้ Asia/Bangkok เป็นโซนอ้างอิงกลาง)

**EN:** Accepts `clinic=None` for a Super Admin viewing all branches (falling back to Asia/Bangkok
as the reference zone).

| Method | คืนอะไร (TH) | Returns (EN) |
|---|---|---|
| `base_queryset(period, doctor_id)` | คิวทั้งหมดในช่วง (ยังไม่กรองสถานะ) | All appointments in range |
| `summary(period, group_by, doctor_id)` | ก้อนใหญ่: totals, series, peak_hours, by_service, by_doctor, average_waiting_minutes | The full dashboard payload |
| `no_show_rate(period, doctor_id)` | อัตราผิดนัดรวม + แยกรายแพทย์ | Overall and per-doctor no-show rates |

**ส่วนคำนวณย่อย / sub-computations:**

| Private method | ทำอะไร (TH) | What it does (EN) |
|---|---|---|
| `_status_totals()` | นับแยกทุกสถานะด้วย `Count(filter=Q(...))` ครั้งเดียว | Per-status counts in one aggregate |
| `_time_series()` | `TruncDate`/`TruncMonth` ตาม `group_by` → กราฟเส้น/แท่ง | Daily or monthly buckets for the chart |
| `_peak_hour_heatmap()` | `ExtractIsoWeekDay` × `ExtractHour` → heatmap ชั่วโมงเร่งด่วน | Weekday × hour heatmap |
| `_service_breakdown()` | จำนวนคิว + **รายได้เฉพาะคิวที่เสร็จสิ้น** | Volume + revenue (completed only) |
| `_doctor_breakdown()` | จำนวนคิว, เสร็จสิ้น, นาทีที่ถูกจองรวม | Volume, completions, booked minutes |
| `_average_waiting_minutes()` | เวลารอเฉลี่ยจริง (เช็คอิน → เริ่มรักษา) | Real average waiting time |

**🔑 ทุก `Trunc`/`Extract` ส่ง `tzinfo=self.zone`** — ไม่งั้น "ยอดจองวันที่ 5" จะนับตาม UTC และเพี้ยน 7 ชั่วโมง
**🔑** Every truncation/extraction passes `tzinfo`, otherwise daily totals shift by the UTC offset.

**🔑 ตัวหารของ no-show rate ไม่รวมคิวที่ยกเลิก** — คนไข้ที่แจ้งล่วงหน้าไม่ถือว่าผิดนัด
ถ้ารวมเข้าไปด้วย ตัวเลขจะดูดีเกินจริง
**🔑** Cancelled appointments are excluded from the denominator — advance cancellations aren't
no-shows, and including them would flatter the metric.

**🔑 `_average_waiting_minutes()` ใช้ `output_field=DurationField()`**
เพราะผลต่างของ timestamp มีหน่วยต่างกันในแต่ละฐานข้อมูล การประกาศ output field ทำให้ Django
แปลงเป็น `timedelta` ให้เองอย่างถูกต้อง และคำนวณในฐานข้อมูล ไม่ต้องดึงทุกแถวมานับใน Python
**🔑** Declaring the output field lets Django return a proper `timedelta` regardless of backend, and
keeps the computation in the database.

**🔑 ระวัง weekday สองระบบ:** ที่นี่ใช้ ISO (จันทร์=**1**) ส่วน `doctors.Weekday` ใช้ Python (จันทร์=**0**)
frontend มี `ISO_WEEKDAY_LABELS` ที่ตรงกับ ISO
**🔑 Two weekday bases coexist:** ISO here (Monday=1) vs Python in `doctors.Weekday` (Monday=0). The
frontend's `ISO_WEEKDAY_LABELS` matches the ISO one.

---

## `reports/views.py`

| View | Endpoint | หน้าที่ (TH) | Role (EN) |
|---|---|---|---|
| `BaseReportView` | — | 🔒 ตรวจสิทธิ์ (`IsBranchManager`), หาสาขา, อ่านช่วงวันที่ | Shared permission, clinic resolution and date parsing |
| `SummaryReportView` | `GET /api/reports/summary/` | สรุปยอดจอง + heatmap | Booking summary + heatmap |
| `NoShowRateReportView` | `GET /api/reports/no-show-rate/` | อัตราผิดนัดแยกรายแพทย์ | No-show rate by doctor |

**🔑 `get_report_service()`** — Super Admin ไม่ส่ง `clinic_id` = ดูรวมทุกสาขา, ส่งมา = เจาะสาขาเดียว
ส่วน role อื่นถูกล็อกที่สาขาตัวเองเสมอ 🔒
**🔑** Super Admin sees everything (or one branch with `?clinic_id=`); other roles are pinned to
their own branch. 🔒

**🔑 `MAX_REPORT_RANGE_DAYS = 366`** — กัน query หนักเกินไปโดยไม่ตั้งใจ (เช่นเผลอขอ 10 ปี)
**🔑** Caps accidental multi-year queries.

**🔑 ค่าเริ่มต้นคือย้อนหลัง 30 วันถึงวันนี้** ถ้าไม่ส่งช่วงวันที่มา

**🔒 permission = `IsBranchManager`** — เจ้าหน้าที่หน้าเคาน์เตอร์และแพทย์ **เข้าไม่ได้**
(เมนู "รายงาน" ฝั่ง frontend ก็ถูกซ่อนตาม role อยู่แล้ว แต่การตรวจจริงอยู่ที่นี่)

---

## `reports/urls.py` / `apps.py`

**TH:** สอง path ตรง ๆ mount ที่ `/api/reports/` — ไม่มี model, migrations, serializers
(response เป็น dict ที่ประกอบใน service layer)
**EN:** Two explicit paths at `/api/reports/`. No models, migrations, or serializers — responses are
plain dicts assembled in the service layer.

---

# ส่วนที่ 2 — `apps/notifications/` (SMS reminder)

---

## `notifications/models.py` — `SMSLog`

**TH:** หนึ่งแถว = หนึ่งข้อความที่ระบบ *พยายาม* ส่ง เก็บไว้เพื่อ (1) ตรวจสอบย้อนหลังว่าคนไข้ได้รับการเตือนไหม
และ (2) **กันการส่งซ้ำ**

**EN:** One row per *attempted* message, kept both for auditing and to **prevent duplicates**.

| สถานะ / Status | ความหมาย | Meaning |
|---|---|---|
| `pending` | สร้างแล้วรอส่ง | Created, awaiting send |
| `sent` | ส่งสำเร็จ | Delivered to the gateway |
| `failed` | ส่งไม่สำเร็จ (retry ได้) | Failed (retryable) |

**★ Constraint กันส่งซ้ำ / the anti-duplicate constraint:**
```python
UniqueConstraint(
    fields=["appointment", "kind"],
    condition=~Q(status=SmsStatus.FAILED),
)
```
อ่านว่า: *"หนึ่งนัดมีข้อความเตือนได้ครั้งเดียว — ยกเว้นแถวที่ส่งไม่สำเร็จ ซึ่งไม่ถูกนับ จึง retry ได้"*
*"One reminder per appointment — failed rows are excluded from the constraint so retries remain possible."*

**Method:** `mark_sent(provider, message_id)` / `mark_failed(provider, error)` — อัปเดตเฉพาะ field ที่เปลี่ยน

**🔑 `__str__` ใช้ `masked_phone`** 🔒 เพื่อไม่ให้เบอร์เต็มโผล่ใน log/admin โดยไม่จำเป็น

---

## `notifications/providers.py` — 🔌 ตัวเชื่อม SMS Gateway

**TH:** ออกแบบตามหลัก OOP: interface กลาง + implementation ต่อเจ้า + factory
**เพิ่มผู้ให้บริการใหม่ = เขียน class เดียวแล้วลงทะเบียนใน `_REGISTRY` ไม่ต้องแก้ส่วนอื่นของระบบเลย**

**EN:** A textbook strategy pattern: one interface, one class per provider, plus a factory.
**Adding a provider = writing one class and registering it — nothing else changes.**

| Class | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `SmsSendResult` (dataclass) | ผลการส่งหนึ่งครั้ง (`success`, `provider`, `provider_message_id`, `error_message`) | One send result |
| `SmsConfigurationError` | ตั้งค่าไม่ครบ (เช่นไม่ได้ใส่ API key) | Missing configuration |
| `BaseSmsProvider` (ABC) | interface กลาง + `_mask()` สำหรับ log | Interface + masking helper |
| `ConsoleSmsProvider` | เขียนลง log แทนการส่งจริง (dev) | Logs instead of sending (dev) |
| `ThaiBulkSmsProvider` | HTTP API + basic auth, รองรับ `sender_name` ต่อสาขา | Thai gateway with per-branch sender name |
| `TwilioSmsProvider` | REST API ตรง ๆ (ไม่เพิ่ม SDK) + แปลงเบอร์เป็น E.164 (`0xx` → `+66xx`) | Direct REST (no SDK) + E.164 conversion |
| `SmsProviderFactory` | เลือก provider ตามการตั้งค่าของสาขา (fallback เป็นค่าเริ่มต้นของระบบ) | Picks the provider per branch, falling back to the system default |

**🔒 กฎความปลอดภัยสองข้อในไฟล์นี้ / two security rules here:**
1. **credential อ่านจาก environment variable เท่านั้น** — ไม่มีใน DB ไม่มีในโค้ด
   *Credentials come only from environment variables.*
2. **ห้าม log เบอร์เต็มหรือเนื้อหาข้อความ** — ทุก log ใช้ `_mask()` และบอกแค่ความยาวข้อความ
   *Never log full numbers or message bodies; logs use `_mask()` and message length only.*

**🔑 `ConsoleSmsProvider` ไม่ใช่ mock data** — ไม่ได้ปลอมข้อมูลใน DB แต่เป็น *ช่องทางส่ง* แบบไม่มีค่าใช้จ่าย
ระหว่างพัฒนา ต้องเปลี่ยนเป็น provider จริงผ่าน env ก่อนขึ้น production
**🔑** It isn't mock data — nothing fake enters the database; it's a zero-cost *transport* for
development. Switch providers via env before production.

**🔑 timeout 10 วินาที** ทุกคำขอ — กัน worker ค้างเพราะ gateway ไม่ตอบ

---

## `notifications/services.py` — `AppointmentReminderService`

**TH:** หน้าที่สองอย่าง: (1) หานัดที่ถึงเวลาต้องเตือนแล้วสร้าง `SMSLog` (2) ส่งจริงแล้วบันทึกผล

**EN:** Two jobs: find appointments due for a reminder and create their logs, then actually send and
record the outcome.

| Method | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `find_due_appointments(now)` | นัดที่อยู่ในหน้าต่างเตือน, สถานะ `booked`/`confirmed`, และ **ยังไม่มี log ค้างอยู่** | Appointments in the window, still active, with no pending/sent log |
| `create_reminder_log(appointment)` | สร้าง log สถานะ `pending` (คืน `None` ถ้ามีอยู่แล้ว) | Create a pending log (`None` if one exists) |
| `build_message(appointment)` | ข้อความภาษาไทย: ชื่อ, บริการ, แพทย์, วัน-เวลา (แปลงเป็นเวลาสาขาแล้ว), ชื่อสาขา, เบอร์ติดต่อ | Thai message body with local time |
| `send(sms_log, provider=None)` | ส่งผ่าน provider ของสาขา แล้ว `mark_sent()`/`mark_failed()` | Send and record the result |

**🔑 `REMINDER_WINDOW = 1 ชั่วโมง 5 นาที`** — **กว้างกว่า** รอบของ Celery beat (ทุก 1 ชั่วโมง) เล็กน้อย
เผื่องานรันช้ากว่ากำหนดนิดหน่อย จะได้ไม่มีนัดหลุดการเตือน ส่วนการส่งซ้ำถูกกันด้วย unique constraint อยู่แล้ว
**🔑** The window is deliberately slightly **wider** than the hourly beat, so a late run never misses
an appointment; duplicates are already prevented by the unique constraint.

**🔑 `build_message()` ไม่ใส่ข้อมูลอ่อนไหวเกินจำเป็น** 🔒 — ไม่มีรหัสคนไข้ ไม่มีรายละเอียดการรักษา
เพราะ SMS ไม่ได้เข้ารหัสและอาจถูกอ่านบนหน้าจอล็อก
**🔑** The message omits patient codes and treatment details — SMS is unencrypted and visible on lock screens.

**🔑 ตั้งค่า provider ผิด → `mark_failed()` ไม่ใช่ crash** เจ้าหน้าที่จึงเห็นสาเหตุในหน้าประวัติการส่ง

---

## `notifications/tasks.py` — Celery tasks

| Task | หน้าที่ (TH) | Role (EN) |
|---|---|---|
| `queue_appointment_reminders()` | รันทุกชั่วโมงโดย beat: หานัดที่ถึงเวลา → สร้าง log → สั่ง `send_sms.delay()` ทีละใบ | Hourly: find due, create logs, dispatch one task per message |
| `send_sms(sms_log_id)` | ส่งหนึ่งใบ, **retry สูงสุด 3 ครั้ง ทุก 5 นาที** เผื่อ gateway ขัดข้องชั่วคราว | Send one message, retrying 3× every 5 minutes |

**🔑 ทำไมแตกเป็น task ย่อยรายข้อความ:** ข้อความหนึ่งที่ล้มเหลวจะไม่ทำให้ทั้งรอบล้มตาม
และ retry เฉพาะใบที่มีปัญหาได้
**🔑 Why one task per message:** a single failure doesn't take down the batch, and only the failing
message retries.

**🔑 log ที่ถูกลบไปแล้ว → คืน `False` ไม่ crash**

---

## `notifications/views.py` — `SMSLogViewSet`

**TH:** 🔒 **read-only** เพราะการส่งจริงถูกสั่งโดยระบบ (Celery) เท่านั้น ไม่ใช่โดยผู้ใช้
ใช้ `BranchScopedQuerySetMixin` (เห็นเฉพาะสาขาตัวเอง) + `IsBranchManager` (ผู้จัดการขึ้นไป)
รองรับกรอง `?status=`, `?appointment_id=`

**EN:** 🔒 Read-only, because sending is system-driven. Branch-scoped and manager-only, with status
and appointment filters.

---

## `notifications/serializers.py` — `SMSLogSerializer`

**TH:** 🔒 แสดง `masked_phone` แทนเบอร์เต็ม, `read_only_fields = fields` (แก้ไขอะไรไม่ได้เลย)
**EN:** 🔒 Exposes the masked phone only; every field is read-only.

---

## `notifications/urls.py` / `admin.py` / `migrations/`

**TH:** router mount `sms-logs/` ที่ `/api/notifications/`; admin ตั้ง `readonly_fields` ของ timestamp;
`0001` สร้างตาราง + constraint, `0002` เพิ่ม FK ที่ต้องรอแอปอื่น (patient/appointment/clinic)
**EN:** A `sms-logs/` router under `/api/notifications/`; a read-only-timestamps admin; `0001` creates
the table and constraint while `0002` adds the cross-app FKs.
