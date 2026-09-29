# DB — ข้อมูลทดสอบชุดเดียวกับเครื่องผู้พัฒนา / Shared test database

`clinic.sql` คือ dump ของฐานข้อมูล `clinic` (PostgreSQL 18, format: plain SQL) ที่มีบัญชีผู้ใช้และข้อมูล
สำหรับทดสอบการใช้งาน ใช้เมื่อต้องการข้อมูล **ชุดเดียวกันเป๊ะ ๆ** กับเครื่องผู้พัฒนา

ถ้าแค่ต้องการระบบที่รันได้ ใช้ `python manage.py seed_dev_data` แทน (ดู [README หลัก](../README.md))

> ⚠️ เป็น **ข้อมูลทดสอบเท่านั้น** ห้ามใช้ไฟล์นี้กับ production และห้ามใส่ข้อมูลคนไข้จริงแล้ว commit ไฟล์นี้

## มีอะไรอยู่ข้างใน

| ข้อมูล | จำนวน |
|---|---|
| สาขา | 2 |
| บัญชีผู้ใช้ | 9 (Super Admin, Admin, Staff, Doctor) |
| คนไข้ | 5 |
| นัดหมาย | 5 |

รวมโครงสร้างครบ: ทุกตาราง, extension (`btree_gist`, `pg_trgm`), exclusion constraint กันคิวชน, index
และประวัติ migration (`django_migrations`) — **ไม่ต้องรัน `migrate` หลังกู้คืน**

**ไม่ได้รวม:** JWT refresh token และ session (ทุกคนต้อง login ใหม่หลังกู้คืน)

บัญชีทดสอบ: ดู [README หลัก หัวข้อ 4](../README.md#4-บัญชีทดสอบ-หลังรัน-seed_dev_data) —
บัญชีที่สร้างเพิ่มนอกเหนือจาก seed ให้สอบถามรหัสผ่านจากเจ้าของโปรเจกต์

## วิธีกู้คืน / How to restore

**สำคัญ:** ต้องกู้ลงฐานข้อมูลที่ **ว่างเปล่า** และ **ห้ามรัน `migrate` ก่อน**
(ไฟล์นี้สร้างตารางเอง ถ้ามีตารางอยู่แล้วจะ error `already exists`)

### แบบ Docker

```bash
cp backend/.env.example backend/.env
docker compose up -d db
docker compose exec -T db psql -U clinic -d clinic -v ON_ERROR_STOP=1 < DB/clinic.sql
docker compose up --build
```

### แบบ PostgreSQL ในเครื่อง (ต้องเป็นเวอร์ชัน 16 ขึ้นไป)

1. สร้างผู้ใช้ `clinic` (รหัสผ่าน `clinic`) และฐานข้อมูลเปล่าชื่อ `clinic` ที่ owner เป็น `clinic`
   (ใน pgAdmin: Login/Group Roles → Create, แล้ว Databases → Create)
2. กู้คืน:

```bash
psql --dbname="postgres://clinic:clinic@127.0.0.1:5432/clinic" -v ON_ERROR_STOP=1 --file=DB/clinic.sql
```

3. ตั้ง `DATABASE_URL=postgres://clinic:clinic@127.0.0.1:5432/clinic` ใน `backend/.env` แล้วรัน backend ตามปกติ

> **ผ่าน pgAdmin:** คลิกขวาที่ database `clinic` (ที่ว่าง) → **Query Tool** → เปิดไฟล์ `clinic.sql` → Execute
> (ไฟล์ plain SQL ใช้เมนู Restore... ไม่ได้ — เมนูนั้นรับเฉพาะ format Custom/Tar)

### กู้ทับฐานข้อมูลเดิม

ลบแล้วสร้างใหม่ก่อน (ข้อมูลเดิมจะหายทั้งหมด):

```bash
psql --dbname="postgres://clinic:clinic@127.0.0.1:5432/postgres" -c "DROP DATABASE clinic" -c "CREATE DATABASE clinic"
```

แบบ Docker (หยุด backend ก่อน เพราะ DROP ไม่ได้ถ้ายังมี connection ค้าง):

```bash
docker compose stop backend celery_worker celery_beat
docker compose exec db psql -U clinic -d postgres -c "DROP DATABASE clinic" -c "CREATE DATABASE clinic"
```

## วิธีอัปเดตไฟล์นี้ / Regenerating the dump

เมื่อแก้ข้อมูลทดสอบแล้วอยากให้คนอื่นได้ชุดใหม่ รันจากรากโปรเจกต์ (Git Bash):

```bash
PG_DUMP="/c/Program Files/PostgreSQL/18/bin/pg_dump.exe" bash DB/export_db.sh
```

[`export_db.sh`](export_db.sh) ทำให้ไฟล์กู้คืนได้ทุกทาง:
- ข้อมูลเป็น `INSERT` ธรรมดา → รันใน pgAdmin Query Tool ได้ (Query Tool รัน `COPY ... FROM stdin` ไม่ได้)
- ตัด `SET transaction_timeout` (มีเฉพาะ v17+) และ `\restrict` (คำสั่งเฉพาะ psql) → ใช้กับ PostgreSQL 16 ใน Docker ได้
- `--no-owner --no-privileges` → กู้คืนได้แม้ชื่อผู้ใช้ PostgreSQL ของอีกเครื่องไม่ตรงกัน
- ไม่แจก JWT token / session ที่ใช้ login อยู่

> **ไม่แนะนำให้ export ผ่าน pgAdmin:**
> - เมนู **Backup Server** เรียก `pg_dumpall` ต้องใช้สิทธิ์ superuser — ถ้าตั้ง Role เป็น `clinic` จะ error
>   `permission denied for table pg_authid`
> - เมนู **Backup...** ของ database ใช้ได้ แต่ได้ไฟล์ที่มี `COPY ... FROM stdin` และ `\restrict`
>   ซึ่งกู้คืนผ่าน Query Tool หรือบน PostgreSQL 16 ไม่ได้ — ใช้ `export_db.sh` แทน
