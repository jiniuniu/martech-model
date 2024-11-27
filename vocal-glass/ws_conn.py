import asyncio
import uuid
from io import BytesIO

from fastapi import WebSocket
from loguru import logger

PING_INTERVAL = 10  # Interval for sending pings (seconds)


class ConnectionManager:
    """Manages WebSocket connections, heartbeats, and audio buffers."""

    def __init__(self):
        self.active_connections: dict[WebSocket, dict] = {}

    async def connect(self, websocket: WebSocket) -> str:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        session_id = str(uuid.uuid4())  # Generate a unique session ID
        self.active_connections[websocket] = {
            "session_id": session_id,
            "audio_buffer": BytesIO(),  # Initialize an empty audio buffer
        }
        logger.info(f"New connection: {websocket.client} with session_id {session_id}")
        asyncio.create_task(self.heartbeat(websocket))
        return session_id

    async def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        connection_info = self.active_connections.pop(websocket, None)
        if connection_info:
            session_id = connection_info["session_id"]
            logger.info(
                f"Connection closed: {websocket.client} (session_id: {session_id})"
            )

    async def heartbeat(self, websocket: WebSocket):
        """Send periodic pings to check connection health."""
        try:
            while websocket in self.active_connections:
                await websocket.send_text("ping")
                logger.debug("Ping sent.")
                await asyncio.sleep(PING_INTERVAL)
        except Exception:
            logger.warning(f"Connection lost during heartbeat: {websocket.client}")
            await self.disconnect(websocket)
