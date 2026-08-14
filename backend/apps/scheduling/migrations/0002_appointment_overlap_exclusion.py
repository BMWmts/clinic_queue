"""
กันคิวชนกันในระดับฐานข้อมูล (PostgreSQL)

ชั้นแอปพลิเคชันตรวจเวลาว่างและล็อกแถวแพทย์อยู่แล้ว (ดู AppointmentBookingService)
แต่ exclusion constraint นี้เป็นตาข่ายรองสุดท้าย: ต่อให้มีโค้ดใหม่ในอนาคต
เขียนคิวลงตารางโดยข้าม service layer ฐานข้อมูลก็จะปฏิเสธคิวที่ซ้อนทับกันเอง

เงื่อนไข: นับเฉพาะคิวที่ยังกินเวลาจริง (ยกเลิก/ไม่มาตามนัด ไม่ถือว่าจองเวลาอยู่)
และเฉพาะคิวที่มีแพทย์ ส่วนบริการที่ไม่ใช้แพทย์ถูกจำกัดด้วยเพดานจำนวนเคสของสาขา
ซึ่งเป็นกฎเชิงจำนวน จึงตรวจที่ชั้นแอปพลิเคชันแทน

migration นี้ข้ามการทำงานบนฐานข้อมูลที่ไม่ใช่ PostgreSQL (เช่น sqlite ตอนรันเทสต์)
"""
from django.db import migrations

from apps.common.db_operations import PostgresOnlySQL

OCCUPYING_STATUSES_SQL = "'booked', 'confirmed', 'checked_in', 'in_progress', 'completed'"

CREATE_CONSTRAINT_SQL = f"""
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE scheduling_appointment
    ADD CONSTRAINT appointment_no_overlap_per_doctor
    EXCLUDE USING gist (
        doctor_id WITH =,
        tstzrange(scheduled_start, scheduled_end, '[)') WITH &&
    )
    WHERE (doctor_id IS NOT NULL AND status IN ({OCCUPYING_STATUSES_SQL}));
"""

DROP_CONSTRAINT_SQL = """
ALTER TABLE scheduling_appointment
    DROP CONSTRAINT IF EXISTS appointment_no_overlap_per_doctor;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("scheduling", "0001_initial"),
    ]

    operations = [
        PostgresOnlySQL(sql=CREATE_CONSTRAINT_SQL, reverse_sql=DROP_CONSTRAINT_SQL),
    ]
