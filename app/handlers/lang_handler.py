"""Language and session event handlers."""
from __future__ import annotations

import logging
from typing import Any

from flask import request
from flask_socketio import emit

from ..languages import LANGUAGES

logger = logging.getLogger("live_bridge.handlers.lang")


def register(socketio: Any, manager: Any) -> None:
    """Register language and session event handlers."""

    @socketio.on("connect")
    def on_connect() -> None:
        sid = request.sid  # type: ignore[attr-defined]
        logger.info("client connected: %s", sid)
        emit("hello", {"languages": LANGUAGES, "model": manager.model})

    @socketio.on("disconnect")
    def on_disconnect() -> None:
        sid = request.sid  # type: ignore[attr-defined]
        logger.info("client disconnected: %s", sid)
        manager.stop(sid)

    @socketio.on("session_init")
    def on_session_init(data: dict[str, Any]) -> None:
        sid = request.sid  # type: ignore[attr-defined]
        src = data.get("source", "auto")
        tgt = data.get("target", "en")
        logger.info("[%s] session_init: source=%s, target=%s", sid, src, tgt)
        manager.start(sid, src, tgt)

    @socketio.on("set_languages")
    def on_set_languages(data: dict[str, Any]) -> None:
        sid = request.sid  # type: ignore[attr-defined]
        source = data.get("source", "auto")
        target = data.get("target", "en")
        logger.info("[%s] set_languages: source=%s, target=%s", sid, source, target)
        manager.update_languages(sid, source, target)

    @socketio.on("reconnect")
    def on_reconnect(data: dict[str, Any] | None = None) -> None:
        """Handle auto-reconnect requests from SessionManager."""
        sid = request.sid  # type: ignore[attr-defined]
        data = data or {}
        source = data.get("source", "auto")
        target = data.get("target", "en")
        logger.info("[%s] reconnect event received (src=%s, tgt=%s)", sid, source, target)
        # 重新啟動 session
        manager.start(sid, source, target)