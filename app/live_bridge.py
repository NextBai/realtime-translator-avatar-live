"""LiveBridge — 將 Flask-SocketIO（threaded）橋接到 Gemini Live async 會話。

每一個 Socket.IO sid 皆對應一條 daemon thread，於該 thread 中啟動獨立的
asyncio event loop，並開啟一個 `client.aio.live.connect(...)` 會話。
SocketIO callback 透過 `asyncio.run_coroutine_threadsafe` 將事件投遞到 loop。

協議（PTT, push-to-talk）：
  使用者按下 → 前端送 `ptt_start` → 後端 `activity_start`
  錄音中     → 前端持續送 `audio_chunk`（PCM 16-bit/16kHz/LE） → 後端 `send_realtime_input(audio=Blob(...))`
  使用者放開 → 前端送 `ptt_end` → 後端 `activity_end`，等待 `turn_complete`
"""
from __future__ import annotations

import asyncio
import base64
import logging
import threading
import time
from typing import Any, Optional

from flask_socketio import SocketIO
from google import genai
from google.genai import types

from .languages import label_of
from .session import Session, SessionManager

logger = logging.getLogger("live_bridge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

AUDIO_MIME = "audio/pcm;rate=16000"
RECONNECT_DELAY = 3.0  # seconds


def _build_system_instruction(target: str) -> str:
    """產生系統提示詞 — 自動偵測來源，要求只翻譯到目標語言。

    模型會自動辨識所有 17 種語言（與更多）。
    我們不需要在 prompt 裡明說 source，因為 Gemini Live 自動處理多語輸入。
    """
    tgt = label_of(target)
    return (
        "You are a professional simultaneous interpreter for a push-to-talk translator app.\n"
        f"Detect the language the user speaks automatically, then translate every utterance into {tgt} "
        "and SPEAK the translation aloud.\n"
        "STRICT RULES:\n"
        f"1. Speak ONLY in {tgt}. Output ONLY the translated sentence — no greetings, no explanations, no quotes.\n"
        "2. Preserve the speaker's tone (formal, casual, question, exclamation).\n"
        "3. Keep proper nouns, numbers, dates, and code-mixed terms intact.\n"
        "4. If the audio is silent or contains no intelligible speech, stay silent and do not respond.\n"
        "5. Never add filler words like 'sure', 'okay', 'translation:'. Just deliver the translated sentence.\n"
        "6. If the user already speaks the target language, still repeat / paraphrase faithfully — do not refuse."
    )


class LiveBridgeManager:
    """管理所有 sid 對應的 Live 會話。"""

    def __init__(self, socketio: SocketIO, api_key: str, model: str) -> None:
        if not api_key:
            logger.warning("GEMINI_API_KEY 未設定，啟動後將無法連線 Live API")
        self.socketio = socketio
        self.api_key = api_key
        self.model = model
        self._session_manager = SessionManager(socketio)

    @property
    def sessions(self) -> dict[str, Session]:
        """取得所有 session（用於唯讀操作）。"""
        return self._session_manager.sessions

    # ------------------------------------------------------------------ public

    def start(self, sid: str, source_lang: str, target_lang: str) -> None:
        """為指定 sid 啟動 Live 會話。"""
        self.stop(sid)  # 若有舊的，先收乾淨

        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=self._thread_main,
            args=(loop, sid, source_lang, target_lang),
            name=f"live-{sid[:6]}",
            daemon=True,
        )

        session = Session(
            sid=sid,
            source_lang=source_lang,
            target_lang=target_lang,
            loop=loop,
            thread=thread,
            auto_reconnect=True,
            reconnect_delay=RECONNECT_DELAY,
        )
        self._session_manager.add(session)
        thread.start()
        logger.info("[%s] live session thread started (src=%s, tgt=%s)", sid, source_lang, target_lang)

    def stop(self, sid: str) -> None:
        """停止指定 sid 的會話。"""
        # 清除重連排程
        self._session_manager.clear_reconnect(sid)

        session = self._session_manager.remove(sid)
        if not session:
            return

        # 使用 TaskGroup 取消模式：直接取消主 task
        def _cancel_main() -> None:
            if session.main_task and not session.main_task.done():
                session.main_task.cancel()

        try:
            session.loop.call_soon_threadsafe(_cancel_main)
        except RuntimeError:
            pass  # loop 已關

        # 給 3 秒讓 loop 自行收尾
        session.thread.join(timeout=3.0)
        if session.loop.is_running():
            try:
                session.loop.call_soon_threadsafe(session.loop.stop)
            except Exception:
                pass
        logger.info("[%s] live session stopped", sid)

    def restart(self, sid: str) -> None:
        """重新啟動會話（用於 auto_reconnect）。"""
        config = self._session_manager.get_session_config(sid)
        if config:
            src, tgt = config
            self.start(sid, src, tgt)
            logger.info("[%s] session restarted for auto_reconnect", sid)

    def update_languages(self, sid: str, source_lang: str, target_lang: str) -> None:
        """切換語言：因 system_instruction 是建立連線時鎖定的，需重啟會話。"""
        logger.info("[%s] language change → src=%s, tgt=%s (restart session)", sid, source_lang, target_lang)
        self.start(sid, source_lang, target_lang)

    def ptt_start(self, sid: str) -> None:
        self._post(sid, {"type": "ptt_start"})

    def ptt_end(self, sid: str) -> None:
        self._post(sid, {"type": "ptt_end"})

    def push_audio(self, sid: str, pcm_bytes: bytes) -> None:
        self._post(sid, {"type": "audio", "data": pcm_bytes})

    # ----------------------------------------------------------------- helpers

    def _post(self, sid: str, msg: dict[str, Any]) -> None:
        session = self._session_manager.get(sid)
        if not session:
            logger.debug("[%s] ignore %s — no session", sid, msg.get("type"))
            return
        coro = self._enqueue(session, msg)
        try:
            asyncio.run_coroutine_threadsafe(coro, session.loop)
        except RuntimeError as exc:
            coro.close()
            logger.warning("[%s] post failed: %s", sid, exc)

    @staticmethod
    async def _enqueue(session: Session, msg: dict[str, Any]) -> None:
        await session.inbox.put(msg)

    # ------------------------------------------------------------------ thread

    def _thread_main(
        self,
        loop: asyncio.AbstractEventLoop,
        sid: str,
        src: str,
        tgt: str,
    ) -> None:
        asyncio.set_event_loop(loop)
        try:
            session = self._session_manager.get(sid)
            if not session:
                return
            main_coro = self._run_session(sid, src, tgt)
            main_task = loop.create_task(main_coro, name=f"live-main-{sid[:6]}")
            session.main_task = main_task
            try:
                loop.run_until_complete(main_task)
            except asyncio.CancelledError:
                pass
            # TaskGroup 處理後的收尾
            try:
                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                for t in pending:
                    t.cancel()
                if pending:
                    loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
        except Exception:  # noqa: BLE001
            logger.exception("[%s] live thread crashed", sid)
        finally:
            # 檢查是否需要 auto_reconnect
            session = self._session_manager.get(sid)
            should_reconnect = session is not None and session.auto_reconnect

            try:
                loop.close()
            except Exception:
                pass

            if should_reconnect:
                # session 已被 remove，在 stop 時已經處理
                # 這裡是正常結束（非主動停止）的情況
                logger.info("[%s] session ended, scheduling auto_reconnect", sid)
                self._session_manager.schedule_reconnect(sid)

    async def _run_session(self, sid: str, src: str, tgt: str) -> None:
        session = self._session_manager.get(sid)
        if not session:
            return

        client = genai.Client(api_key=self.api_key)

        config = types.LiveConnectConfig(
            response_modalities=[types.Modality.AUDIO],
            system_instruction=_build_system_instruction(tgt),
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(disabled=True),
                activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
            ),
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
        )

        self._emit(sid, "status", {"state": "connecting", "model": self.model})
        try:
            async with client.aio.live.connect(model=self.model, config=config) as api_session:
                self._emit(sid, "status", {"state": "ready"})

                # 使用 asyncio.TaskGroup 重構取消邏輯
                async with asyncio.TaskGroup() as tg:
                    send_task = tg.create_task(
                        self._sender(session, api_session),
                        name="sender",
                    )
                    recv_task = tg.create_task(
                        self._receiver(session, api_session),
                        name="receiver",
                    )
                    # TaskGroup 會自動等待所有任務完成
                    # 任務被取消時，TaskGroup 會傳播 CancelledError

        except asyncio.CancelledError:
            # 這裡是主動取消，不需要額外處理
            raise
        except Exception as exc:  # noqa: BLE001
            logger.exception("[%s] live api error", sid)
            self._emit(sid, "status", {"state": "error", "message": str(exc)})

    async def _sender(self, session: Session, api_session: Any) -> None:
        in_turn = False
        try:
            while True:
                msg = await session.inbox.get()
                kind = msg["type"]
                if kind == "ptt_start":
                    if not in_turn:
                        await api_session.send_realtime_input(
                            activity_start=types.ActivityStart()
                        )
                        in_turn = True
                        self._emit(session.sid, "status", {"state": "listening"})
                elif kind == "audio" and in_turn:
                    await api_session.send_realtime_input(
                        audio=types.Blob(data=msg["data"], mime_type=AUDIO_MIME),
                    )
                elif kind == "ptt_end":
                    if in_turn:
                        await api_session.send_realtime_input(
                            activity_end=types.ActivityEnd()
                        )
                        in_turn = False
                        self._emit(session.sid, "status", {"state": "translating"})
        except asyncio.CancelledError:
            if in_turn:
                try:
                    await api_session.send_realtime_input(
                        activity_end=types.ActivityEnd()
                    )
                except Exception:
                    pass
            raise

    async def _receiver(self, session: Session, api_session: Any) -> None:
        current_translation: list[str] = []
        current_input: list[str] = []
        current_audio: list[bytes] = []
        async for chunk in api_session.receive():
            sc = getattr(chunk, "server_content", None)
            if sc is not None:
                in_tx = getattr(sc, "input_transcription", None)
                if in_tx and getattr(in_tx, "text", None):
                    current_input.append(in_tx.text)
                    self._emit(session.sid, "transcript", {
                        "text": "".join(current_input),
                        "final": False,
                    })
                out_tx = getattr(sc, "output_transcription", None)
                if out_tx and getattr(out_tx, "text", None):
                    current_translation.append(out_tx.text)
                    self._emit(session.sid, "translation", {
                        "text": "".join(current_translation),
                        "final": False,
                    })
                model_turn = getattr(sc, "model_turn", None)
                if model_turn and getattr(model_turn, "parts", None):
                    for part in model_turn.parts:
                        inline = getattr(part, "inline_data", None)
                        if inline and getattr(inline, "data", None):
                            current_audio.append(inline.data)
                            self._emit(session.sid, "audio_response_chunk", {
                                "pcm": base64.b64encode(inline.data).decode("ascii"),
                                "mime": getattr(inline, "mime_type", "audio/pcm;rate=24000"),
                            })
                if getattr(sc, "turn_complete", False):
                    final_translation = "".join(current_translation).strip()
                    final_input = "".join(current_input).strip()
                    if not final_translation or final_translation == "[no_speech]":
                        self._emit(session.sid, "turn_complete", {
                            "skipped": True,
                            "reason": "no_speech",
                        })
                    else:
                        self._emit(session.sid, "turn_complete", {
                            "translation": final_translation,
                            "transcript": final_input,
                        })
                    current_translation.clear()
                    current_input.clear()
                    current_audio.clear()
                    self._emit(session.sid, "status", {"state": "ready"})

    # ------------------------------------------------------------------- emit

    def _emit(self, sid: str, event: str, payload: dict[str, Any]) -> None:
        try:
            self.socketio.emit(event, payload, to=sid)
        except Exception:  # noqa: BLE001
            logger.exception("[%s] emit %s failed", sid, event)