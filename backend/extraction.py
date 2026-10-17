from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .config import Settings
from .models import Highlight, IncidentState

try:
    from groq import AsyncGroq
except ImportError:  # pragma: no cover - optional in demo mode
    AsyncGroq = None  # type: ignore[assignment]


NUMBER_WORDS = {
    "one": 1, "ek": 1, "एक": 1,
    "two": 2, "do": 2, "दोन": 2, "दो": 2,
    "three": 3, "teen": 3, "तीन": 3,
    "four": 4, "चार": 4,
    "five": 5, "paanch": 5, "पाच": 5,
}


@dataclass
class ExtractionResult:
    patch: dict[str, Any] = field(default_factory=dict)
    highlights: list[Highlight] = field(default_factory=list)
    corrected_fields: set[str] = field(default_factory=set)
    used_groq: bool = False


def _spans(text: str, terms: list[tuple[str, str]]) -> list[Highlight]:
    found: list[Highlight] = []
    lower = text.lower()
    seen: set[tuple[int, int, str]] = set()
    for category, term in terms:
        start = lower.find(term.lower())
        if start < 0:
            continue
        key = (start, start + len(term), category)
        if key not in seen:
            seen.add(key)
            found.append(Highlight(start=start, end=start + len(term), category=category))
    return sorted(found, key=lambda item: item.start)


