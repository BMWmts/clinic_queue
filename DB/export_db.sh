#!/usr/bin/env bash
# สร้าง DB/clinic.sql จากฐานข้อมูล clinic ในเครื่อง ให้กู้คืนได้ทั้ง psql และ pgAdmin Query Tool
# บน PostgreSQL 16 ขึ้นไป — รันจากรากโปรเจกต์:  bash DB/export_db.sh
#
# ทำไมต้องมีสคริปต์ แทนที่จะสั่ง pg_dump ตรง ๆ:
#   --column-inserts      ข้อมูลเป็น INSERT ปกติ (pgAdmin Query Tool รัน COPY ... FROM stdin ไม่ได้)
#   --no-owner/privileges กู้คืนได้แม้ชื่อผู้ใช้ PostgreSQL ของอีกเครื่องไม่ตรงกัน
#   --exclude-table-data  ไม่แจก JWT token/session ที่ใช้ login อยู่
#   sed                   ตัดคำสั่งที่ PostgreSQL 16 / pgAdmin ไม่รู้จัก
#                         (SET transaction_timeout มีตั้งแต่ v17, \restrict เป็นคำสั่งเฉพาะ psql)
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-postgres://clinic:clinic@127.0.0.1:5432/clinic}"
OUTPUT_FILE="${1:-DB/clinic.sql}"
PG_DUMP="${PG_DUMP:-pg_dump}"

"$PG_DUMP" --dbname="$DATABASE_URL" \
    --format=plain --column-inserts --no-owner --no-privileges --encoding=UTF8 \
    --exclude-table-data=token_blacklist_outstandingtoken \
    --exclude-table-data=token_blacklist_blacklistedtoken \
    --exclude-table-data=django_session \
  | sed -e '/^SET transaction_timeout = /d' \
        -e '/^\\restrict /d' \
        -e '/^\\unrestrict /d' \
  > "$OUTPUT_FILE"

echo "เขียน $OUTPUT_FILE แล้ว ($(wc -c < "$OUTPUT_FILE") bytes)"
