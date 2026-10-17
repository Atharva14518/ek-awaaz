from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from threading import Lock

from .models import StoredSession, StreamEvent


class SessionStore:
    """Small SQLite repository; each operation owns its connection."""

    def __init__(self, path: Path):
        self.path = path
        self._write_lock = Lock()

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_events_session
                ON events(session_id, id);
                """
            )

    def create_session(self, session: StoredSession) -> None:
        encoded = session.model_dump_json()
        now = session.started_at.isoformat()
        with self._write_lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO sessions (id, state_json, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session.incident.session_id, encoded, now, now),
            )

    def get_session(self, session_id: str) -> StoredSession | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT state_json FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
        return StoredSession.model_validate_json(row[0]) if row else None

    def save_session(self, session: StoredSession) -> None:
        with self._write_lock, self._connect() as connection:
            connection.execute(
                "UPDATE sessions SET state_json = ?, updated_at = ? WHERE id = ?",
                (
                    session.model_dump_json(),
                    session.last_activity_at.isoformat(),
                    session.incident.session_id,
                ),
            )

    def append_event(self, event: StreamEvent) -> StreamEvent:
        payload = event.model_dump(mode="json")
        with self._write_lock, self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO events (session_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (event.session_id, event.event, json.dumps(payload), event.ts.isoformat()),
            )
            event.sequence = int(cursor.lastrowid)
            payload["sequence"] = event.sequence
            connection.execute(
                "UPDATE events SET payload_json = ? WHERE id = ?",
                (json.dumps(payload), event.sequence),
            )
        return event

    def list_events(self, session_id: str, after: int = 0) -> list[StreamEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM events WHERE session_id = ? AND id > ? ORDER BY id",
                (session_id, after),
            ).fetchall()
        return [StreamEvent.model_validate_json(row[0]) for row in rows]

    def list_sessions(self, limit: int = 100) -> list[StoredSession]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT state_json FROM sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [StoredSession.model_validate_json(row[0]) for row in rows]

    def delete_session(self, session_id: str) -> bool:
        with self._write_lock, self._connect() as connection:
            connection.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
            cursor = connection.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cursor.rowcount > 0

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection
