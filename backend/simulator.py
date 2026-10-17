from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Awaitable, Callable, Literal

from .models import StoredSession, StreamEvent


@dataclass(frozen=True)
class ScenarioLine:
    speaker: Literal["caller", "agent"]
    text: str


ACCIDENT_SCENARIO = (
    ScenarioLine("agent", "Ek Awaaz. Main sun raha hoon. Kya hua?"),
    ScenarioLine("caller", "Bike ka accident hua hai, do log injured hain."),
    ScenarioLine("agent", "Aap exactly kahan hain? Nearest landmark batayein."),
    ScenarioLine("caller", "Baner flyover ke baad, blue temple ke paas."),
    ScenarioLine("agent", "Kya dono hosh mein hain?"),
    ScenarioLine("caller", "Haan, dono conscious hain. Traffic bahut fast hai."),
    ScenarioLine("agent", "Accident Baner flyover ke baad hai. Kya yeh sahi hai?"),
    ScenarioLine("caller", "Nahi, actually tunnel ke dusri side, blue temple ke paas."),
    ScenarioLine("agent", "Tunnel ki dusri side, blue temple. Kya yeh sahi hai?"),
    ScenarioLine("caller", "Haan, sahi hai."),
)


SILENT_SCENARIO = (
    ScenarioLine("agent", "Ek Awaaz. Main sun raha hoon. Kya hua?"),
    ScenarioLine("caller", "I'd like to order the usual."),
    ScenarioLine("agent", "Press 1 if you need help."),
    ScenarioLine("caller", "1"),
    ScenarioLine("agent", "Press 1 for medical danger."),
    ScenarioLine("caller", "1"),
    ScenarioLine("caller", "I am near Baner station, two people are hurt."),
    ScenarioLine("agent", "Press 1 to confirm the location."),
    ScenarioLine("caller", "1"),
)


async def run_simulation(
    session: StoredSession,
    delay_seconds: float,
    emit: Callable[[StreamEvent], Awaitable[None]],
    process: Callable[[StoredSession, str, str], Awaitable[bool]],
    dispatch: Callable[[StoredSession], Awaitable[None]],
    scenario: str = "accident",
) -> None:
    session.status = "listening"
    await emit(StreamEvent(
        event="simulation.started",
        session_id=session.incident.session_id,
        data={"scenario": scenario, "simulated": True},
    ))
    lines = SILENT_SCENARIO if scenario == "silent" else ACCIDENT_SCENARIO
    silent_yes_count = 0
    for line in lines:
        if session.status == "stopped":
            return
        await asyncio.sleep(delay_seconds)
        if scenario == "silent" and line.speaker == "caller" and line.text == "1":
            silent_yes_count += 1
            if silent_yes_count == 1:
                # DTMF confirms help is needed; the next prompt narrows the type.
                continue
            if silent_yes_count == 2:
                line = ScenarioLine("caller", "Medical emergency, two people hurt.")
            if silent_yes_count == 3:
                line = ScenarioLine("caller", "Yes, correct.")
        should_dispatch = await process(session, line.speaker, line.text)
        if should_dispatch:
            await dispatch(session)
    if session.incident.dispatch_confirmed and not session.incident.actions:
        await dispatch(session)
    await emit(StreamEvent(
        event="simulation.completed",
        session_id=session.incident.session_id,
        data={"incident": session.incident.model_dump(mode="json"), "simulated": True},
    ))

