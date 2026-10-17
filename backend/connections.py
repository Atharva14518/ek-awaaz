from __future__ import annotations

import asyncio
from collections import defaultdict

from fastapi import WebSocket

from .models import StreamEvent


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[session_id].add(websocket)

    async def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._connections.get(session_id)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._connections.pop(session_id, None)

    async def broadcast(self, event: StreamEvent) -> None:
        async with self._lock:
            sockets = list(self._connections.get(event.session_id, ()))
        stale: list[WebSocket] = []
        for socket in sockets:
            try:
                await socket.send_json(event.model_dump(mode="json"))
            except RuntimeError:
                stale.append(socket)
        for socket in stale:
            await self.disconnect(event.session_id, socket)

