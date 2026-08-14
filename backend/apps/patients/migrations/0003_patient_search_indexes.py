"""
Index สำหรับค้นหาคนไข้ให้เร็วเมื่อข้อมูลเยอะ (PostgreSQL)

ค้นด้วยเบอร์โทร/รหัสคนไข้ใช้ B-tree index ที่ประกาศไว้ใน model อยู่แล้ว
ส่วนการค้นด้วย "ชื่อบางส่วน" (ILIKE '%คำค้น%') ใช้ index ปกติไม่ได้
จึงเพิ่ม trigram index ให้ตรงกับรูปแบบการค้นจริงของเจ้าหน้าที่หน้าเคาน์เตอร์

ข้ามการทำงานบนฐานข้อมูลที่ไม่ใช่ PostgreSQL
"""
from django.db import migrations

from apps.common.db_operations import PostgresOnlySQL

CREATE_TRIGRAM_INDEXES_SQL = """
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS patient_first_name_trgm_idx
    ON patients_patient USING gin (first_name gin_trgm_ops);

CREATE INDEX IF NOT EXISTS patient_last_name_trgm_idx
    ON patients_patient USING gin (last_name gin_trgm_ops);
"""

DROP_TRIGRAM_INDEXES_SQL = """
DROP INDEX IF EXISTS patient_first_name_trgm_idx;
DROP INDEX IF EXISTS patient_last_name_trgm_idx;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("patients", "0002_initial"),
    ]

    operations = [
        PostgresOnlySQL(
            sql=CREATE_TRIGRAM_INDEXES_SQL, reverse_sql=DROP_TRIGRAM_INDEXES_SQL
        ),
    ]
