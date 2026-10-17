from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_PATH"] = str(Path(__file__).parent / "test.db")
os.environ["SIMULATOR_DELAY_SECONDS"] = "0.001"

from fastapi.testclient import TestClient

from backend.main import app
from backend.bolna_client import BolnaClient, BolnaSafetyError
from backend.config import get_settings
from backend.extraction import ExtractionResult, apply_extraction
from backend.graph import LANGGRAPH_AVAILABLE, graph_preview
from backend.models import IncidentState, StoredSession
from backend.report import build_pdf

import pytest


def test_simulator_streams_transcript_and_incident_updates() -> None:
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["real_actions_enabled"] is False

        created = client.post("/api/sessions")
        assert created.status_code == 201
        session_id = created.json()["incident"]["session_id"]

        with client.websocket_connect(f"/ws/sessions/{session_id}") as websocket:
            assert websocket.receive_json()["event"] == "session.snapshot"
            # The persisted creation event is replayed immediately after the snapshot.
            assert websocket.receive_json()["event"] == "session.created"

            started = client.post(f"/api/sessions/{session_id}/simulate")
            assert started.status_code == 202

            event_types: list[str] = []
            final_event = None
            while "simulation.completed" not in event_types:
                event = websocket.receive_json()
                event_types.append(event["event"])
                if event["event"] == "simulation.completed":
                    final_event = event

        assert "transcript.chunk" in event_types
        assert "incident.updated" in event_types
        assert "action.updated" in event_types
        assert "session.completed" in event_types
        assert final_event is not None
        incident = final_event["data"]["incident"]
        assert incident["type"] == "road_accident"
        assert incident["location"]["confirmed"] is True
        assert "tunnel" in incident["location"]["text"].lower()
        assert not incident["location"]["text"].lower().startswith(("nahi", "actually"))
        assert incident["dispatch_confirmed"] is True
        assert len(incident["transcript"]) == 10
        assert len(incident["actions"]) == 4
        assert all(action["status"] == "done" for action in incident["actions"])

        stored = client.get(f"/api/sessions/{session_id}").json()
        assert stored["status"] == "complete"

        cleared = client.delete(f"/api/sessions/{session_id}")
        assert cleared.status_code == 204
        assert client.get(f"/api/sessions/{session_id}").status_code == 404


def test_confirmed_location_requires_an_explicit_correction() -> None:
    incident = IncidentState()
    incident.location.text = "Blue temple"
    incident.location.confirmed = True
    incident.dispatch_confirmed = True

    ignored = ExtractionResult(patch={"location": {"text": "Other road"}})
    assert not apply_extraction(incident, ignored)
    assert incident.location.text == "Blue temple"

    correction = ExtractionResult(
        patch={"location": {"text": "Other side of tunnel"}},
        corrected_fields={"location"},
    )
    changed = apply_extraction(incident, correction)
    assert "location.text" in changed
    assert incident.location.confirmed is False
    assert incident.dispatch_confirmed is False


def test_dispatch_graph_and_pdf_report() -> None:
    incident = IncidentState(type="medical", severity="high", dispatch_confirmed=True)
    incident.location.text = "Near Baner station"
    incident.location.confidence = "medium"
    incident.location.confirmed = True
    preview = graph_preview(incident)
    assert LANGGRAPH_AVAILABLE is True
    assert preview["complete"] is True
    assert len(preview["planned_actions"]) == 4

    pdf = build_pdf(StoredSession(incident=incident))
    assert pdf.startswith(b"%PDF")


def test_emergency_numbers_are_blocked_at_the_adapter() -> None:
    client = BolnaClient(get_settings())
    for number in ["100", "101", "102", "108", "112", "+91 112"]:
        with pytest.raises(BolnaSafetyError):
            client._assert_safe_recipient(number)
