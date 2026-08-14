"""
บทบาทผู้ใช้งานในระบบ (ทุก role คือเจ้าหน้าที่ภายในคลินิก — ไม่มี role ของลูกค้า)

เก็บไว้ใน `common` เพราะทั้ง accounts (นิยาม User) และ permission/mixin ส่วนกลาง
ต้องใช้ค่าเดียวกัน การรวมไว้ที่เดียวช่วยกันค่าไม่ตรงกันระหว่าง app
"""
from __future__ import annotations

from django.db import models


class UserRole(models.TextChoices):
    SUPER_ADMIN = "super_admin", "ผู้ดูแลระบบสูงสุด"
    ADMIN = "admin", "ผู้จัดการสาขา"
    STAFF = "staff", "เจ้าหน้าที่หน้าเคาน์เตอร์"
    DOCTOR = "doctor", "แพทย์"


#: role ที่มองเห็นข้อมูลได้ทุกสาขา
CROSS_BRANCH_ROLES: frozenset[str] = frozenset({UserRole.SUPER_ADMIN})

#: role ที่บริหารจัดการข้อมูลตั้งค่า (แพทย์/บริการ/ตาราง) ของสาขาได้
MANAGEMENT_ROLES: frozenset[str] = frozenset({UserRole.SUPER_ADMIN, UserRole.ADMIN})

#: role ที่ทำงานหน้างานกับคิวได้ (สร้าง/แก้ไขคิว)
QUEUE_OPERATION_ROLES: frozenset[str] = frozenset(
    {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.STAFF}
)
