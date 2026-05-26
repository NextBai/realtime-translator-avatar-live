"""Session management - 將 _Session 與生命週期管理從 live_bridge.py 提取出來。"""
from __future__ import annotations

import asyncio
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import logging

logger = logging.getLogger("live_bridge.session")


@dataclass
class Session:
    """內部狀態：單一 sid 的會話。

    職責：
    - 儲存 session 基本資訊（sid, 語言）
    - 提供 asyncio event loop 與 daemon thread
    - 維護 inbox queue 給外部投遞訊息
    - 追蹤建立時間與 main_task 參照
    """

    sid: str
    source_lang: str
    target_lang: str
    loop: asyncio.AbstractEventLoop
    thread: threading.Thread
    inbox: asyncio.Queue = field(default_factory=asyncio.Queue)
    started: float = field(default_factory=time.time)
    main_task: Optional[asyncio.Task] = None
    auto_reconnect: bool = True
    reconnect_delay: float = 3.0  # seconds


class SessionManager:
    """管理所有 Session 生命週期。

    負責：
    - 建立 / 銷毀 Session
    - 提供 thread-safe 的 session 存取
    - 支援 auto_reconnect 機制
    """

    def __init__(self, socketio: Any) -> None:
        self._socketio = socketio
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._reconnect_tasks: dict[str, asyncio.Task] = {}

    @property
    def sessions(self) -> dict[str, Session]:
        """取得所有 session（用於唯讀操作）。"""
        return self._sessions

    def get(self, sid: str) -> Optional[Session]:
        """取得指定 sid 的 session。"""
        with self._lock:
            return self._sessions.get(sid)

    def add(self, session: Session) -> None:
        """加入新的 session。"""
        with self._lock:
            self._sessions[session.sid] = session
        logger.debug("[%s] session added", session.sid)

    def remove(self, sid: str) -> Optional[Session]:
        """移除並回傳 session。"""
        with self._lock:
            return self._sessions.pop(sid, None)

    def has(self, sid: str) -> bool:
        """檢查 session 是否存在。"""
        with self._lock:
            return sid in self._sessions

    def schedule_reconnect(self, sid: str) -> None:
        """排程自動重連（3 秒後）。"""
        # 避免重複排程
        with self._lock:
            if sid in self._reconnect_tasks:
                return
            # 取得當前 reconnect 設定（在移除 session 之前）
            sess = self._sessions.get(sid)
            if not sess or not sess.auto_reconnect:
                return
            # 複製需要的資訊
            reconnect_delay = sess.reconnect_delay
            source_lang = sess.source_lang
            target_lang = sess.target_lang

        def reconnect() -> None:
            logger.info("[%s] attempting auto-reconnect after %.1fs", sid, reconnect_delay)
            time.sleep(reconnect_delay)
            # 觸發重新連線 - 發送 reconnect 事件讓 handler 處理
            self._socketio.emit("reconnect", {"source": source_lang, "target": target_lang}, to=sid)

        task = threading.Thread(target=reconnect, daemon=True, name=f"reconnect-{sid[:6]}")
        task.start()
        with self._lock:
            self._reconnect_tasks[sid] = task  # type: ignore[assignment]

    def clear_reconnect(self, sid: str) -> None:
        """清除重連排程。"""
        with self._lock:
            self._reconnect_tasks.pop(sid, None)

    def emit(self, sid: str, event: str, payload: dict[str, Any]) -> None:
        """透過 Socket.IO 發送事件到客戶端。"""
        try:
            self._socketio.emit(event, payload, to=sid)
        except Exception:
            logger.exception("[%s] emit %s failed", sid, event)

    def get_session_config(self, sid: str) -> tuple[str, str] | None:
        """取得 session 的語言設定，用於重新連線。"""
        with self._lock:
            sess = self._sessions.get(sid)
        if sess:
            return (sess.source_lang, sess.target_lang)
        return None