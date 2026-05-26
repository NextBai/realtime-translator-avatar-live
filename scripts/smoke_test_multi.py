"""多輪 + 切換語言端到端測試。"""
from __future__ import annotations

import base64
import os
import threading
import time

import socketio

from smoke_test import synthesize_zh_speech, to_16k_pcm  # type: ignore


def main() -> None:
    pcm = to_16k_pcm(synthesize_zh_speech())
    print(f"PCM ready: {len(pcm)} bytes")

    sio = socketio.Client(logger=False)
    turns: list[dict] = []
    barrier = threading.Event()

    @sio.event
    def connect():
        print("[client] connected")
        sio.emit("session_init", {"source": "zh-TW", "target": "ja"})

    @sio.on("status")
    def status(s):
        if s.get("state") == "ready":
            barrier.set()

    @sio.on("turn_complete")
    def turn_complete(t):
        print(f"[turn] {t}")
        turns.append(t)

    def push_round():
        barrier.clear()
        # 等 ready
        if not barrier.wait(timeout=15):
            raise RuntimeError("not ready")
        sio.emit("ptt_start")
        chunk = 16000 * 2 * 80 // 1000
        for i in range(0, len(pcm), chunk):
            sio.emit("audio_chunk", {"pcm": base64.b64encode(pcm[i:i + chunk]).decode()})
            time.sleep(0.07)
        sio.emit("ptt_end")
        # 等 turn 完成
        deadline = time.time() + 30
        target = len(turns) + 1
        while len(turns) < target and time.time() < deadline:
            time.sleep(0.1)

    sio.connect("http://127.0.0.1:5000", transports=["websocket"])
    push_round()  # 中文 → 日文
    print("--- switching to zh-TW → ko ---")
    sio.emit("set_languages", {"source": "zh-TW", "target": "ko"})
    push_round()
    print("--- switching to zh-TW → fr ---")
    sio.emit("set_languages", {"source": "zh-TW", "target": "fr"})
    push_round()
    sio.disconnect()
    print("ALL TURNS:")
    for i, t in enumerate(turns, 1):
        print(f"  {i}. transcript={t.get('transcript')!r} translation={t.get('translation')!r}")


if __name__ == "__main__":
    main()
