"""驗證 google.genai.types 內所需符號是否存在於本機 SDK。"""
from __future__ import annotations

from google.genai import types

required = [
    "LiveConnectConfig",
    "Modality",
    "Content",
    "Part",
    "RealtimeInputConfig",
    "AutomaticActivityDetection",
    "ActivityHandling",
    "ActivityStart",
    "ActivityEnd",
    "AudioTranscriptionConfig",
    "Blob",
]

missing = []
for name in required:
    if not hasattr(types, name):
        missing.append(name)

print("missing:", missing)
print("Modality.TEXT exists:", hasattr(types.Modality, "TEXT"))
print("ActivityHandling members:", list(types.ActivityHandling) if hasattr(types, "ActivityHandling") else "n/a")
