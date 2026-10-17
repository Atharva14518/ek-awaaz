from __future__ import annotations

from typing import Any, TypedDict
from urllib.parse import quote_plus

from .models import Action, IncidentState

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:  # pragma: no cover - fallback keeps simulator runnable
    END = "__end__"
    StateGraph = None  # type: ignore[assignment]
    LANGGRAPH_AVAILABLE = False


class DispatcherState(TypedDict, total=False):
    incident: dict[str, Any]
    chunk: dict[str, Any]
    complete: bool
    confirmation_required: bool
    planned_actions: list[dict[str, Any]]
    report_ready: bool


def ingest_chunk(state: DispatcherState) -> DispatcherState:
    return state


def extract_entities(state: DispatcherState) -> DispatcherState:
    # Streaming extraction happens before graph invocation so the same function
    # can serve WebSocket, Bolna webhook, and simulator inputs.
    return state


def completeness_check(state: DispatcherState) -> DispatcherState:
    incident = state["incident"]
    location = incident.get("location", {})
    state["complete"] = bool(
        incident.get("type") not in {None, "", "unknown"}
        and location.get("text")
        and location.get("confidence") in {"medium", "high"}
    )
    return state


def await_confirmation(state: DispatcherState) -> DispatcherState:
    incident = state["incident"]
    state["confirmation_required"] = bool(
        state.get("complete") and not incident.get("dispatch_confirmed")
    )
    return state


def plan_actions_node(state: DispatcherState) -> DispatcherState:
    incident = IncidentState.model_validate(state["incident"])
    state["planned_actions"] = [item.model_dump(mode="json") for item in plan_actions(incident)]
    return state


def execute_actions(state: DispatcherState) -> DispatcherState:
    # Side effects are deliberately executed by DispatchCoordinator, where
    # confirmation, rate limits, kill switches, and adapters are available.
    return state


def report(state: DispatcherState) -> DispatcherState:
    state["report_ready"] = True
    return state


def _route_after_completeness(state: DispatcherState) -> str:
    return "await_confirmation" if state.get("complete") else "report"


def _route_after_confirmation(state: DispatcherState) -> str:
    incident = state["incident"]
    return "plan_actions" if incident.get("dispatch_confirmed") else "report"


def build_dispatcher_graph():
    if not LANGGRAPH_AVAILABLE:
        return None
    builder = StateGraph(DispatcherState)
    builder.add_node("ingest_chunk", ingest_chunk)
    builder.add_node("extract_entities", extract_entities)
    builder.add_node("completeness_check", completeness_check)
    builder.add_node("await_confirmation", await_confirmation)
    builder.add_node("plan_actions", plan_actions_node)
    builder.add_node("execute_actions", execute_actions)
    builder.add_node("report", report)
    builder.set_entry_point("ingest_chunk")
    builder.add_edge("ingest_chunk", "extract_entities")
    builder.add_edge("extract_entities", "completeness_check")
    builder.add_conditional_edges(
        "completeness_check",
        _route_after_completeness,
        {"await_confirmation": "await_confirmation", "report": "report"},
    )
    builder.add_conditional_edges(
        "await_confirmation",
        _route_after_confirmation,
        {"plan_actions": "plan_actions", "report": "report"},
    )
    builder.add_edge("plan_actions", "execute_actions")
    builder.add_edge("execute_actions", "report")
    builder.add_edge("report", END)
    return builder.compile()


def graph_preview(incident: IncidentState) -> DispatcherState:
    state: DispatcherState = {"incident": incident.model_dump(mode="json")}
    if LANGGRAPH_AVAILABLE:
        return build_dispatcher_graph().invoke(state)
    state = completeness_check(state)
    if state.get("complete"):
        state = await_confirmation(state)
        if incident.dispatch_confirmed:
            state = plan_actions_node(state)
            state = execute_actions(state)
    return report(state)


def plan_actions(incident: IncidentState) -> list[Action]:
    location = incident.location.text or "location pending"
    landmarks = ", ".join(incident.location.landmarks) or "none given"
    hazards = ", ".join(incident.hazards) or "none reported"
    actions = [
        Action(
            kind="call",
            target="Ambulance (demo)",
            status="queued",
            script_summary=(
                f"{incident.people.injured} injured of {incident.people.count}; "
                f"conscious: {incident.people.conscious}; at {location}; landmarks: {landmarks}."
            ),
        ),
        Action(
            kind="call",
            target="Police (demo)",
            status="queued",
            script_summary=f"{incident.type.replace('_', ' ')}; hazards: {hazards}; at {location}.",
        ),
        Action(
            kind="call",
            target="Family (demo)",
            status="queued",
            script_summary=f"Your family member is at {location}. Support contacts have been notified.",
        ),
    ]
    map_query = (
        f"{incident.location.gps.lat},{incident.location.gps.lng}"
        if incident.location.gps
        else quote_plus(location)
    )
    actions.append(
        Action(
            kind="sms",
            target="Caller location link (demo)",
            status="queued",
            script_summary=f"Share exact location: https://maps.google.com/?q={map_query}",
        )
    )
    return actions

