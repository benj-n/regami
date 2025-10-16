"""
WebSocket router for real-time notifications.

Provides WebSocket endpoint for clients to receive real-time updates about:
- New match notifications
- Match status changes (accepted, confirmed, rejected)
- New messages (future feature)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from typing import Dict, Set
import json
import asyncio
from datetime import datetime
from ..db import get_db
from .users import get_current_user_ws
from ..logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Store active WebSocket connections: user_id -> Set[WebSocket]
active_connections: Dict[str, Set[WebSocket]] = {}


class ConnectionManager:
    """Manage WebSocket connections for real-time notifications."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        """Accept new WebSocket connection for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(
            "websocket_connected",
            user_id=user_id,
            total_connections=len(self.active_connections[user_id])
        )

    def disconnect(self, user_id: str, websocket: WebSocket):
        """Remove WebSocket connection."""
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
            logger.info("websocket_disconnected", user_id=user_id)

    async def send_personal_message(self, message: dict, user_id: str):
        """Send message to a specific user's all connections."""
        if user_id in self.active_connections:
            # Send to all connections for this user (multiple tabs/devices)
            disconnected = []
            for websocket in self.active_connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(
                        "websocket_send_error",
                        user_id=user_id,
                        error=str(e),
                        error_type=type(e).__name__
                    )
                    disconnected.append(websocket)

            # Clean up failed connections
            for ws in disconnected:
                self.disconnect(user_id, ws)

    async def broadcast(self, message: dict, user_ids: list[str] = None):
        """Broadcast message to specific users or all connected users."""
        target_users = user_ids if user_ids else list(self.active_connections.keys())

        for user_id in target_users:
            await self.send_personal_message(message, user_id)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for real-time notifications.

    Query params:
        token: JWT authentication token

    Message format (server -> client):
        {
            "type": "notification" | "match_update" | "ping",
            "data": {...},
            "timestamp": "2025-11-11T12:00:00"
        }

    Client should send ping messages to keep connection alive:
        {"type": "ping"}

    Server will respond with:
        {"type": "pong"}
    """
    # Authenticate user
    try:
        user = await get_current_user_ws(token, db)
    except Exception as e:
        await websocket.close(code=1008, reason=f"Authentication failed: {str(e)}")
        return

    # Connect
    await manager.connect(user.id, websocket)

    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "data": {"message": "WebSocket connected", "user_id": user.id},
        "timestamp": asyncio.get_event_loop().time()
    })

    try:
        while True:
            # Wait for messages from client (ping/pong)
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(user.id, websocket)
    except Exception as e:
        logger.error(
            "websocket_error",
            user_id=user.id,
            error=str(e),
            error_type=type(e).__name__
        )
        manager.disconnect(user.id, websocket)


# Helper functions to send notifications through WebSocket

async def notify_new_match(user_id: str, match_data: dict):
    """Send notification about new match to user."""
    await manager.send_personal_message({
        "type": "new_match",
        "data": match_data,
        "timestamp": asyncio.get_event_loop().time()
    }, user_id)


async def notify_match_accepted(user_id: str, match_data: dict):
    """Send notification about match acceptance to user."""
    await manager.send_personal_message({
        "type": "match_accepted",
        "data": match_data,
        "timestamp": asyncio.get_event_loop().time()
    }, user_id)


async def notify_match_confirmed(user_id: str, match_data: dict):
    """Send notification about match confirmation to user."""
    await manager.send_personal_message({
        "type": "match_confirmed",
        "data": match_data,
        "timestamp": asyncio.get_event_loop().time()
    }, user_id)


async def notify_match_rejected(user_id: str, match_data: dict):
    """Send notification about match rejection to user."""
    await manager.send_personal_message({
        "type": "match_rejected",
        "data": match_data,
        "timestamp": asyncio.get_event_loop().time()
    }, user_id)


async def notify_new_notification(user_id: str, notification_data: dict):
    """Send notification about new system notification to user."""
    await manager.send_personal_message({
        "type": "notification",
        "data": notification_data,
        "timestamp": asyncio.get_event_loop().time()
    }, user_id)


async def notify_new_message(user_id: str, message_data: dict):
    """Send notification about new message to user."""
    await manager.send_personal_message({
        "type": "new_message",
        "data": message_data,
        "timestamp": asyncio.get_event_loop().time()
    }, user_id)
