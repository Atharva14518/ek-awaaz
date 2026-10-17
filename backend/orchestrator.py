from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable

from .bolna_client import BolnaClient
from .config import Settings
from .database import SessionStore
from .extraction import EntityExtractor, apply_extraction
from .graph import graph_preview, plan_actions
from .models import Action, GPS, StoredSession, StreamEvent, TranscriptItem
from .sms_client import SMSClient


Emit = Callable[[StreamEvent], Awaitable[None]]


class IncidentOrchestrator:
    def __init__(self, settings: Settings, store: SessionStore, emit: Emit):
        self.settings = settings
        self.store = store
        self.emit = emit
        self.extractor = EntityExtractor(settings)
        self.bolna = BolnaClient(settings)
        self.sms = SMSClient(settings)
        self._stopped: set[str] = set()

    async def process_transcript(
        self,
        session: StoredSession,
        speaker: str,
        text: str,
        *,
        simulated: bool,
    ) -> bool:
        result = await self.extractor.extract(text, session.incident) if speaker == "caller" else None
        highlights = result.highlights if result else []
        item = TranscriptItem(speaker=speaker, text=text, highlights=highlights)
        session.incident.transcript.append(item)
        changed: set[str] = set()
        if result:
            changed = apply_extraction(session.incident, result)
        session.last_activity_at = item.ts
        if session.status == "idle":
            session.status = "listening"

        if result and result.corrected_fields:
            self._revise_pending_actions(session)
        self.store.save_session(session)
        await self.emit(StreamEvent(
            event="transcript.chunk",
            session_id=session.incident.session_id,
            ts=item.ts,
            data={
                "chunk": item.model_dump(mode="json"),
                "simulated": simulated,
                "extraction": "groq+rules" if result and result.used_groq else "rules",
            },
        ))
        if changed:
            await self.emit(StreamEvent(
                event="incident.updated",
                session_id=session.incident.session_id,
                data={
                    "incident": session.incident.model_dump(mode="json"),
                    "changed": sorted(changed),
                    "simulated": simulated,
                },
            ))

        preview = graph_preview(session.incident)
        if preview.get("confirmation_required") and session.status != "awaiting_confirmation":
            session.status = "awaiting_confirmation"
            self.store.save_session(session)
            await self.emit(StreamEvent(
                event="confirmation.required",
                session_id=session.incident.session_id,
                data={
                    "type": session.incident.type,
                    "location": session.incident.location.text,
                    "silent_mode": session.incident.silent_mode,
                },
            ))
        return bool(session.incident.dispatch_confirmed and not session.incident.actions)

    async def dispatch(self, session: StoredSession, *, simulated: bool) -> None:
        session_id = session.incident.session_id
        if session_id in self._stopped:
            return
        if not session.incident.dispatch_confirmed:
            raise ValueError("Caller confirmation is required before dispatch")
        preview = graph_preview(session.incident)
        if not preview.get("complete"):
            raise ValueError("Incident type and a medium-confidence location are required")
        if session.incident.actions:
            return

        session.status = "dispatching"
        actions = plan_actions(session.incident)
        for action in actions:
            action.simulated = simulated or not self.settings.allow_real_actions
        session.incident.actions.extend(actions)
        session.last_activity_at = datetime.now(timezone.utc)
        self.store.save_session(session)
        await self.emit(StreamEvent(
            event="dispatch.started",
            session_id=session_id,
            data={"incident": session.incident.model_dump(mode="json"), "simulated": simulated},
        ))

        await asyncio.gather(*(self._execute_action(session, action, simulated) for action in actions))
        if session_id in self._stopped:
            return
        session.status = "complete"
        session.ended_at = datetime.now(timezone.utc)
        session.last_activity_at = session.ended_at
        self.store.save_session(session)
        await self.emit(StreamEvent(
            event="session.completed",
            session_id=session_id,
            data={"incident": session.incident.model_dump(mode="json"), "simulated": simulated},
        ))

    async def _execute_action(self, session: StoredSession, action: Action, simulated: bool) -> None:
        if action.kind == "sms":
            await self._execute_sms(session, action, simulated)
            return
        if simulated or not self.settings.allow_real_actions:
            for new_status in ["ringing", "connected", "done"]:
                if session.incident.session_id in self._stopped:
                    return
                await asyncio.sleep(0.18)
                action.status = new_status
                action.attempts = 1
                self.store.save_session(session)
                await self._emit_action(session, action)
            return

        phone = self.settings.contacts.get(action.target, "")
        last_error = ""
        for attempt in range(1, 3):
            if session.incident.session_id in self._stopped:
                return
            action.attempts = attempt
            try:
                response = await self.bolna.place_call(
                    phone,
                    action.script_summary,
                    session.incident.session_id,
                    action.target,
                )
                action.external_id = response.get("execution_id")
                action.status = "queued"
                action.simulated = False
                self.store.save_session(session)
                await self._emit_action(session, action)
                return
            except Exception as exc:
                last_error = str(exc)
                await asyncio.sleep(0.25)
        action.status = "failed"
        action.script_summary = f"{action.script_summary} Failure: {last_error[:120]}"
        self.store.save_session(session)
        await self._emit_action(session, action)
        await self.emit(StreamEvent(
            event="listener.prompt",
            session_id=session.incident.session_id,
            data={"text": f"The call to {action.target} failed. Please tell the caller."},
        ))

    async def _execute_sms(self, session: StoredSession, action: Action, simulated: bool) -> None:
        try:
            result = await self.sms.send(self.settings.sms_demo_number, action.script_summary)
            action.external_id = result.get("id")
            action.status = "done"
            action.attempts = 1
            action.simulated = bool(result.get("simulated", simulated))
        except Exception as exc:
            action.status = "failed"
            action.attempts = 1
            action.script_summary = f"{action.script_summary} Failure: {str(exc)[:120]}"
        self.store.save_session(session)
        await self._emit_action(session, action)

    async def _emit_action(self, session: StoredSession, action: Action) -> None:
        await self.emit(StreamEvent(
            event="action.updated",
            session_id=session.incident.session_id,
            data={
                "action": action.model_dump(mode="json"),
                "incident": session.incident.model_dump(mode="json"),
            },
        ))

    def _revise_pending_actions(self, session: StoredSession) -> None:
        revised = {item.target: item.script_summary for item in plan_actions(session.incident)}
        for action in session.incident.actions:
            if action.status in {"queued", "ringing"} and action.target in revised:
                action.script_summary = revised[action.target]

    async def set_confirmation(
        self,
        session: StoredSession,
        confirmed: bool,
        correction: str | None = None,
    ) -> bool:
        if correction:
            should_dispatch = await self.process_transcript(
                session,
                "caller",
                correction,
                simulated=session.source == "simulator",
            )
            if not confirmed:
                return should_dispatch
        session.incident.dispatch_confirmed = confirmed
        session.incident.location.confirmed = confirmed
        session.status = "dispatching" if confirmed else "awaiting_confirmation"
        session.last_activity_at = datetime.now(timezone.utc)
        self.store.save_session(session)
        await self.emit(StreamEvent(
            event="incident.updated",
            session_id=session.incident.session_id,
            data={
                "incident": session.incident.model_dump(mode="json"),
                "changed": ["dispatch_confirmed", "location.confirmed"],
                "simulated": session.source == "simulator",
            },
        ))
        return confirmed and not session.incident.actions

    async def set_gps(self, session: StoredSession, lat: float, lng: float) -> None:
        session.incident.location.gps = GPS(lat=lat, lng=lng)
        session.incident.location.confidence = "high"
        session.last_activity_at = datetime.now(timezone.utc)
        self._revise_pending_actions(session)
        self.store.save_session(session)
        await self.emit(StreamEvent(
            event="incident.updated",
            session_id=session.incident.session_id,
            data={"incident": session.incident.model_dump(mode="json"), "changed": ["location.gps", "location.confidence"]},
        ))

    async def silence_check(self, session: StoredSession) -> None:
        if not session.silence_check_failed:
            session.silence_check_failed = True
            self.store.save_session(session)
            await self.emit(StreamEvent(
                event="listener.prompt",
                session_id=session.incident.session_id,
                data={"text": "Are you still there? Say yes or press 1.", "silent_mode": session.incident.silent_mode},
            ))
            return
        # The product brief asks for automatic high-severity dispatch, but the
        # hard rule requires confirmation before every real outbound call. Keep
        # the escalation visible without crossing that boundary.
        if session.incident.severity in {"high", "critical"} and not session.incident.dispatch_confirmed:
            note = Action(
                kind="note",
                target="Dispatcher",
                status="queued",
                script_summary="High-severity silence escalation: caller confirmation still required before external calls.",
                simulated=True,
            )
            session.incident.actions.append(note)
            self.store.save_session(session)
            await self._emit_action(session, note)

    async def stop(self, session: StoredSession) -> None:
        self._stopped.add(session.incident.session_id)
        session.status = "stopped"
        for action in session.incident.actions:
            if action.status in {"queued", "ringing"}:
                action.status = "failed"
        session.last_activity_at = datetime.now(timezone.utc)
        self.store.save_session(session)

