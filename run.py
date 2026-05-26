"""Local entrypoint."""
from __future__ import annotations

import os

from app import create_app


def main() -> None:
    app, socketio, _ = create_app()
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    # allow_unsafe_werkzeug 僅供本機開發；上線請改用 gunicorn + eventlet 或 uvicorn 替代方案
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
