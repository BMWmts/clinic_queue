"""
ตัวเชื่อมต่อ SMS Gateway

ออกแบบเป็น class ตามหลัก OOP: มี interface กลาง (`BaseSmsProvider`) แล้วแต่ละ
ผู้ให้บริการสืบทอดไปทำจริง การเพิ่มเจ้าใหม่จึงทำได้โดยเขียน class เดียว
ไม่ต้องแก้โค้ดส่วนอื่นของระบบ

credential ทั้งหมดอ่านจาก environment variable เท่านั้น (ห้าม hardcode/เก็บใน DB)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

import requests
from django.conf import settings

from apps.clinics.models import Clinic, SmsProvider

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class SmsSendResult:
    """ผลการส่งข้อความหนึ่งครั้ง"""

    success: bool
    provider: str
    provider_message_id: str = ""
    error_message: str = ""


class SmsConfigurationError(Exception):
    """ตั้งค่า provider ไม่ครบ (เช่น ไม่ได้ใส่ API key ใน environment)"""


class BaseSmsProvider(ABC):
    """interface กลางของผู้ให้บริการ SMS ทุกเจ้า"""

    name: str = "base"

    @abstractmethod
    def send(self, phone: str, message: str) -> SmsSendResult:
        """ส่งข้อความไปยังเบอร์ปลายทาง — ห้าม log เบอร์เต็มหรือเนื้อหาที่มีข้อมูลคนไข้"""

    @staticmethod
    def _mask(phone: str) -> str:
        return f"{phone[:3]}xxx{phone[-3:]}" if len(phone) >= 6 else "***"


class ConsoleSmsProvider(BaseSmsProvider):
    """
    provider สำหรับ dev — เขียนลง log แทนการส่งจริง

    ไม่ใช่ mock data ของระบบ (ไม่ได้ปลอมข้อมูลใน DB) แต่เป็นช่องทางส่งแบบไม่มีค่าใช้จ่าย
    ระหว่างพัฒนา และต้องเปลี่ยนเป็น provider จริงผ่าน env ก่อนขึ้น production
    """

    name = SmsProvider.CONSOLE

    def send(self, phone: str, message: str) -> SmsSendResult:
        logger.info("[SMS/console] ส่งข้อความถึง %s (%s ตัวอักษร)", self._mask(phone), len(message))
        return SmsSendResult(success=True, provider=self.name, provider_message_id="console")


class ThaiBulkSmsProvider(BaseSmsProvider):
    """ผู้ให้บริการในประเทศไทย — ใช้ HTTP API แบบ basic auth"""

    name = SmsProvider.THAIBULKSMS
    API_URL = "https://api-v2.thaibulksms.com/sms"

    def __init__(self, sender_name: str = "") -> None:
        self.api_key = settings.THAIBULKSMS_API_KEY
        self.api_secret = settings.THAIBULKSMS_API_SECRET
        self.sender_name = sender_name
        if not (self.api_key and self.api_secret):
            raise SmsConfigurationError(
                "ยังไม่ได้ตั้งค่า THAIBULKSMS_API_KEY / THAIBULKSMS_API_SECRET"
            )

    def send(self, phone: str, message: str) -> SmsSendResult:
        payload = {"msisdn": phone, "message": message, "sender": self.sender_name or "Clinic"}
        try:
            response = requests.post(
                self.API_URL,
                data=payload,
                auth=(self.api_key, self.api_secret),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            body = response.json()
            return SmsSendResult(
                success=True,
                provider=self.name,
                provider_message_id=str(body.get("id", "")),
            )
        except requests.RequestException as exc:
            logger.warning("ส่ง SMS ผ่าน ThaiBulkSMS ไม่สำเร็จถึง %s", self._mask(phone))
            return SmsSendResult(success=False, provider=self.name, error_message=str(exc))


class TwilioSmsProvider(BaseSmsProvider):
    """Twilio — ใช้ REST API โดยตรงเพื่อไม่ต้องเพิ่ม SDK"""

    name = SmsProvider.TWILIO
    API_URL_TEMPLATE = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"

    def __init__(self) -> None:
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_FROM_NUMBER
        if not (self.account_sid and self.auth_token and self.from_number):
            raise SmsConfigurationError("ยังไม่ได้ตั้งค่า credential ของ Twilio ครบถ้วน")

    def send(self, phone: str, message: str) -> SmsSendResult:
        try:
            response = requests.post(
                self.API_URL_TEMPLATE.format(sid=self.account_sid),
                data={"To": self._to_e164(phone), "From": self.from_number, "Body": message},
                auth=(self.account_sid, self.auth_token),
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return SmsSendResult(
                success=True,
                provider=self.name,
                provider_message_id=str(response.json().get("sid", "")),
            )
        except requests.RequestException as exc:
            logger.warning("ส่ง SMS ผ่าน Twilio ไม่สำเร็จถึง %s", self._mask(phone))
            return SmsSendResult(success=False, provider=self.name, error_message=str(exc))

    @staticmethod
    def _to_e164(phone: str) -> str:
        """แปลงเบอร์ไทย 0xxxxxxxxx เป็นรูปแบบสากล +66xxxxxxxxx"""
        return f"+66{phone[1:]}" if phone.startswith("0") else phone


class SmsProviderFactory:
    """เลือก provider ตามการตั้งค่าของสาขา (fallback เป็นค่าเริ่มต้นของระบบ)"""

    _REGISTRY: dict[str, type[BaseSmsProvider]] = {
        SmsProvider.CONSOLE: ConsoleSmsProvider,
        SmsProvider.THAIBULKSMS: ThaiBulkSmsProvider,
        SmsProvider.TWILIO: TwilioSmsProvider,
    }

    @classmethod
    def for_clinic(cls, clinic: Clinic) -> BaseSmsProvider:
        provider_key = clinic.sms_provider
        if provider_key == SmsProvider.DEFAULT:
            provider_key = settings.SMS_PROVIDER

        provider_class = cls._REGISTRY.get(provider_key)
        if provider_class is None:
            raise SmsConfigurationError(f"ไม่รู้จักผู้ให้บริการ SMS: {provider_key}")

        if provider_class is ThaiBulkSmsProvider:
            return ThaiBulkSmsProvider(sender_name=clinic.sms_sender_name)
        return provider_class()
