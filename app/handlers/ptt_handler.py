"""Push-to-talk event handlers."""
from __future__ import annotations

import base64
import logging
from typing import Any

from flask import request
from flask_socketio import emit

logger = logging.getLogger("live_bridge.handlers.ptt")


def register(socketio: Any, manager: Any) -> None:
    """Register PTT (push-to-talk) event handlers."""

    @socketio.on("ptt_start")
    def on_ptt_start(*_args: Any, **_kwargs: Any) -> None:
        sid = request.sid  # type: ignore[attr-defined]
        logger.debug("[%s] ptt_start", sid)
        manager.ptt_start(sid)

    @socketio.on("ptt_end")
    def on_ptt_end(*_args: Any, **_kwargs: Any) -> None:
        sid = request.sid  # type: ignore[attr-defined]
        logger.debug("[%s] ptt_end", sid)
        manager.ptt_end(sid)

    @socketio.on("audio_chunk")
    def on_audio_chunk(data: Any = None, *_args: Any, **_kwargs: Any) -> None:
        sid = request.sid  # type: ignore[attr-defined]
        if not isinstance(data, dict):
            return
        payload = data.get("pcm")
        if payload is None:
            return

        if isinstance(payload, str):
            try:
                pcm = base64.b64decode(payload)
            except Exception:
                return
        elif isinstance(payload, (bytes, bytearray)):
            pcm = bytes(payload)
        else:
            return

        if pcm:
            manager.push_audio(sid, pcm)