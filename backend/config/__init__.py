"""Django project config package."""
from .celery import celery_app

__all__ = ["celery_app"]
