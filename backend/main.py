from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, Query, Response, WebSocket, WebSocketDisconnect, status
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
    StoredSession,
    StreamEvent,
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


async def emit(event: StreamEvent) -> None:
    stored = store.append_event(event)
    await connections.broadcast(stored)


orchestrator = IncidentOrchestrator(settings, store, emit)


@asynccontextmanager
async def lifespan(_: FastAPI):
    store.initialize()
    yield
    for task in [*simulation_tasks.values(), *dispatch_tasks.values()]:
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
    }


@app.get("/api/config")
async def public_config() -> dict[str, Any]:
    return {
        "demo_mode": settings.demo_mode,
        "real_actions_enabled": settings.allow_real_actions,
        "demo_phone_number": settings.bolna_from_phone_number or "+91 00000 00000",
        "listener_agent_configured": bool(settings.bolna_listener_agent_id),
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
    for registry in [simulation_tasks, dispatch_tasks]:
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
        return [("caller", transcript)]
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


@app.post("/api/webhooks/bolna")
async def bolna_webhook(
    payload: dict[str, Any] = Body(...),
    x_ek_awaaz_secret: str | None = Header(default=None),
) -> JSONResponse:
    if settings.bolna_webhook_secret and x_ek_awaaz_secret != settings.bolna_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
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
    if bolna_status == "completed" and not external_action:
        session.status = "complete"
        session.ended_at = datetime.now(timezone.utc)
        store.save_session(session)
        await emit(StreamEvent(event="session.completed", session_id=session.incident.session_id, data={"source": "bolna"}))
    return JSONResponse({"ok": True, "session_id": session.incident.session_id})


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
