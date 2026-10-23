from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from .config import ROOT, get_settings
from .connections import ConnectionManager
from .database import SessionStore
from .models import (
    ConfirmationInput,
    DTMFInput,
    GPSInput,
    IncidentState,
    ReportSummary,
    SilentIncidentInput,
    StoredSession,
    StreamEvent,
    TranscriptItem,
    TranscriptInput,
)
from .orchestrator import IncidentOrchestrator
from .report import build_pdf
from .simulator import run_simulation


settings = get_settings()
store = SessionStore(settings.database_path)
connections = ConnectionManager()
simulation_tasks: dict[str, asyncio.Task] = {}
dispatch_tasks: dict[str, asyncio.Task] = {}
intake_tasks: dict[str, asyncio.Task] = {}


async def emit(event: StreamEvent) -> None:
    stored = store.append_event(event)
    await connections.broadcast(stored)


orchestrator = IncidentOrchestrator(settings, store, emit)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.initialize()
    yield
    for task in [*simulation_tasks.values(), *dispatch_tasks.values(), *intake_tasks.values()]:
        if not task.done():
            task.cancel()


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_session(session_id: str) -> StoredSession:
    session = store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


def schedule_dispatch(session: StoredSession, *, simulated: bool) -> asyncio.Task:
    session_id = session.incident.session_id
    running = dispatch_tasks.get(session_id)
    if running and not running.done():
        return running
    task = asyncio.create_task(orchestrator.dispatch(session, simulated=simulated))
    dispatch_tasks[session_id] = task
    return task


@app.get("/api/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "demo_mode": settings.demo_mode,
        "real_actions_enabled": settings.allow_real_actions,
        "groq_configured": bool(settings.groq_api_key),
        "bolna_configured": orchestrator.bolna.configured,
        "bolna_intake_configured": orchestrator.bolna.intake_configured,
    }


@app.get("/api/config")
async def public_config() -> dict[str, Any]:
    return {
        "demo_mode": settings.demo_mode,
        "real_actions_enabled": settings.allow_real_actions,
        "demo_phone_number": settings.bolna_from_phone_number,
        "listener_agent_configured": bool(settings.bolna_listener_agent_id),
        "live_call_ready": orchestrator.bolna.intake_configured,
        "live_dispatch_enabled": settings.live_dispatch_enabled,
        "services": {
            "groq": bool(settings.groq_api_key),
            "bolna": bool(settings.bolna_api_key),
            "sms": "mock" if orchestrator.sms.is_mock else "twilio",
        },
    }


@app.post("/api/sessions", response_model=StoredSession, status_code=status.HTTP_201_CREATED)
async def create_session(source: str = Query(default="simulator", pattern="^(simulator|bolna|manual)$")) -> StoredSession:
    session = StoredSession(
        incident=IncidentState(),
        demo_mode=not settings.allow_real_actions or source == "simulator",
        source=source,
    )
    store.create_session(session)
    await emit(StreamEvent(
        event="session.created",
        session_id=session.incident.session_id,
        data={"demo_mode": session.demo_mode, "real_actions_enabled": settings.allow_real_actions},
    ))
    return session


@app.get("/api/sessions/{session_id}", response_model=StoredSession)
async def get_session(session_id: str) -> StoredSession:
    return require_session(session_id)


