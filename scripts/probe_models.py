"""列出帳號可見的模型，並針對 generateContent 做最小驗證。"""
from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

load_dotenv()
KEY = os.getenv("GEMINI_API_KEY")
print("KEY length:", len(KEY or ""))

# 1) 列出模型
for v in ("v1beta", "v1alpha"):
    url = f"https://generativelanguage.googleapis.com/{v}/models?key={KEY}"
    r = requests.get(url, timeout=15)
    print(f"\n=== {v} models (status={r.status_code}) ===")
    if r.status_code != 200:
        print(r.text[:500])
        continue
    data = r.json()
    live = [m["name"] for m in data.get("models", []) if "live" in m["name"].lower()]
    flash3 = [m["name"] for m in data.get("models", []) if "3.1" in m["name"]]
    print("Live models:", *live, sep="\n  ")
    print("Gemini 3.1 models:", *flash3, sep="\n  ")

# 2) 用 generateContent 驗證金鑰
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={KEY}"
r = requests.post(url, json={"contents": [{"parts": [{"text": "ping"}]}]}, timeout=20)
print("\n=== generateContent gemini-2.5-flash ===")
print("status:", r.status_code)
print(r.text[:300])
