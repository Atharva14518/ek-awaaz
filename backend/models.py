from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MutableModel(BaseModel):
    model_config = ConfigDict(validate_assignment=True)


class Confidence(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class GPS(MutableModel):
    lat: float
    lng: float


class Location(MutableModel):
    text: str = ""
    landmarks: list[str] = Field(default_factory=list)
    gps: GPS | None = None
    confidence: Confidence = Confidence.low
    confirmed: bool = False


class People(MutableModel):
    count: int = 0
    injured: int = 0
    conscious: Literal["yes", "no", "unknown"] = "unknown"


class Highlight(MutableModel):
    start: int
    end: int
    category: Literal["location", "injury", "people", "hazard", "time"]


class TranscriptItem(MutableModel):
    ts: datetime = Field(default_factory=utc_now)
    speaker: Literal["caller", "agent"]
    text: str
    highlights: list[Highlight] = Field(default_factory=list)


class Evidence(MutableModel):
    motion_detected: bool = False
    motion_peak: float | None = None
    video_captured: bool = False
    video_duration_seconds: int = 0
    captured_at: datetime | None = None
    file_name: str | None = None


class Action(MutableModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ts: datetime = Field(default_factory=utc_now)
    kind: Literal["call", "sms", "note"]
    target: str
    status: Literal["queued", "ringing", "connected", "failed", "done"]
    script_summary: str
    attempts: int = 0
    external_id: str | None = None
    simulated: bool = True


class IncidentState(MutableModel):
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    language_detected: Literal["hi", "mr", "en", "hinglish"] = "hinglish"
    type: Literal["road_accident", "fire", "medical", "assault", "other", "unknown"] = "unknown"
    location: Location = Field(default_factory=Location)
    people: People = Field(default_factory=People)
    severity: Literal["low", "medium", "high", "critical", "unknown"] = "unknown"
    hazards: list[Literal["fire", "traffic", "gas", "crowd"]] = Field(default_factory=list)
    caller_safe: Literal["yes", "no", "unknown"] = "unknown"
    silent_mode: bool = False
    dispatch_confirmed: bool = False
    evidence: Evidence = Field(default_factory=Evidence)
    actions: list[Action] = Field(default_factory=list)
    transcript: list[TranscriptItem] = Field(default_factory=list)


class StoredSession(MutableModel):
    incident: IncidentState
    status: Literal["idle", "listening", "awaiting_confirmation", "dispatching", "complete", "stopped"] = "idle"
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    demo_mode: bool = True
    source: Literal["simulator", "bolna", "manual"] = "simulator"
    bolna_execution_id: str | None = None
    last_activity_at: datetime = Field(default_factory=utc_now)
    silence_check_failed: bool = False


EventName = Literal[
    "session.created",
    "simulation.started",
    "transcript.chunk",
    "incident.updated",
    "listener.prompt",
    "confirmation.required",
    "dispatch.started",
    "action.updated",
    "simulation.completed",
    "session.completed",
    "session.stopped",
    "session.snapshot",
    "error",
]


class StreamEvent(MutableModel):
    sequence: int = 0
    event: EventName
    session_id: str
    ts: datetime = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)


class TranscriptInput(BaseModel):
    speaker: Literal["caller", "agent"] = "caller"
    text: str = Field(min_length=1, max_length=4000)
    source: Literal["bolna", "manual", "simulator"] = "manual"


class ConfirmationInput(BaseModel):
    confirmed: bool
    correction: str | None = Field(default=None, max_length=1000)


class DTMFInput(BaseModel):
    digit: Literal["1", "2"]


class GPSInput(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class SilentIncidentInput(BaseModel):
    incident_type: Literal["road_accident", "fire", "medical", "assault", "other"]
    address: str = Field(min_length=3, max_length=500)
    address_confirmed: bool
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    people: int = Field(default=1, ge=0, le=100)
    injured: int = Field(default=1, ge=0, le=100)
    conscious: Literal["yes", "no", "unknown"] = "unknown"
    severity: Literal["low", "medium", "high", "critical"] = "high"
    notes: str = Field(default="", max_length=1000)
    motion_detected: bool = False
    motion_peak: float | None = Field(default=None, ge=0, le=200)
    video_captured: bool = False
    video_duration_seconds: int = Field(default=0, ge=0, le=10)


class ReportSummary(BaseModel):
    session_id: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    type: str
    location: str
    severity: str
    source: str
    demo_mode: bool