@app.delete("/api/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_session(session_id: str) -> None:
    session = store.get_session(session_id)
    if session and session.incident.evidence.file_name:
        evidence_path = settings.database_path.parent / "evidence" / session.incident.evidence.file_name
        if evidence_path.exists():
            evidence_path.unlink()
    for registry in [simulation_tasks, dispatch_tasks, intake_tasks]:
        task = registry.pop(session_id, None)
        if task and not task.done():
            task.cancel()
    if not store.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")


@app.post("/api/sessions/{session_id}/simulate", status_code=status.HTTP_202_ACCEPTED)
async def start_simulation(
    session_id: str,
    scenario: str = Query(default="accident", pattern="^(accident|silent)$"),
) -> dict[str, Any]:
    session = require_session(session_id)
    running = simulation_tasks.get(session_id)
    if running and not running.done():
        raise HTTPException(status_code=409, detail="Simulation already running")
    if session.status != "idle":
        raise HTTPException(status_code=409, detail="Session has already been used")
    session.status = "listening"
    session.source = "simulator"
    session.demo_mode = True
    store.save_session(session)

    async def process(current: StoredSession, speaker: str, text: str) -> bool:
        return await orchestrator.process_transcript(current, speaker, text, simulated=True)

    async def dispatch(current: StoredSession) -> None:
        await orchestrator.dispatch(current, simulated=True)

    task = asyncio.create_task(run_simulation(
        session,
        settings.simulator_delay_seconds,
        emit,
        process,
        dispatch,
        scenario,
    ))
    simulation_tasks[session_id] = task
    return {"session_id": session_id, "status": "listening", "simulated": True, "scenario": scenario}


@app.post("/api/sessions/{session_id}/live-call", status_code=status.HTTP_202_ACCEPTED)
async def start_live_call(
    session_id: str,
    confirm: bool = Body(embed=True),
) -> dict[str, Any]:
    """Ring one preconfigured stand-in number with the Bolna Listener agent."""
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    session = require_session(session_id)
    if session.status != "idle":
        raise HTTPException(status_code=409, detail="Session has already been used")
    if not orchestrator.bolna.intake_configured:
        raise HTTPException(
            status_code=503,
            detail="Live call needs both safety switches, a Bolna key, Listener agent ID, and LIVE_DEMO_CALLER_NUMBER",
        )

    try:
        result = await orchestrator.bolna.place_intake_call(session_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Bolna could not start the call: {str(exc)[:220]}") from exc
    execution_id = str(result.get("execution_id") or result.get("id") or "")
    if not execution_id:
        raise HTTPException(status_code=502, detail="Bolna did not return an execution ID")

    session.source = "bolna"
    session.demo_mode = not settings.live_dispatch_enabled
    session.status = "listening"
    session.bolna_execution_id = execution_id
    session.last_activity_at = datetime.now(timezone.utc)
    store.save_session(session)
    await emit(StreamEvent(
        event="listener.prompt",
        session_id=session_id,
        data={
            "text": "Live Bolna intake call queued. Answer the configured stand-in phone.",
            "live_call": True,
            "execution_id": execution_id,
        },
    ))
    intake_tasks[session_id] = asyncio.create_task(_poll_intake_call(session_id, execution_id))
    return {
        "session_id": session_id,
        "status": str(result.get("status") or "queued"),
        "execution_id": execution_id,
        "live": True,
        "downstream_actions_simulated": session.demo_mode,
    }


@app.post("/api/sessions/{session_id}/transcript", response_model=StoredSession)
async def ingest_transcript(session_id: str, body: TranscriptInput) -> StoredSession:
    session = require_session(session_id)
    should_dispatch = await orchestrator.process_transcript(
        session,
        body.speaker,
        body.text,
        simulated=body.source == "simulator" or session.demo_mode,
    )
    if should_dispatch:
        schedule_dispatch(session, simulated=session.demo_mode)
    return session


@app.post("/api/sessions/{session_id}/confirm", response_model=StoredSession)
async def confirm_dispatch(session_id: str, body: ConfirmationInput) -> StoredSession:
    session = require_session(session_id)
    should_dispatch = await orchestrator.set_confirmation(session, body.confirmed, body.correction)
    if should_dispatch:
        schedule_dispatch(session, simulated=session.demo_mode)
    return session


@app.post("/api/sessions/{session_id}/dtmf", response_model=StoredSession)
async def handle_dtmf(session_id: str, body: DTMFInput) -> StoredSession:
    session = require_session(session_id)
    if not session.incident.silent_mode:
        raise HTTPException(status_code=409, detail="DTMF is only accepted in silent mode")
    text = "Yes, correct." if body.digit == "1" else "No, correction needed."
    should_dispatch = await orchestrator.process_transcript(session, "caller", text, simulated=session.demo_mode)
    if should_dispatch:
        schedule_dispatch(session, simulated=session.demo_mode)
    return session


@app.post("/api/sessions/{session_id}/location", response_model=StoredSession)
async def share_location(session_id: str, body: GPSInput) -> StoredSession:
    session = require_session(session_id)
    await orchestrator.set_gps(session, body.lat, body.lng)
    return session


@app.post("/api/sessions/{session_id}/silent-intake", response_model=StoredSession)
async def submit_silent_intake(session_id: str, body: SilentIncidentInput) -> StoredSession:
    """Submit a confirmed, structured incident without requiring speech."""
    session = require_session(session_id)
    if session.status != "idle":
        raise HTTPException(status_code=409, detail="Session has already been used")
    if not body.address_confirmed:
        raise HTTPException(status_code=400, detail="The location must be confirmed before proceeding")
    if (body.lat is None) != (body.lng is None):
        raise HTTPException(status_code=400, detail="Latitude and longitude must be provided together")

    incident = session.incident
    incident.type = body.incident_type
    incident.location.text = body.address.strip()
    incident.location.confidence = "high" if body.lat is not None else "medium"
    incident.location.confirmed = True
    if body.lat is not None and body.lng is not None:
        incident.location.gps = {"lat": body.lat, "lng": body.lng}
    incident.people.count = body.people
    incident.people.injured = body.injured
    incident.people.conscious = body.conscious
    incident.severity = body.severity
    incident.caller_safe = "unknown"
    incident.silent_mode = True
    incident.dispatch_confirmed = True
    incident.evidence.motion_detected = body.motion_detected
    incident.evidence.motion_peak = body.motion_peak
    incident.evidence.video_captured = body.video_captured
    incident.evidence.video_duration_seconds = body.video_duration_seconds
    incident.evidence.captured_at = datetime.now(timezone.utc) if body.video_captured else None

    summary = (
        f"Silent incident form: {body.incident_type.replace('_', ' ')} at {body.address.strip()}. "
        f"People: {body.people}; injured: {body.injured}; conscious: {body.conscious}."
    )
    if body.notes.strip():
        summary += f" Notes: {body.notes.strip()}"
    transcript = TranscriptItem(speaker="caller", text=summary)
    incident.transcript.append(transcript)
    session.source = "manual"
    session.demo_mode = True
    session.status = "awaiting_confirmation"
    session.last_activity_at = transcript.ts
    store.save_session(session)

    await emit(StreamEvent(
        event="transcript.chunk",
        session_id=session_id,
        ts=transcript.ts,
        data={"chunk": transcript.model_dump(mode="json"), "simulated": True, "extraction": "structured form"},
    ))
    await emit(StreamEvent(
        event="incident.updated",
        session_id=session_id,
        data={
            "incident": incident.model_dump(mode="json"),
            "changed": ["silent_mode", "location", "type", "people", "severity", "evidence", "dispatch_confirmed"],
            "simulated": True,
        },
    ))
    schedule_dispatch(session, simulated=True)
    return session


@app.put("/api/sessions/{session_id}/evidence-video", status_code=status.HTTP_201_CREATED)
async def upload_evidence_video(session_id: str, request: Request) -> dict[str, Any]:
    """Persist a short, explicitly recorded demo clip with a strict size cap."""
    session = require_session(session_id)
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    extensions = {"video/webm": ".webm", "video/mp4": ".mp4", "video/quicktime": ".mov"}
    if content_type not in extensions:
        raise HTTPException(status_code=415, detail="Only WebM, MP4, or QuickTime video is accepted")
    body = await request.body()
    if not body:
        raise HTTPException(status_code=400, detail="The video is empty")
    if len(body) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="The 10-second video must be smaller than 15 MB")

    evidence_dir = settings.database_path.parent / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{session_id}{extensions[content_type]}"
    (evidence_dir / file_name).write_bytes(body)
    session.incident.evidence.video_captured = True
    session.incident.evidence.captured_at = datetime.now(timezone.utc)
    session.incident.evidence.file_name = file_name
    session.last_activity_at = session.incident.evidence.captured_at
    store.save_session(session)
    return {"stored": True, "bytes": len(body), "file_name": file_name}


@app.get("/api/sessions/{session_id}/evidence-video")
async def get_evidence_video(session_id: str) -> FileResponse:
    session = require_session(session_id)
    file_name = session.incident.evidence.file_name
    if not file_name:
        raise HTTPException(status_code=404, detail="No evidence video has been recorded")
    path = settings.database_path.parent / "evidence" / file_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Evidence video is unavailable")
    media_type = {".webm": "video/webm", ".mp4": "video/mp4", ".mov": "video/quicktime"}.get(path.suffix, "video/webm")
    return FileResponse(path, media_type=media_type)


@app.post("/api/sessions/{session_id}/silence", status_code=status.HTTP_202_ACCEPTED)
async def report_silence(session_id: str) -> dict[str, str]:
    session = require_session(session_id)
    await orchestrator.silence_check(session)
    return {"status": "check-in requested"}


@app.post("/api/sessions/{session_id}/stop", status_code=status.HTTP_202_ACCEPTED)
async def stop_session(session_id: str) -> dict[str, str]:
    session = require_session(session_id)
    await orchestrator.stop(session)
    for registry in [simulation_tasks, dispatch_tasks]:
        task = registry.get(session_id)
        if task and not task.done():
            task.cancel()
    await emit(StreamEvent(event="session.stopped", session_id=session_id, data={"simulated": session.demo_mode}))
    return {"session_id": session_id, "status": "stopped"}


@app.post("/api/sessions/{session_id}/complete", response_model=StoredSession)
async def complete_session(session_id: str) -> StoredSession:
    session = require_session(session_id)
    session.status = "complete"
    session.ended_at = datetime.now(timezone.utc)
    session.last_activity_at = session.ended_at
    store.save_session(session)
    await emit(StreamEvent(event="session.completed", session_id=session_id, data={"incident": session.incident.model_dump(mode="json")}))
    return session


@app.get("/api/reports", response_model=list[ReportSummary])
async def list_reports(limit: int = Query(default=50, ge=1, le=100)) -> list[ReportSummary]:
    return [
        ReportSummary(
            session_id=item.incident.session_id,
            started_at=item.started_at,
            ended_at=item.ended_at,
            status=item.status,
            type=item.incident.type,
            location=item.incident.location.text,
            severity=item.incident.severity,
            source=item.source,
            demo_mode=item.demo_mode,
        )
        for item in store.list_sessions(limit)
    ]


@app.get("/api/reports/{session_id}", response_model=StoredSession)
async def get_report(session_id: str) -> StoredSession:
    return require_session(session_id)


@app.get("/api/reports/{session_id}/pdf")
async def export_report_pdf(session_id: str) -> Response:
    session = require_session(session_id)
    pdf = build_pdf(session)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ek-awaaz-{session_id[:8]}.pdf"'},
    )


