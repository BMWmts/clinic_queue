"""
ผู้ใช้งานระบบ — เจ้าหน้าที่ภายในคลินิกเท่านั้น (ไม่มีบัญชีของลูกค้า/คนไข้)

ใช้ email เป็น username เพราะคลินิกออกบัญชีให้พนักงานเป็นรายบุคคล
และผูกทุกบัญชีกับ "สาขา" เพื่อให้ระบบ scope ข้อมูลตามสาขาได้ตั้งแต่ระดับ auth
"""
from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.common.roles import CROSS_BRANCH_ROLES, MANAGEMENT_ROLES, UserRole

phone_validator = RegexValidator(
    regex=r"^0\d{8,9}$",
    message="เบอร์โทรต้องเป็นตัวเลข 9-10 หลักและขึ้นต้นด้วย 0 (เช่น 0812345678)",
)


class UserManager(BaseUserManager):
    """Manager ที่บังคับให้ทุกบัญชีมี email และเข้ารหัสรหัสผ่านเสมอ"""

    use_in_migrations = True

    def create_user(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        if not email:
            raise ValueError("ต้องระบุอีเมลสำหรับบัญชีผู้ใช้")

        email = self.normalize_email(email).lower()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.full_clean(exclude=["password"])
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str | None = None, **extra_fields: Any) -> "User":
        extra_fields.setdefault("role", UserRole.SUPER_ADMIN)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("full_name", "Super Admin")

        if extra_fields["role"] != UserRole.SUPER_ADMIN:
            raise ValueError("บัญชี superuser ต้องมี role เป็น super_admin")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """บัญชีเจ้าหน้าที่ในระบบ"""

    Role = UserRole

    email = models.EmailField("อีเมล", unique=True, db_index=True)
    full_name = models.CharField("ชื่อ-สกุล", max_length=150)
    phone = models.CharField(
        "เบอร์โทร", max_length=10, blank=True, validators=[phone_validator]
    )
    role = models.CharField(
        "บทบาท", max_length=20, choices=UserRole.choices, default=UserRole.STAFF, db_index=True
    )
    clinic = models.ForeignKey(
        "clinics.Clinic",
        verbose_name="สาขาที่สังกัด",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="users",
        help_text="Super Admin ปล่อยว่างได้ (ดูแลทุกสาขา) role อื่นต้องระบุสาขา",
    )

    is_active = models.BooleanField("เปิดใช้งาน", default=True)
    is_staff = models.BooleanField("เข้าหน้า Django admin ได้", default=False)
    date_joined = models.DateTimeField("เข้าร่วมเมื่อ", default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "ผู้ใช้งาน"
        verbose_name_plural = "ผู้ใช้งาน"
        ordering = ["full_name"]
        constraints = [
            # role ที่ไม่ใช่ super_admin ต้องสังกัดสาขาเสมอ มิฉะนั้น branch scoping
            # จะไม่มีความหมายและผู้ใช้จะไม่เห็นข้อมูลใดเลย
            models.CheckConstraint(
                condition=models.Q(role=UserRole.SUPER_ADMIN) | models.Q(clinic__isnull=False),
                name="user_non_super_admin_requires_clinic",
            )
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_role_display()})"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.email = self.email.lower().strip()
        super().save(*args, **kwargs)

    @property
    def can_access_all_branches(self) -> bool:
        """Super Admin เท่านั้นที่ query ข้ามสาขาได้"""
        return self.role in CROSS_BRANCH_ROLES

    @property
    def is_branch_manager(self) -> bool:
        """จัดการตารางแพทย์/บริการ/ผู้ใช้ในสาขาได้"""
        return self.role in MANAGEMENT_ROLES

    @property
    def is_doctor(self) -> bool:
        return self.role == UserRole.DOCTOR

    def can_access_clinic(self, clinic_id: int | None) -> bool:
        """ตรวจว่าผู้ใช้มีสิทธิ์แตะข้อมูลของสาขานี้หรือไม่"""
        if self.can_access_all_branches:
            return True
        return clinic_id is not None and clinic_id == self.clinic_id
