from __future__ import annotations

import re
from typing import Any

import httpx

from .bolna_client import FORBIDDEN_EMERGENCY_NUMBERS, BolnaSafetyError
from .config import Settings


class SMSClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def is_mock(self) -> bool:
        return self.settings.sms_provider != "twilio" or not self.settings.allow_real_actions

    async def send(self, to: str, body: str) -> dict[str, Any]:
        if self.is_mock:
            return {"id": "mock-sms", "status": "done", "simulated": True}
        digits = re.sub(r"\D", "", to)
        if not digits or digits in FORBIDDEN_EMERGENCY_NUMBERS:
            raise BolnaSafetyError("SMS recipient is missing or blocked")
        if digits != re.sub(r"\D", "", self.settings.sms_demo_number):
            raise BolnaSafetyError("SMS may only go to SMS_DEMO_NUMBER")
        if not all([
            self.settings.twilio_account_sid,
            self.settings.twilio_auth_token,
            self.settings.twilio_from_number,
        ]):
            raise RuntimeError("Twilio credentials are incomplete")
        url = (
            "https://api.twilio.com/2010-04-01/Accounts/"
            f"{self.settings.twilio_account_sid}/Messages.json"
        )
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                url,
                data={"To": to, "From": self.settings.twilio_from_number, "Body": body},
                auth=(self.settings.twilio_account_sid, self.settings.twilio_auth_token),
            )
        response.raise_for_status()
        data = response.json()
        return {"id": data.get("sid"), "status": data.get("status", "queued"), "simulated": False}