class EntityExtractor:
    """Deterministic fast path with optional Groq enrichment."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = (
            AsyncGroq(api_key=settings.groq_api_key)
            if settings.groq_api_key and AsyncGroq is not None
            else None
        )

    async def extract(self, text: str, incident: IncidentState) -> ExtractionResult:
        result = self._heuristic(text, incident)
        if not self.client:
            return result
        try:
            groq_patch = await self._groq_extract(text, incident)
        except Exception:
            return result
        result.used_groq = True
        result.patch = self._combine(result.patch, groq_patch)
        return result

    def _heuristic(self, text: str, incident: IncidentState) -> ExtractionResult:
        lower = text.lower().strip()
        patch: dict[str, Any] = {}
        terms: list[tuple[str, str]] = []
        corrected: set[str] = set()

        if "i'd like to order the usual" in lower or "order the usual" in lower:
            patch["silent_mode"] = True

        type_terms = {
            "road_accident": ["accident", "crash", "bike gir", "gaadi takkar"],
            "fire": ["fire", "aag", "आग"],
            "medical": ["heart attack", "fainted", "breathing", "medical", "बेहोश"],
            "assault": ["attack", "assault", "weapon", "मार"],
        }
        for kind, needles in type_terms.items():
            hit = next((needle for needle in needles if needle in lower), None)
            if hit:
                patch["type"] = kind
                terms.append(("hazard", hit))
                break

        hazard_terms = {
            "fire": ["fire", "aag", "आग"],
            "traffic": ["traffic", "gaadiyan", "cars fast"],
            "gas": ["gas leak", "gas"],
            "crowd": ["crowd", "bheed", "भीड़"],
        }
        hazards = list(incident.hazards)
        for hazard, needles in hazard_terms.items():
            hit = next((needle for needle in needles if needle in lower), None)
            if hit and hazard not in hazards:
                hazards.append(hazard)
                terms.append(("hazard", hit))
        if hazards != incident.hazards:
            patch["hazards"] = hazards

        count = None
        count_term = None
        for token in re.findall(r"[\w\u0900-\u097f]+", lower):
            if token.isdigit():
                count, count_term = int(token), token
                break
            if token in NUMBER_WORDS:
                count, count_term = NUMBER_WORDS[token], token
                break
        person_words = ["people", "person", "log", "injured", "hurt", "जखमी"]
        if count is not None and any(word in lower for word in person_words):
            people = incident.people.model_dump()
            people["count"] = count
            if any(word in lower for word in ["injured", "hurt", "जखमी"]):
                people["injured"] = count
                injury_term = next(word for word in ["injured", "hurt", "जखमी"] if word in lower)
                terms.append(("injury", injury_term))
            terms.append(("people", count_term or str(count)))
            patch["people"] = people

        conscious_terms = ["conscious", "hosh mein", "होश में"]
        if any(term in lower for term in conscious_terms):
            people = patch.get("people", incident.people.model_dump())
            negative = any(term in lower for term in ["not conscious", "behosh", "बेहोश"])
            people["conscious"] = "no" if negative else "yes"
            patch["people"] = people
            terms.append(("people", next(term for term in conscious_terms if term in lower)))

        if any(term in lower for term in ["critical", "not breathing", "बहुत खून", "heavy bleeding"]):
            patch["severity"] = "critical"
        elif any(term in lower for term in ["traffic", "fire", "bleeding", "injured", "बेहोश"]):
            patch["severity"] = "high"
        elif patch.get("type") and incident.severity == "unknown":
            patch["severity"] = "medium"

        if any(term in lower for term in ["i am safe", "main safe", "मी सुरक्षित", "haan, safe"]):
            patch["caller_safe"] = "yes"
        elif any(term in lower for term in ["not safe", "danger mein", "धोका"]):
            patch["caller_safe"] = "no"

        is_correction = bool(re.search(r"\b(no|nahi|actually|correction)\b", lower)) or "नहीं" in lower or "नाही" in lower
        location = self._location_from_text(text)
        if location:
            patch["location"] = {
                "text": location,
                "landmarks": self._landmarks(location),
                "confidence": "medium",
                "confirmed": False,
            }
            terms.append(("location", location))
            if is_correction:
                corrected.add("location")

        confirmation_terms = ["haan, sahi", "yes, correct", "correct hai", "हो बरोबर", "yes that's right"]
        if any(term in lower for term in confirmation_terms):
            patch["dispatch_confirmed"] = True
            patch["location"] = {"confirmed": True}

        return ExtractionResult(
            patch=patch,
            highlights=_spans(text, terms),
            corrected_fields=corrected,
        )

    @staticmethod
    def _location_from_text(text: str) -> str | None:
        lower = text.lower()
        markers = ["near ", "at ", "ke paas", "के पास", "after ", "baad", "opposite ", "समोर"]
        if not any(marker in lower for marker in markers):
            return None
        cleaned = text.strip().strip(".?!")
        cleaned = re.sub(
            r"^(?:(?:no|nahi|nahin|actually|correction(?:\s+is)?)\b[\s,:-]*)+",
            "",
            cleaned,
            flags=re.I,
        )
        cleaned = re.sub(r"^(we are|i am|hum|main|location is|it is)\s+", "", cleaned, flags=re.I)
        return cleaned[:220]

    @staticmethod
    def _landmarks(location: str) -> list[str]:
        pieces = re.split(r",|\b(?:near|after|opposite|ke paas|baad)\b", location, flags=re.I)
        return [piece.strip(" .") for piece in pieces if len(piece.strip(" .")) >= 4][:3]

    async def _groq_extract(self, text: str, incident: IncidentState) -> dict[str, Any]:
        schema_hint = {
            "language_detected": "hi|mr|en|hinglish|null",
            "type": "road_accident|fire|medical|assault|other|unknown|null",
            "location": {"text": "string|null", "landmarks": [], "confidence": "low|medium|high|null"},
            "people": {"count": "int|null", "injured": "int|null", "conscious": "yes|no|unknown|null"},
            "severity": "low|medium|high|critical|unknown|null",
            "hazards": ["fire|traffic|gas|crowd"],
            "caller_safe": "yes|no|unknown|null",
            "silent_mode": "bool|null",
        }
        response = await self.client.chat.completions.create(
            model=self.settings.groq_model,
            temperature=0,
            max_tokens=450,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Extract emergency facts from one Hindi, Marathi, English, or code-switched utterance. "
                        "Return JSON only. Use null when absent. Do not invent. Schema: " + json.dumps(schema_hint)
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps({"current": incident.model_dump(mode="json"), "utterance": text}),
                },
            ],
        )
        raw = json.loads(response.choices[0].message.content or "{}")
        return self._drop_nulls(raw)

    @classmethod
    def _drop_nulls(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: cls._drop_nulls(item) for key, item in value.items() if item is not None}
        if isinstance(value, list):
            return [cls._drop_nulls(item) for item in value if item is not None]
        return value

    @staticmethod
    def _combine(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
        merged = dict(secondary)
        for key, value in primary.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged


def apply_extraction(incident: IncidentState, result: ExtractionResult) -> set[str]:
    """Merge extraction while protecting confirmed data from accidental overwrite."""
    changed: set[str] = set()
    for key, value in result.patch.items():
        if key == "location":
            correction = "location" in result.corrected_fields
            for nested_key, nested_value in value.items():
                current = getattr(incident.location, nested_key)
                if incident.location.confirmed and nested_key != "confirmed" and not correction:
                    continue
                if current != nested_value:
                    setattr(incident.location, nested_key, nested_value)
                    changed.add(f"location.{nested_key}")
            if correction:
                incident.location.confirmed = False
                incident.dispatch_confirmed = False
                changed.update({"location.confirmed", "dispatch_confirmed"})
        elif key == "people":
            for nested_key, nested_value in value.items():
                current = getattr(incident.people, nested_key)
                if current != nested_value:
                    setattr(incident.people, nested_key, nested_value)
                    changed.add(f"people.{nested_key}")
        elif hasattr(incident, key) and getattr(incident, key) != value:
            setattr(incident, key, value)
            changed.add(key)
    return changed
