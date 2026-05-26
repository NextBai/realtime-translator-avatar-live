"""即時多國語言翻譯 Chatbot — Flask + Socket.IO + Gemini Live API。"""
from __future__ import annotations

import mimetypes
import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, render_template
from flask_socketio import SocketIO

from .live_bridge import LiveBridgeManager

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Windows registry 常把 .js 識別為 text/plain，導致 ES module import 失敗。
# 強制註冊正確的 MIME types，與 ES module / WASM / SourceMap 規範一致。
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("application/javascript", ".mjs")
mimetypes.add_type("text/css", ".css")
mimetypes.add_type("application/wasm", ".wasm")
mimetypes.add_type("application/json", ".map")


def create_app() -> tuple[Flask, SocketIO, LiveBridgeManager]:
    app = Flask(
        __name__,
        template_folder=str(ROOT / "templates"),
        static_folder=str(ROOT / "static"),
    )
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET", "dev-secret")

    socketio = SocketIO(
        app,
        async_mode="threading",
        cors_allowed_origins="*",
        max_http_buffer_size=4 * 1024 * 1024,
        ping_interval=20,
        ping_timeout=30,
        logger=False,
        engineio_logger=False,
    )

    # 抑制 werkzeug dev server 在 simple-websocket disconnect 之後對閒置 ping
    # 拋出的 "write() before start_response" 噪音 log，不影響 client 行為
    import logging
    werk_logger = logging.getLogger("werkzeug")

    class _SuppressWrite(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
            msg = record.getMessage()
            return "write() before start_response" not in msg

    werk_logger.addFilter(_SuppressWrite())

    manager = LiveBridgeManager(
        socketio=socketio,
        api_key=os.getenv("GEMINI_API_KEY", ""),
        model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-live-preview"),
    )

    from . import sockets  # noqa: WPS433  匯入時註冊 SocketIO handlers
    sockets.register(socketio, manager)

    @app.route("/")
    def index():  # type: ignore[unused-ignore]
        return render_template("index.html")

    @app.route("/healthz")
    def healthz():  # type: ignore[unused-ignore]
        return {"status": "ok", "model": manager.model}

    return app, socketio, manager
