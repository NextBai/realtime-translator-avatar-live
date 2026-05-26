"""驗證 app 能正確 import 並建立 (不啟動 server)。"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 給一個假 key 避免 manager warning
os.environ.setdefault("GEMINI_API_KEY", "dummy")

from app import create_app  # noqa: E402

app, sio, mgr = create_app()
print("Flask app:", app.name)
print("SocketIO async_mode:", sio.async_mode)
print("LiveBridge model:", mgr.model)
print("OK")
