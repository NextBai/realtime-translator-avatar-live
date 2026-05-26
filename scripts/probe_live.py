"""探測：不同 model × api_version × 設定 的可用組合。"""
from __future__ import annotations

import asyncio
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
KEY = os.getenv("GEMINI_API_KEY")


async def try_connect(model: str, api_version: str | None, manual: bool, audio_tx: bool) -> str:
    http_options = types.HttpOptions(api_version=api_version) if api_version else None
    client = genai.Client(api_key=KEY, http_options=http_options)
    config_kwargs = {
        "response_modalities": [types.Modality.TEXT],
        "system_instruction": "You are a translator. Reply with only the translation.",
    }
    if manual:
        config_kwargs["realtime_input_config"] = types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(disabled=True),
        )
    if audio_tx:
        config_kwargs["input_audio_transcription"] = types.AudioTranscriptionConfig()
    config = types.LiveConnectConfig(**config_kwargs)
    try:
        async with asyncio.timeout(20):
            async with client.aio.live.connect(model=model, config=config) as _:
                return "OK"
    except Exception as exc:  # noqa: BLE001
        return f"FAIL: {exc.__class__.__name__}: {exc}"


async def main() -> None:
    cases = [
        ("gemini-3.1-flash-live-preview", None,        False, False),
        ("gemini-3.1-flash-live-preview", "v1alpha",   False, False),
        ("gemini-3.1-flash-live-preview", "v1beta",    False, False),
        ("gemini-3.1-flash-live-preview", "v1alpha",   True,  True),
        ("gemini-3.1-flash-live-preview", "v1beta",    True,  True),
        ("gemini-live-2.5-flash-preview", None,        False, False),
        ("gemini-live-2.5-flash-preview", "v1beta",    True,  True),
        ("gemini-live-2.5-flash-preview", "v1alpha",   True,  True),
    ]
    for model, api, manual, tx in cases:
        result = await try_connect(model, api, manual, tx)
        print(f"[{model:38s}|{api or 'default':8s}|manual={manual}|tx={tx}] -> {result[:160]}")


if __name__ == "__main__":
    asyncio.run(main())
