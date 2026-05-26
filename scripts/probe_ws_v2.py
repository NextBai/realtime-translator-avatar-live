"""針對 gemini-3.1-flash-live-preview，嘗試各種最小 setup payload。"""
from __future__ import annotations

import asyncio
import json
import os

import websockets
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("GEMINI_API_KEY")
MODEL = "gemini-3.1-flash-live-preview"


async def probe(label: str, setup: dict, api: str = "v1beta") -> str:
    url = (
        f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage."
        f"{api}.GenerativeService.BidiGenerateContent?key={KEY}"
    )
    try:
        async with asyncio.timeout(15):
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps({"setup": setup}))
                resp = await ws.recv()
                return f"OK | {resp[:300]}"
    except Exception as exc:  # noqa: BLE001
        return f"FAIL | {str(exc)[:200]}"


async def main() -> None:
    base = {"model": f"models/{MODEL}"}
    cases = [
        ("bare", base),
        ("audio modality", {**base, "generation_config": {"response_modalities": ["AUDIO"]}}),
        ("text modality", {**base, "generation_config": {"response_modalities": ["TEXT"]}}),
        ("audio + voice", {**base, "generation_config": {"response_modalities": ["AUDIO"], "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": "Puck"}}}}}),
        ("system instruction string", {**base, "system_instruction": {"parts": [{"text": "be a translator"}]}, "generation_config": {"response_modalities": ["AUDIO"]}}),
        ("input transcription enabled", {**base, "generation_config": {"response_modalities": ["AUDIO"]}, "input_audio_transcription": {}}),
        ("output transcription enabled", {**base, "generation_config": {"response_modalities": ["AUDIO"]}, "output_audio_transcription": {}}),
        ("manual VAD disabled", {**base, "generation_config": {"response_modalities": ["AUDIO"]}, "realtime_input_config": {"automatic_activity_detection": {"disabled": True}}}),
        ("everything", {**base, "generation_config": {"response_modalities": ["AUDIO"]}, "input_audio_transcription": {}, "output_audio_transcription": {}, "realtime_input_config": {"automatic_activity_detection": {"disabled": True}}, "system_instruction": {"parts": [{"text": "Translate to English."}]}}),
    ]
    for label, setup in cases:
        for api in ("v1beta", "v1alpha"):
            print(f"[{api:8s}|{label:32s}] -> {await probe(label, setup, api)}")


if __name__ == "__main__":
    asyncio.run(main())
