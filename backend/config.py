from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    demo_mode: bool
    allow_real_actions: bool
    simulator_delay_seconds: float
    database_path: Path
    frontend_dist: Path
    groq_api_key: str
    groq_model: str
    bolna_api_key: str
    bolna_base_url: str
    bolna_listener_agent_id: str
    bolna_dispatch_agent_id: str
    bolna_from_phone_number: str
    bolna_inbound_phone_number_id: str
    bolna_webhook_secret: str
    ambulance_demo_number: str
    police_demo_number: str
    family_demo_number: str
    sms_demo_number: str
    sms_provider: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_from_number: str
    public_base_url: str
    outbound_rate_limit: int
    outbound_rate_window_seconds: int

    @property
    def contacts(self) -> dict[str, str]:
        return {
            "Ambulance (demo)": self.ambulance_demo_number,
            "Police (demo)": self.police_demo_number,
            "Family (demo)": self.family_demo_number,
        }


@lru_cache
def get_settings() -> Settings:
    demo_mode = _bool("DEMO_MODE", True)
    # Two separate switches are deliberate: a copied .env cannot enable calls
    # merely by turning demo mode off.
    allow_real_actions = _bool("ALLOW_REAL_ACTIONS", False) and not demo_mode
    return Settings(
        app_name="Ek Awaaz API",
        demo_mode=demo_mode,
        allow_real_actions=allow_real_actions,
        simulator_delay_seconds=float(os.getenv("SIMULATOR_DELAY_SECONDS", "0.55")),
        database_path=Path(os.getenv("DATABASE_PATH", ROOT / "data" / "ek_awaaz.db")),
        frontend_dist=ROOT / "frontend" / "dist",
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        bolna_api_key=os.getenv("BOLNA_API_KEY", ""),
        bolna_base_url=os.getenv("BOLNA_BASE_URL", "https://api.bolna.ai").rstrip("/"),
        bolna_listener_agent_id=os.getenv("BOLNA_LISTENER_AGENT_ID", ""),
        bolna_dispatch_agent_id=os.getenv("BOLNA_DISPATCH_AGENT_ID", ""),
        bolna_from_phone_number=os.getenv("BOLNA_FROM_PHONE_NUMBER", ""),
        bolna_inbound_phone_number_id=os.getenv("BOLNA_INBOUND_PHONE_NUMBER_ID", ""),
        bolna_webhook_secret=os.getenv("BOLNA_WEBHOOK_SECRET", ""),
        ambulance_demo_number=os.getenv("AMBULANCE_DEMO_NUMBER", ""),
        police_demo_number=os.getenv("POLICE_DEMO_NUMBER", ""),
        family_demo_number=os.getenv("FAMILY_DEMO_NUMBER", ""),
        sms_demo_number=os.getenv("SMS_DEMO_NUMBER", ""),
        sms_provider=os.getenv("SMS_PROVIDER", "mock").lower(),
        twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
        twilio_from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
        public_base_url=os.getenv("PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/"),
        outbound_rate_limit=int(os.getenv("OUTBOUND_RATE_LIMIT", "3")),
        outbound_rate_window_seconds=int(os.getenv("OUTBOUND_RATE_WINDOW_SECONDS", "60")),
    )

