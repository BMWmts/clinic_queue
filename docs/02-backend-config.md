# 02 — `backend/config/` + ไฟล์ระดับราก / project-level files

---

## `backend/config/settings.py`

**TH:** ศูนย์รวมการตั้งค่าทั้งหมดของ Django อ่านค่าจาก environment variable เท่านั้น (ไม่มี secret ฝังในโค้ด)
กำหนด: แอปที่ติดตั้ง, ฐานข้อมูล (PostgreSQL ผ่าน `DATABASE_URL`, fallback เป็น sqlite สำหรับเทสต์),
โซนเวลา `Asia/Bangkok` + `USE_TZ=True`, ค่าเริ่มต้นของ DRF (auth = JWT, permission = ต้อง login,
pagination, exception handler, throttle ที่หน้า login), อายุ JWT, CORS/CSRF, Channels layer, Celery
และการเปิด security header เมื่อ `DEBUG=False`

**EN:** The single Django configuration hub. Everything is read from environment variables — no
secret is hardcoded. It defines: installed apps, database (PostgreSQL via `DATABASE_URL`, with an
sqlite fallback for tests), `Asia/Bangkok` timezone with `USE_TZ=True`, DRF defaults (JWT auth,
login-required by default, pagination, the custom exception handler, login throttling), JWT
lifetimes, CORS/CSRF, the Channels layer, Celery, and production security headers when `DEBUG=False`.

**⬅️ ใครใช้ / Used by:** ทุกไฟล์ที่ `from django.conf import settings` และ Django เองตอน boot
**➡️ อ้างถึง / References:** `apps.common.pagination.DefaultPagination`, `apps.common.exceptions.api_exception_handler`, `apps.accounts.User` (ผ่าน `AUTH_USER_MODEL`)

**🔑 จุดสำคัญ / Key points:**
- `DATABASE_URL` ค่าว่าง = "ไม่ได้ตั้งค่า" → ตกไป sqlite ทำให้สั่ง `DATABASE_URL= python manage.py test` ได้
  *An empty `DATABASE_URL` counts as unset → falls back to sqlite, enabling `DATABASE_URL= python manage.py test`.*
- `ROTATE_REFRESH_TOKENS` + `BLACKLIST_AFTER_ROTATION` = refresh token ใบเก่าใช้ซ้ำไม่ได้ 🔒
  *Old refresh tokens become unusable after rotation. 🔒*
- `CELERY_TASK_ALWAYS_EAGER = not REDIS_URL` → ไม่มี Redis ก็ยังรันเทสต์ที่แตะ Celery ได้
  *Without Redis, Celery tasks run synchronously so tests still work.*
- `"login"` throttle rate ปรับได้ผ่าน `LOGIN_THROTTLE_RATE` 🔒
- `daphne` ต้องอยู่ **บนสุด** ของ `INSTALLED_APPS` เพื่อให้ `runserver` เป็น ASGI (WebSocket ทำงาน)
  *`daphne` must be first in `INSTALLED_APPS` so `runserver` speaks ASGI (WebSocket support).*

---

## `backend/config/urls.py`

**TH:** ตารางเส้นทางหลัก แต่ละแอปถูก mount ใต้ `/api/<domain>/` ตรงกับชื่อแอป และเปิด OpenAPI schema
ที่ `/api/schema/` กับ Swagger UI ที่ `/api/docs/`

**EN:** The root routing table. Each app is mounted at `/api/<domain>/` matching the app name, plus
the OpenAPI schema at `/api/schema/` and Swagger UI at `/api/docs/`.

**➡️ include:** `apps.accounts.urls`, `apps.clinics.urls`, `apps.doctors.urls`, `apps.services.urls`,
`apps.scheduling.urls`, `apps.queue.urls`, `apps.patients.urls`, `apps.reports.urls`, `apps.notifications.urls`

**🔑** เพิ่มแอปใหม่ต้องเพิ่มบรรทัด `path(...)` ที่นี่ ไม่งั้น URL ของแอปนั้นจะไม่มีตัวตน
**🔑** A new app needs a `path(...)` line here, otherwise its URLs simply don't exist.

---

## `backend/config/asgi.py`

**TH:** ทางเข้าแบบ ASGI รองรับสองโปรโตคอล: `http` ให้ Django ปกติ, `websocket` ส่งผ่าน
`JWTAuthMiddleware` แล้วเข้า `URLRouter` ของแอป queue
ลำดับ import สำคัญ — ต้องเรียก `get_asgi_application()` **ก่อน** import consumer เพื่อให้ app registry พร้อม

**EN:** The ASGI entrypoint serving two protocols: `http` → normal Django, `websocket` → through
`JWTAuthMiddleware` into the queue app's `URLRouter`. Import order matters: `get_asgi_application()`
must run **before** importing consumers so the app registry is ready.

**⬅️ ใช้โดย / Used by:** `daphne` (docker-compose `backend` service), `runserver` ในโหมด ASGI
**➡️ ใช้:** `apps.common.websocket_auth.JWTAuthMiddleware`, `apps.queue.routing.websocket_urlpatterns`

---

## `backend/config/wsgi.py`

**TH:** ทางเข้าแบบ WSGI (ไม่รองรับ WebSocket) เก็บไว้เผื่อ deploy ด้วย gunicorn/uwsgi ที่ไม่ต้องการ realtime
**EN:** The WSGI entrypoint (no WebSocket). Kept for deployments on gunicorn/uwsgi that don't need realtime.

