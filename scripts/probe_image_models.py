"""探測 Gemini image generation 是否在皇上的 API key 下可用。"""
from __future__ import annotations
import base64, os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
KEY = os.getenv("GEMINI_API_KEY")

candidates = [
    "gemini-3.1-flash-image-preview",
    "gemini-3.1-flash-image",
    "imagen-4.0-generate-001",
    "imagen-3.0-generate-002",
]

client = genai.Client(api_key=KEY)
out = Path("static/avatars")
out.mkdir(parents=True, exist_ok=True)

for m in candidates:
    print(f"\n=== try {m} ===")
    try:
        resp = client.models.generate_content(
            model=m,
            contents="A simple red apple on white background, photorealistic.",
            config=types.GenerateContentConfig(response_modalities=["IMAGE", "TEXT"]),
        )
        # 嘗試解析回傳
        ok = False
        for part in resp.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                data = part.inline_data.data
                mime = part.inline_data.mime_type
                ext = mime.split("/")[-1] if mime else "png"
                Path(out / f"_probe_{m}.{ext}").write_bytes(data)
                print(f"  OK: got {len(data)} bytes ({mime})")
                ok = True
                break
        if not ok:
            print(f"  no inline_data; text: {(resp.text or '')[:120]}")
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {str(exc)[:200]}")
