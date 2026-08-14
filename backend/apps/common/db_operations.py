"""
Migration operation ที่ทำงานเฉพาะบน PostgreSQL

ระบบจริงใช้ PostgreSQL เสมอ และเราต้องการ constraint ระดับฐานข้อมูล
(exclusion constraint กันคิวชน, extension สำหรับค้นหาชื่อคนไข้)
แต่ระหว่าง dev/CI บางเครื่องรัน sqlite เพื่อทดสอบ logic ล้วน ๆ
operation นี้จึงข้ามการทำงานไปเงียบ ๆ เมื่อไม่ได้อยู่บน PostgreSQL
(การกันคิวชนระดับ application layer ยังทำงานครบทุกกรณีอยู่แล้ว)
"""
from __future__ import annotations

from typing import Any

from django.db import migrations


class PostgresOnlySQL(migrations.RunSQL):
    """RunSQL ที่ทำงานเฉพาะเมื่อ backend เป็น PostgreSQL"""

    def database_forwards(self, app_label: str, schema_editor: Any, from_state: Any, to_state: Any) -> None:
        if schema_editor.connection.vendor != "postgresql":
            return
        super().database_forwards(app_label, schema_editor, from_state, to_state)

    def database_backwards(self, app_label: str, schema_editor: Any, from_state: Any, to_state: Any) -> None:
        if schema_editor.connection.vendor != "postgresql":
            return
        super().database_backwards(app_label, schema_editor, from_state, to_state)