def _session_for_execution(execution_id: str | None, hinted_session_id: str | None) -> StoredSession | None:
    if hinted_session_id:
        found = store.get_session(hinted_session_id)
        if found:
            return found
    if execution_id:
        for candidate in store.list_sessions(100):
            if candidate.bolna_execution_id == execution_id:
                return candidate
            if any(action.external_id == execution_id for action in candidate.incident.actions):
                return candidate
    return None


def _normalise_bolna_transcript(payload: dict[str, Any]) -> list[tuple[str, str]]:
    transcript = payload.get("transcript") or payload.get("conversation") or []
    if isinstance(transcript, str):
        rows: list[tuple[str, str]] = []
        for line in transcript.splitlines():
            if ":" not in line:
                continue
            raw_speaker, text = line.split(":", 1)
            raw_speaker = raw_speaker.strip().lower()
            text = text.strip()
            if raw_speaker not in {"assistant", "agent", "bot", "user", "caller", "human"} or not text:
                continue
            speaker = "agent" if raw_speaker in {"assistant", "agent", "bot"} else "caller"
            rows.append((speaker, text))
        return rows or [("caller", transcript.strip())]
    rows: list[tuple[str, str]] = []
    for item in transcript if isinstance(transcript, list) else []:
        if not isinstance(item, dict):
            continue
        raw_speaker = str(item.get("speaker") or item.get("role") or "caller").lower()
        speaker = "agent" if raw_speaker in {"assistant", "agent", "bot"} else "caller"
        text = str(item.get("text") or item.get("content") or "").strip()
        if text:
            rows.append((speaker, text))
    return rows


