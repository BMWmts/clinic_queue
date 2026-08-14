"""
Django settings สำหรับระบบจองคิวคลินิก (Clinic Queue Booking System)

ค่า config ทั้งหมดอ่านจาก environment variable เท่านั้น (ดู .env.example)
ห้าม hardcode secret ใด ๆ ลงในไฟล์นี้
"""
from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# โหลด .env จาก backend/.env ถ้ามี (บน production ใช้ env จริงของ container)
load_dotenv(BASE_DIR / ".env")


def get_env_bool(name: str, default: bool = False) -> bool:
    """อ่าน environment variable แบบ boolean ('1', 'true', 'yes' ถือว่า True)"""
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def get_env_list(name: str, default: str = "") -> list[str]:
    """อ่าน environment variable ที่คั่นด้วย comma เป็น list"""
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = get_env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    if not DEBUG:
        raise RuntimeError("ต้องตั้งค่า DJANGO_SECRET_KEY ก่อนรันแบบ production")
    # dev เท่านั้น: key ชั่วคราวเพื่อให้ `manage.py` ใช้งานได้โดยไม่ต้องตั้งค่า
    SECRET_KEY = "insecure-dev-key-do-not-use-in-production"

ALLOWED_HOSTS = get_env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

INSTALLED_APPS = [
    "daphne",  # ต้องมาก่อน staticfiles เพื่อให้ runserver เป็น ASGI (WebSocket)
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",  # ทำให้ logout ยกเลิก refresh token ได้จริง
    "corsheaders",
    "drf_spectacular",
    "channels",
    # local apps
    "apps.common",
    "apps.accounts",
    "apps.clinics",
    "apps.doctors",
    "apps.services",
    "apps.scheduling",
    "apps.queue",
    "apps.patients",
    "apps.reports",
    "apps.notifications",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---------------------------------------------------------------------------
# Database — PostgreSQL เป็นมาตรฐานของระบบ
# ---------------------------------------------------------------------------
# sqlite ใช้ได้เฉพาะกรณีรัน unit test/dev เครื่องที่ยังไม่มี PostgreSQL เท่านั้น
# (constraint ระดับ DB บางตัว เช่น exclusion constraint จะถูกข้ามบน sqlite)
# ค่าว่างถือว่า "ไม่ได้ตั้งค่า" เพื่อให้สั่ง `DATABASE_URL= python manage.py test`
# แล้วกลับไปใช้ sqlite ได้ แม้ใน .env จะชี้ไปโฮสต์ของ Docker (db:5432) อยู่
DATABASE_URL = os.getenv("DATABASE_URL", "").strip() or f"sqlite:///{BASE_DIR / 'dev.sqlite3'}"

DATABASES = {
    "default": dj_database_url.parse(DATABASE_URL, conn_max_age=600),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Time zone — เก็บ UTC ใน DB, แสดงผลเป็นเวลาไทย
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "th"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    # ทุก endpoint ต้อง login เสมอ เว้นแต่ระบุ AllowAny อย่างชัดเจน (เช่น login)
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "apps.common.pagination.DefaultPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.common.exceptions.api_exception_handler",
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        # rate limit กันการเดารหัสผ่านที่หน้า login
        "login": os.getenv("LOGIN_THROTTLE_RATE", "10/min"),
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_TOKEN_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_DAYS", "7"))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Clinic Queue Booking API",
    "DESCRIPTION": "ระบบจองคิวคลินิก (back-office) — REST API สำหรับเจ้าหน้าที่คลินิก",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
}

# ---------------------------------------------------------------------------
# CORS / CSRF — frontend เรียก API ข้าม origin พร้อม cookie
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = [FRONTEND_ORIGIN]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [FRONTEND_ORIGIN]

# ---------------------------------------------------------------------------
# Channels (realtime queue dashboard)
# ---------------------------------------------------------------------------
REDIS_URL = os.getenv("REDIS_URL", "")

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [REDIS_URL]},
        }
    }
else:
    # ไม่มี Redis (dev/test) — ใช้ in-memory layer, frontend ยัง fallback ไป polling ได้
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# ---------------------------------------------------------------------------
# Celery (SMS reminder)
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = REDIS_URL or "cache+memory://"
CELERY_TASK_ALWAYS_EAGER = not REDIS_URL  # dev/test: รัน task ทันทีแบบ synchronous
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

# ---------------------------------------------------------------------------
# SMS Gateway — credential อ่านจาก env เท่านั้น
# ---------------------------------------------------------------------------
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console")
SMS_REMINDER_HOURS_BEFORE = int(os.getenv("SMS_REMINDER_HOURS_BEFORE", "24"))
THAIBULKSMS_API_KEY = os.getenv("THAIBULKSMS_API_KEY", "")
THAIBULKSMS_API_SECRET = os.getenv("THAIBULKSMS_API_SECRET", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM_NUMBER = os.getenv("TWILIO_FROM_NUMBER", "")

# ---------------------------------------------------------------------------
# Security (production hardening)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = get_env_bool("SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

import sys  # noqa: E402  (ใช้เฉพาะการปรับค่าเวลารันเทสต์ด้านล่าง)

if "test" in sys.argv:
    # เทสต์ไม่ได้ทดสอบความแข็งแรงของการ hash รหัสผ่าน — ใช้ hasher เร็วเพื่อลดเวลารัน
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "standard"},
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING" if "test" in sys.argv else os.getenv("LOG_LEVEL", "INFO"),
    },
}
