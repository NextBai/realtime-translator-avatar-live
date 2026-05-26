"""直接用 websockets 嘗試多個模型，取得首個 server 回應確認支援度。"""
from __future__ import annotations

import asyncio
import json
import os

import websockets
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("GEMINI_API_KEY")


async def probe(model: str, api: str) -> str:
    url = (
        f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage."
        f"{api}.GenerativeService.BidiGenerateContent?key={KEY}"
    )
    try:
        async with asyncio.timeout(10):
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps({
                    "setup": {
                        "model": f"models/{model}",
                        "generation_config": {"response_modalities": ["TEXT"]},
                    }
                }))
                resp = await ws.recv()
                return f"OK msg={resp[:160]}"
    except Exception as exc:  # noqa: BLE001
        return f"FAIL: {exc.__class__.__name__}: {str(exc)[:160]}"


async def main() -> None:
    candidates = [
        ("gemini-3.1-flash-live-preview", "v1beta"),
        ("gemini-3.1-flash-live-preview", "v1alpha"),
        ("gemini-live-2.5-flash-preview", "v1beta"),
        ("gemini-live-2.5-flash-preview", "v1alpha"),
        ("gemini-2.5-flash-preview-native-audio-dialog", "v1alpha"),
        ("gemini-2.0-flash-live-preview-04-09", "v1beta"),
        ("gemini-2.0-flash-live-001", "v1alpha"),
        ("gemini-2.5-flash-live-preview", "v1beta"),
    ]
    for m, v in candidates:
        print(f"[{m:46s}|{v}] -> {await probe(m, v)}")


if __name__ == "__main__":
    asyncio.run(main())
