#!/usr/bin/env python
"""Django command-line utility for administrative tasks."""
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:  # pragma: no cover - environment guard
        raise ImportError(
            "Django ยังไม่ได้ติดตั้งในสภาพแวดล้อมนี้ "
            "ให้รัน `pip install -r requirements.txt` ก่อน"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
