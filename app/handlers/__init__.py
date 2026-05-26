"""Event handlers for Socket.IO events."""
from __future__ import annotations

from .ptt_handler import register as register_ptt_handlers
from .lang_handler import register as register_lang_handlers


def register_all(socketio: Any, manager: Any) -> None:
    """Register all event handlers with the Socket.IO instance."""
    register_ptt_handlers(socketio, manager)
    register_lang_handlers(socketio, manager)