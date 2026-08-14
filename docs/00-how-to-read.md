# 00 — วิธีอ่านคู่มือนี้ / How to read this guide

---

## รูปแบบของแต่ละหัวข้อ / Entry format

ทุกไฟล์ในคู่มือนี้อธิบายด้วยรูปแบบเดียวกัน:

Every file is documented with the same shape:

> ### `path/to/file.py`
> **TH:** ไฟล์นี้ทำอะไร (ภาษาไทย)
> **EN:** What this file does (English)
>
> **⬅️ ใครเรียกไฟล์นี้ / Who uses it:** ไฟล์ที่ import หรือเรียกใช้ไฟล์นี้
> **➡️ ไฟล์นี้เรียกใคร / What it uses:** ไฟล์ที่ไฟล์นี้ import หรือพึ่งพา
> **🔑 จุดสำคัญ / Key points:** สิ่งที่ต้องรู้เวลาแก้ไข

---

## สัญลักษณ์ / Symbols

| สัญลักษณ์ | ความหมาย (TH) | Meaning (EN) |
|---|---|---|
| ⬅️ | ใครเรียกไฟล์นี้ (ขาเข้า) | Inbound — who depends on this file |
| ➡️ | ไฟล์นี้เรียกใคร (ขาออก) | Outbound — what this file depends on |
| 🔑 | จุดสำคัญ / ข้อควรระวัง | Key point / caveat |
| ★ | หัวใจของระบบ — แก้แล้วกระทบทั้งระบบ | Core of the system — changes ripple everywhere |
| 🔒 | เกี่ยวกับความปลอดภัย/สิทธิ์ | Security / permission related |

---

## คำศัพท์ที่ใช้บ่อย / Glossary

| คำ | ความหมาย (TH) | Meaning (EN) |
|---|---|---|
| **slot** | ช่วงเวลาหนึ่งช่องที่จองได้ เช่น 09:00–09:30 | One bookable time window |
| **branch scoping** | การจำกัดข้อมูลให้เห็นเฉพาะสาขาตัวเอง | Restricting data to the user's own branch |
| **overbook** | การรับคิวเกินความจุจริง — ระบบนี้ **ห้ามเด็ดขาด** | Booking beyond real capacity — **strictly forbidden here** |
| **service layer** | ชั้นที่เก็บ business logic (`services.py`) แยกจาก view | The layer holding business rules, separate from views |
| **half-open interval** | ช่วงเวลาแบบ `[start, end)` — จบ 10:00 กับเริ่ม 10:00 ไม่ชนกัน | `[start, end)` — an appointment ending at 10:00 does not clash with one starting at 10:00 |
| **occupying status** | สถานะที่ยัง "กินเวลา" ในตาราง (ไม่รวม ยกเลิก/ไม่มา) | Statuses that still consume a slot (excludes cancelled / no-show) |
| **broadcast** | การส่งเหตุการณ์ให้ทุกหน้าจอในสาขาผ่าน WebSocket | Pushing an event to every screen in the branch via WebSocket |

---

## กติกา 5 ข้อที่โค้ดทั้งระบบต้องเคารพ / Five rules the whole codebase obeys

อ่านข้อเหล่านี้ก่อนแก้โค้ดใด ๆ — เกือบทุกการตัดสินใจในโปรเจกต์มาจากข้อใดข้อหนึ่งใน 5 ข้อนี้

Read these before touching any code — nearly every design decision traces back to one of them.

1. **ห้าม overbook เด็ดขาด / Never overbook**
   ทุกการสร้าง/เลื่อนคิว รวมถึง walk-in ต้องผ่าน `SlotAvailabilityService.is_slot_available()`
   *Every create/reschedule, walk-in included, must pass `SlotAvailabilityService.is_slot_available()`.*

2. **ข้อมูลแยกตามสาขา / Data is branch-scoped**
   ทุก queryset ผ่าน `BranchScopedQuerySetMixin` ยกเว้น Super Admin
   *Every queryset goes through `BranchScopedQuerySetMixin`, except for Super Admin.*

3. **Business logic อยู่ใน `services.py` / Business logic lives in `services.py`**
   view แค่แปลง request → เรียก service → แปลงผลลัพธ์
   *Views only translate request → service call → response.*

4. **เวลา: เก็บ UTC คำนวณ/แสดงผลด้วยโซนของสาขา / Time: store UTC, compute & render in the branch's zone**
   ผ่าน `apps/common/timezone_utils.py` เสมอ
   *Always via `apps/common/timezone_utils.py`.*

5. **ไม่มี mock data / No mock data**
   ข้อมูลตัวอย่างอยู่ในคำสั่ง `seed_dev_data` แยกต่างหากเท่านั้น
   *Sample data lives only in the separate `seed_dev_data` command.*

---

## เส้นทางการอ่านที่แนะนำ / Suggested reading order

**ถ้าจะแก้เรื่องคิว/การจอง (most common):**
`01-architecture` → `06-backend-scheduling` → `07-backend-queue` → `10-frontend` (ส่วน QueueBoard)

**ถ้าจะเพิ่ม endpoint ใหม่:**
`03-backend-common` (permission + mixin) → แอปที่เกี่ยวข้อง → `12-api-reference`

**ถ้าจะแก้หน้าจอ:**
`10-frontend` → `12-api-reference` (ดูว่า endpoint คืนอะไร)
