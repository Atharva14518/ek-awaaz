from __future__ import annotations

import asyncio
import re
from collections import deque
from pathlib import Path
from time import monotonic
from typing import Any

import httpx

from .config import Settings


FORBIDDEN_EMERGENCY_NUMBERS = {"100", "101", "102", "108", "112"}


class BolnaSafetyError(RuntimeError):
    pass


class BolnaClient:
    """Current Bolna REST adapter with safety checks at the network boundary."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._attempts: deque[float] = deque()
        self._rate_lock = asyncio.Lock()

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.allow_real_actions
            and self.settings.bolna_api_key
            and self.settings.bolna_dispatch_agent_id
        )

    @staticmethod
    def _digits(phone: str) -> str:
        return re.sub(r"\D", "", phone)

    def _assert_safe_recipient(self, phone: str) -> None:
        digits = self._digits(phone)
        if not digits:
            raise BolnaSafetyError("No stand-in number is configured for this recipient")
        if digits in FORBIDDEN_EMERGENCY_NUMBERS or any(
            digits.endswith(number) and len(digits) <= len(number) + 2
            for number in FORBIDDEN_EMERGENCY_NUMBERS
        ):
            raise BolnaSafetyError("Emergency-service numbers are permanently blocked")
        allowed = {self._digits(number) for number in self.settings.contacts.values() if number}
        if digits not in allowed:
            raise BolnaSafetyError("Recipient is not one of the configured stand-in contacts")

    async def _take_rate_slot(self) -> None:
        async with self._rate_lock:
            now = monotonic()
            window = self.settings.outbound_rate_window_seconds
            while self._attempts and now - self._attempts[0] >= window:
                self._attempts.popleft()
            if len(self._attempts) >= self.settings.outbound_rate_limit:
                raise BolnaSafetyError("Outbound call rate limit reached")
            self._attempts.append(now)

    async def place_call(
        self,
        phone: str,
        script: str,
        session_id: str,
        target: str,
    ) -> dict[str, Any]:
        if not self.configured:
            raise BolnaSafetyError("Real calling is disabled or Bolna is not configured")
        self._assert_safe_recipient(phone)
        await self._take_rate_slot()
        payload: dict[str, Any] = {
            "agent_id": self.settings.bolna_dispatch_agent_id,
            "recipient_phone_number": phone,
            "user_data": {
                "session_id": session_id,
                "recipient_role": target,
                "dispatch_script": script,
                "demo_contact_only": True,
            },
        }
        if self.settings.bolna_from_phone_number:
            payload["from_phone_number"] = self.settings.bolna_from_phone_number
        return await self._request("POST", "/call", json=payload)

    async def get_execution(self, execution_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/executions/{execution_id}")

    async def create_listener_agent(self, prompt_path: Path, webhook_url: str) -> dict[str, Any]:
        if not self.settings.bolna_api_key:
            raise BolnaSafetyError("BOLNA_API_KEY is required")
        system_prompt = prompt_path.read_text(encoding="utf-8")
        payload = {
            "agent_config": {
                "agent_name": "Ek Awaaz Listener",
                "agent_welcome_message": "Ek Awaaz. Main sun raha hoon. Kya hua?",
                "webhook_url": webhook_url,
                "tasks": [{
                    "task_type": "conversation",
                    "toolchain": {
                        "execution": "sequential",
                        "pipelines": [["transcriber", "llm", "synthesizer"]],
                    },
                    "tools_config": {
                        "llm_agent": {
                            "agent_type": "simple_llm_agent",
                            "agent_flow_type": "streaming",
                            "llm_config": {
                                "provider": "groq",
                                "model": self.settings.groq_model,
                                "max_tokens": 120,
                                "temperature": 0.1,
                            },
                        },
                        "synthesizer": {
                            "provider": "polly",
                            "provider_config": {"voice": "Aditi", "engine": "neural"},
                            "stream": True,
                            "buffer_size": 200,
                            "audio_format": "wav",
                        },
                        "transcriber": {
                            "provider": "deepgram",
                            "model": "nova-3",
                            "language": "multi",
                            "stream": True,
                            "encoding": "linear16",
                            "sampling_rate": 16000,
                            "endpointing": 250,
                        },
                        "input": {"provider": "plivo", "format": "wav"},
                        "output": {"provider": "plivo", "format": "wav"},
                    },
                    "task_config": {
                        "call_terminate": 600,
                        "hangup_after_silence": 10,
                    },
                }],
            },
            "agent_prompts": {"task_1": {"system_prompt": system_prompt}},
        }
        return await self._request("POST", "/v2/agent", json=payload, expected_status=201)

    async def setup_inbound(self, agent_id: str, phone_number_id: str) -> dict[str, Any]:
        if not self.settings.bolna_api_key:
            raise BolnaSafetyError("BOLNA_API_KEY is required")
        return await self._request(
            "POST",
            "/inbound/setup",
            json={"agent_id": agent_id, "phone_number_id": phone_number_id},
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {self.settings.bolna_api_key}"}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.request(
                method,
                f"{self.settings.bolna_base_url}{path}",
                headers=headers,
                json=json,
            )
        if response.status_code != expected_status:
            raise RuntimeError(f"Bolna returned {response.status_code}: {response.text[:300]}")
        return response.json()

    async def stop_call(self, execution_id: str) -> None:
        # Bolna's current public docs do not document a single-execution stop
        # endpoint. Do not guess one. The local kill switch prevents new calls
        # and cancels pending work; configure provider-side termination if needed.
        _ = execution_id

