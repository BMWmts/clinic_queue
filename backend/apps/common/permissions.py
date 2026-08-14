"""
Permission class ตาม role (ใช้ร่วมกันทุก app)

หลักการ: ประกาศ role ที่อนุญาตไว้ใน class attribute เดียว แล้วสืบทอดต่อ
เพื่อไม่ต้องเขียน logic ตรวจสิทธิ์ซ้ำในหลาย view
"""
from __future__ import annotations

from typing import Iterable

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.common.roles import MANAGEMENT_ROLES, QUEUE_OPERATION_ROLES, UserRole


class RoleBasedPermission(BasePermission):
    """
    Base class: อนุญาตเฉพาะ role ที่อยู่ใน `allowed_roles`

    ถ้ากำหนด `read_only_roles` ด้วย role กลุ่มนั้นจะเรียกได้เฉพาะ method อ่านข้อมูล
    """

    allowed_roles: Iterable[str] = ()
    read_only_roles: Iterable[str] = ()
    message = "บทบาทของคุณไม่มีสิทธิ์ใช้งานส่วนนี้"

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not (user and user.is_authenticated and user.is_active):
            return False

        if user.role in self.allowed_roles:
            return True

        return request.method in SAFE_METHODS and user.role in self.read_only_roles


class IsSuperAdmin(RoleBasedPermission):
    """เฉพาะผู้ดูแลระบบสูงสุด (จัดการข้ามสาขา)"""

    allowed_roles = (UserRole.SUPER_ADMIN,)


class IsBranchManager(RoleBasedPermission):
    """ผู้จัดการสาขาขึ้นไป — จัดการตารางแพทย์/บริการ/ผู้ใช้ในสาขา"""

    allowed_roles = tuple(MANAGEMENT_ROLES)


class IsBranchManagerOrReadOnly(RoleBasedPermission):
    """แก้ไขได้เฉพาะผู้จัดการสาขาขึ้นไป, role อื่นในคลินิกดูได้อย่างเดียว"""

    allowed_roles = tuple(MANAGEMENT_ROLES)
    read_only_roles = (UserRole.STAFF, UserRole.DOCTOR)


class CanOperateQueue(RoleBasedPermission):
    """
    เจ้าหน้าที่หน้าเคาน์เตอร์ขึ้นไป — สร้าง/เลื่อน/ยกเลิกคิวได้

    แพทย์อ่านคิวได้ แต่การเปลี่ยนสถานะคนไข้ของแพทย์ใช้ endpoint เฉพาะ
    ที่มี permission ของตัวเอง (ดู apps/queue/permissions.py)
    """

    allowed_roles = tuple(QUEUE_OPERATION_ROLES)
    read_only_roles = (UserRole.DOCTOR,)


class IsClinicMember(RoleBasedPermission):
    """ผู้ใช้ที่ login แล้วทุก role (ยังคง scope ข้อมูลด้วยสาขาเสมอ)"""

    allowed_roles = tuple(UserRole.values)
