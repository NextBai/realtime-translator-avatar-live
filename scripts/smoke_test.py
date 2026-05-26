"""端到端煙霧測試：用 Windows SAPI 合成一段中文語音，送到後端走完整流程，
驗證能否拿到 transcript / translation 與音訊回應。

需先啟動 `python run.py`。
"""
from __future__ import annotations

import base64
import os
import struct
import threading
import time
import wave

import socketio

WAV_PATH = os.path.join(os.path.dirname(__file__), "_speech_zh.wav")
PCM_PATH = os.path.join(os.path.dirname(__file__), "_speech_zh.pcm16k.raw")


def synthesize_zh_speech() -> str:
    """用 Windows SAPI 合成「你好，今天天氣很好」WAV (PCM 16-bit 22.05k mono)。"""
    if os.path.exists(WAV_PATH):
        return WAV_PATH
    import comtypes.client  # type: ignore
    voice = comtypes.client.CreateObject("SAPI.SpVoice")
    stream = comtypes.client.CreateObject("SAPI.SpFileStream")
    fmt = comtypes.client.CreateObject("SAPI.SpAudioFormat")
    fmt.Type = 22  # SAFT22kHz16BitMono
    stream.Format = fmt
    stream.Open(WAV_PATH, 3, False)  # SSFMCreateForWrite
    voice.AudioOutputStream = stream
    voice.Speak("你好，今天天氣很好。")
    stream.Close()
    return WAV_PATH


def to_16k_pcm(wav_path: str) -> bytes:
    """將任意 WAV 線性插值降取樣到 16kHz / 16-bit / mono。"""
    if os.path.exists(PCM_PATH):
        with open(PCM_PATH, "rb") as f:
            return f.read()
    with wave.open(wav_path, "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        n = w.getnframes()
        raw = w.readframes(n)
    assert sw == 2, "expected 16-bit"
    samples = list(struct.unpack("<" + "h" * (len(raw) // 2), raw))
    if ch == 2:
        # 取平均轉單聲
        mono = []
        for i in range(0, len(samples), 2):
            mono.append((samples[i] + samples[i + 1]) // 2)
        samples = mono
    target_sr = 16000
    ratio = sr / target_sr
    out_len = int(len(samples) / ratio)
    out = []
    for i in range(out_len):
        idx = i * ratio
        i0 = int(idx)
        i1 = min(i0 + 1, len(samples) - 1)
        t = idx - i0
        out.append(int(samples[i0] * (1 - t) + samples[i1] * t))
    pcm = struct.pack("<" + "h" * len(out), *out)
    with open(PCM_PATH, "wb") as f:
        f.write(pcm)
    return pcm


def main() -> None:
    wav = synthesize_zh_speech()
    pcm = to_16k_pcm(wav)
    print(f"prepared PCM: {len(pcm)} bytes ({len(pcm)/32000:.2f}s @16k mono)")

    sio = socketio.Client(logger=False)
    done = threading.Event()
    captured: dict = {"started": False, "turn": None, "audio_bytes": 0}

    @sio.event
    def connect():
        print("[client] connected")
        sio.emit("session_init", {"source": "zh-TW", "target": "en"})

    @sio.on("hello")
    def hello(data):
        print(f"[hello] model={data['model']} langs={len(data['languages'])}")

    @sio.on("status")
    def status(s):
        print(f"[status] {s}")
        if s.get("state") == "ready" and not captured["started"]:
            captured["started"] = True
            threading.Thread(target=run_ptt, daemon=True).start()

    @sio.on("transcript")
    def transcript(t):
        print(f"[transcript] {t.get('text')!r}")

    @sio.on("translation")
    def translation(t):
        print(f"[translation] {t.get('text')!r}")

    @sio.on("audio_response_chunk")
    def audio_response(c):
        try:
            captured["audio_bytes"] += len(base64.b64decode(c["pcm"]))
        except Exception:
            pass

    @sio.on("turn_complete")
    def turn_complete(t):
        print(f"[turn_complete] {t}")
        captured["turn"] = t
        done.set()

    def run_ptt():
        time.sleep(0.3)
        sio.emit("ptt_start")
        chunk = 16000 * 2 * 80 // 1000  # 80ms = 2560 bytes
        for i in range(0, len(pcm), chunk):
            sio.emit("audio_chunk", {"pcm": base64.b64encode(pcm[i:i + chunk]).decode()})
            time.sleep(0.07)
        sio.emit("ptt_end")
        print("[client] ptt_end sent")

    sio.connect("http://127.0.0.1:5000", transports=["websocket"])
    ok = done.wait(timeout=45)
    print()
    if ok:
        print(f"DONE turn={captured['turn']}, audio_bytes={captured['audio_bytes']}")
    else:
        print(f"TIMEOUT (got audio_bytes={captured['audio_bytes']})")
    sio.disconnect()


if __name__ == "__main__":
    main()