async def _apply_bolna_update(payload: dict[str, Any]) -> str:
    execution_id = str(payload.get("id") or payload.get("execution_id") or "") or None
    user_data = payload.get("user_data") if isinstance(payload.get("user_data"), dict) else {}
    hinted_session_id = user_data.get("session_id")
    session = _session_for_execution(execution_id, hinted_session_id)
    if not session:
        session = StoredSession(
            incident=IncidentState(),
            status="listening",
            demo_mode=not settings.allow_real_actions,
            source="bolna",
            bolna_execution_id=execution_id,
        )
        store.create_session(session)
        await emit(StreamEvent(event="session.created", session_id=session.incident.session_id, data={"source": "bolna"}))

    external_action = next((a for a in session.incident.actions if a.external_id == execution_id), None)
    bolna_status = str(payload.get("status") or "")
    status_map = {
        "queued": "queued",
        "initiated": "ringing",
        "ringing": "ringing",
        "in-progress": "connected",
        "completed": "done",
        "call-disconnected": "connected",
        "no-answer": "failed",
        "busy": "failed",
        "failed": "failed",
        "canceled": "failed",
        "stopped": "failed",
        "error": "failed",
        "balance-low": "failed",
    }
    if external_action and bolna_status in status_map:
        external_action.status = status_map[bolna_status]
        store.save_session(session)
        await orchestrator._emit_action(session, external_action)

    existing = {(item.speaker, item.text) for item in session.incident.transcript}
    for speaker, text in _normalise_bolna_transcript(payload):
        if (speaker, text) not in existing:
            should_dispatch = await orchestrator.process_transcript(session, speaker, text, simulated=session.demo_mode)
            if should_dispatch:
                schedule_dispatch(session, simulated=session.demo_mode)
            existing.add((speaker, text))
    if bolna_status == "completed" and not external_action and not session.incident.dispatch_confirmed:
        session.status = "complete"
        session.ended_at = datetime.now(timezone.utc)
        store.save_session(session)
        await emit(StreamEvent(event="session.completed", session_id=session.incident.session_id, data={"source": "bolna"}))
    return session.incident.session_id


