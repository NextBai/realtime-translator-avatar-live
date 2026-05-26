"""Socket.IO event handlers - now delegates to handlers package."""
from __future__ import annotations

from .handlers import register_all


def register(socketio, manager) -> None:
    """Register all event handlers with the Socket.IO instance."""
    register_all(socketio, manager)