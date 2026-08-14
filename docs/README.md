# Code Guide — คู่มืออธิบายโค้ดรายไฟล์ (ไทย/English)

เอกสารชุดนี้อธิบาย **ทุกไฟล์ในโปรเจกต์** ว่า *ทำหน้าที่อะไร* และ *เชื่อมโยงกับไฟล์ไหนอย่างไร*
ทุกหัวข้อเขียนสองภาษา: **TH** (ไทย) และ **EN** (English)

This guide set explains **every file in the project** — what it does and how it connects to the rest.
Every entry is bilingual: **TH** (Thai) and **EN** (English).

---

## แผนที่เอกสาร / Document map

| # | ไฟล์ / File | ครอบคลุม / Covers |
|---|---|---|
| 00 | [00-how-to-read.md](00-how-to-read.md) | วิธีอ่านคู่มือนี้ + สัญลักษณ์ที่ใช้ / How to read this guide |
| 01 | [01-architecture.md](01-architecture.md) | ภาพรวมสถาปัตยกรรม, การไหลของ request, แผนผังการพึ่งพา / Architecture, request flow, dependency map |
| 02 | [02-backend-config.md](02-backend-config.md) | `backend/config/` — settings, urls, asgi, wsgi, celery |
| 03 | [03-backend-common.md](03-backend-common.md) | `apps/common/` — โครงสร้างพื้นฐานที่ใช้ร่วมกันทุกแอป / shared infrastructure |
| 04 | [04-backend-accounts-clinics.md](04-backend-accounts-clinics.md) | `apps/accounts/`, `apps/clinics/` — ผู้ใช้, JWT, สาขา / users, JWT, branches |
| 05 | [05-backend-doctors-services.md](05-backend-doctors-services.md) | `apps/doctors/`, `apps/services/` — แพทย์, ตาราง, บริการ / doctors, schedules, service types |
| 06 | [06-backend-scheduling.md](06-backend-scheduling.md) | ★ `apps/scheduling/` — คำนวณเวลาว่าง + จองคิว (หัวใจระบบ) / slot math + booking (core) |
| 07 | [07-backend-queue.md](07-backend-queue.md) | `apps/queue/` — หน้างาน, walk-in, WebSocket realtime |
| 08 | [08-backend-patients.md](08-backend-patients.md) | `apps/patients/` — ฐานข้อมูลคนไข้, ค้นหา, โน้ต / patient DB, search, notes |
| 09 | [09-backend-reports-notifications.md](09-backend-reports-notifications.md) | `apps/reports/`, `apps/notifications/` — รายงาน, SMS + Celery |
| 10 | [10-frontend.md](10-frontend.md) | `frontend/` — Next.js ทั้งหมด (pages, components, lib, types) |
| 11 | [11-devops-and-tests.md](11-devops-and-tests.md) | Docker, env, migrations, seed, ชุดเทสต์ / tests |
| 12 | [12-api-reference.md](12-api-reference.md) | สรุป endpoint ทั้งหมด + ไฟล์ที่รับผิดชอบ / endpoint → file map |

---

## ถ้าคุณเป็นมือใหม่ / If you are new

เริ่มที่ [`LEARNING.md`](../LEARNING.md) ที่ราก repo ก่อน — เป็นบทเรียนแบบไล่ลำดับพร้อมแบบฝึกหัด
แล้วค่อยกลับมาที่คู่มือชุดนี้เพื่อดูรายละเอียดรายไฟล์

Start with [`LEARNING.md`](../LEARNING.md) at the repo root — a step-by-step course with exercises.
Then come back here for per-file detail.

---

## เอกสารอื่นในโปรเจกต์ / Other project docs

| ไฟล์ / File | คืออะไร / What it is |
|---|---|
| [`CLAUDE.md`](../CLAUDE.md) | ข้อกำหนดต้นทาง (requirements/spec) — กติกาที่โค้ดทั้งหมดต้องเคารพ / the source spec |
| [`README.md`](../README.md) | วิธีติดตั้งและรัน / setup & run instructions |
| [`LEARNING.md`](../LEARNING.md) | บทเรียนสำหรับมือใหม่ / beginner course |
| `/api/docs/` (runtime) | Swagger UI จาก drf-spectacular / live OpenAPI docs |