---

## `backend/config/celery.py`

**TH:** สร้าง Celery app ชื่อ `clinic` อ่าน config จาก Django settings (prefix `CELERY_`) และ autodiscover
`tasks.py` ของทุกแอป พร้อมตั้ง beat schedule ให้รัน `queue_appointment_reminders` **ทุกต้นชั่วโมง**
งานนี้ออกแบบให้ idempotent (มี unique constraint กันส่งซ้ำ) จึงรันถี่ได้อย่างปลอดภัย

**EN:** Creates the `clinic` Celery app, reads config from Django settings (`CELERY_` prefix),
autodiscovers each app's `tasks.py`, and schedules `queue_appointment_reminders` **hourly**.
The task is idempotent (a unique constraint prevents duplicates), so frequent runs are safe.

**⬅️ ใช้โดย / Used by:** `celery -A config worker`, `celery -A config beat` (ดู docker-compose)
**➡️ ใช้:** `apps.notifications.tasks.queue_appointment_reminders`

---

## `backend/manage.py`

**TH:** ตัวสั่งงาน Django ทั้งหมด (`migrate`, `test`, `runserver`, `seed_dev_data`)
**EN:** The Django CLI entrypoint for all commands.

---

## `backend/requirements.txt`

**TH:** รายการ dependency พร้อมคอมเมนต์แบ่งกลุ่ม: core (Django/DRF/JWT/CORS/spectacular),
database (psycopg 3 + dj-database-url), config (python-dotenv), realtime (channels/channels-redis/daphne),
async (celery/redis), และ `requests` สำหรับเรียก SMS gateway
ทุกตัวตรึงเป็นช่วง major version เพื่อไม่ให้อัปเดตข้ามรุ่นโดยไม่ตั้งใจ

**EN:** Dependencies grouped by purpose: core, database, config, realtime, async tasks, and
`requests` for the SMS gateway. All are pinned to a major-version range to avoid accidental jumps.

---

## `backend/Dockerfile` / `backend/.dockerignore`

**TH:** สร้าง image ของ backend (ติดตั้ง requirements แล้ววาง source) `.dockerignore` ตัด `.env`,
`__pycache__`, `dev.sqlite3` ออกจาก build context เพื่อไม่ให้ secret หลุดเข้า image 🔒

**EN:** Builds the backend image (install requirements, copy source). `.dockerignore` excludes
`.env`, `__pycache__`, and `dev.sqlite3` from the build context so secrets never enter the image. 🔒

---

## `backend/.env.example`

**TH:** เทมเพลตของ environment variable ทั้งหมดพร้อมคำอธิบาย — คัดลอกเป็น `.env` แล้วแก้ค่า
ครอบคลุม secret key, DEBUG, allowed hosts, `DATABASE_URL`, `REDIS_URL`, `FRONTEND_ORIGIN`,
อายุ JWT และ credential ของ SMS provider ทั้งสามเจ้า
**ไฟล์ `.env` จริงถูก `.gitignore` ไว้ ห้าม commit** 🔒

**EN:** The documented template of every environment variable — copy to `.env` and fill in.
Covers secret key, DEBUG, allowed hosts, `DATABASE_URL`, `REDIS_URL`, `FRONTEND_ORIGIN`, JWT
lifetimes, and credentials for all three SMS providers. The real `.env` is gitignored — never commit it. 🔒

---

## `docker-compose.yml` (ราก repo / repo root)

**TH:** ประกอบ 6 service: `db` (PostgreSQL 16 + healthcheck), `redis` (7 + healthcheck),
`backend` (migrate แล้วรัน daphne — ASGI เพื่อให้ WebSocket ทำงาน), `celery_worker`, `celery_beat`, `frontend`

**EN:** Six services: `db` (PostgreSQL 16 + healthcheck), `redis` (7 + healthcheck), `backend`
(migrate then run daphne so WebSocket works), `celery_worker`, `celery_beat`, and `frontend`.

**🔑 จุดที่คนพลาดบ่อย / Common gotcha:**
- `BACKEND_INTERNAL_URL: http://backend:8000` — ชื่อ service ใช้ได้เฉพาะ **ภายใน** docker network
  (Next เรียกจากฝั่ง server จึงใช้ได้)
  *Service names only resolve **inside** the docker network; Next calls it server-side, so it works.*
- `NEXT_PUBLIC_WS_URL: ws://localhost:8000` — ต้องเป็น localhost เพราะ **เบราว์เซอร์** เป็นคนต่อ ไม่ใช่ container
  *Must be localhost because the **browser** opens this connection, not the container.*
- `db` เปิดพอร์ต 5432 ออกมาที่เครื่อง จึงรัน `manage.py` บนเครื่องแล้วต่อ Postgres ของ Docker ได้
  *Port 5432 is published, so local `manage.py` can use the dockerised Postgres.*

---

## `.gitignore` (ราก repo / repo root)

**TH:** กัน `.env`, `dev.sqlite3`, `__pycache__`, `node_modules`, `.next` ไม่ให้เข้า git 🔒
**EN:** Keeps `.env`, `dev.sqlite3`, `__pycache__`, `node_modules`, `.next` out of git. 🔒