async def _poll_intake_call(session_id: str, execution_id: str) -> None:
    final_statuses = {"completed", "no-answer", "busy", "failed", "canceled", "stopped", "error", "balance-low"}
    try:
        while True:
            payload = await orchestrator.bolna.get_execution(execution_id)
            payload.setdefault("user_data", {"session_id": session_id})
            await _apply_bolna_update(payload)
            if str(payload.get("status") or "") in final_statuses:
                return
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        await emit(StreamEvent(
            event="error",
            session_id=session_id,
            data={"message": f"Could not refresh the live call: {str(exc)[:220]}"},
        ))


@app.post("/api/webhooks/bolna")
async def bolna_webhook(
    payload: dict[str, Any] = Body(...),
    x_ek_awaaz_secret: str | None = Header(default=None),
) -> JSONResponse:
    if settings.bolna_webhook_secret and x_ek_awaaz_secret != settings.bolna_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    session_id = await _apply_bolna_update(payload)
    return JSONResponse({"ok": True, "session_id": session_id})


@app.post("/api/integrations/bolna/create-listener")
async def create_bolna_listener(confirm: bool = Body(embed=True)) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    result = await orchestrator.bolna.create_listener_agent(
        ROOT / "prompts" / "listener.md",
        f"{settings.public_base_url}/api/webhooks/bolna",
    )
    return result


@app.post("/api/integrations/bolna/setup-inbound")
async def setup_bolna_inbound(confirm: bool = Body(embed=True)) -> dict[str, Any]:
    if not confirm:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required")
    if not settings.bolna_listener_agent_id or not settings.bolna_inbound_phone_number_id:
        raise HTTPException(status_code=400, detail="Listener agent and inbound phone-number IDs are required")
    return await orchestrator.bolna.setup_inbound(
        settings.bolna_listener_agent_id,
        settings.bolna_inbound_phone_number_id,
    )


@app.websocket("/ws/sessions/{session_id}")
async def session_stream(
    websocket: WebSocket,
    session_id: str,
    after: int = Query(default=0, ge=0),
) -> None:
    session = store.get_session(session_id)
    if not session:
        await websocket.close(code=4404, reason="Session not found")
        return
    await connections.connect(session_id, websocket)
    try:
        snapshot = StreamEvent(
            event="session.snapshot",
            session_id=session_id,
            data={"session": session.model_dump(mode="json"), "simulated": session.demo_mode},
        )
        await websocket.send_json(snapshot.model_dump(mode="json"))
        for event in store.list_events(session_id, after=after):
            await websocket.send_json(event.model_dump(mode="json"))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await connections.disconnect(session_id, websocket)


# A production build is served by FastAPI so the demo needs one process. Unknown
# non-API paths fall back to index.html for React Router refreshes.
if settings.frontend_dist.exists():
    @app.get("/{frontend_path:path}", include_in_schema=False)
    async def serve_frontend(frontend_path: str) -> FileResponse:
        dist = settings.frontend_dist.resolve()
        candidate = (dist / frontend_path).resolve()
        if frontend_path and candidate.is_relative_to(dist) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")
