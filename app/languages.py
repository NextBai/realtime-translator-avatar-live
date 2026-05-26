"""支援語言清單，於前後端共用展示。"""
from __future__ import annotations

LANGUAGES: list[dict[str, str]] = [
    {"code": "auto", "label": "自動偵測", "native": "Auto detect"},
    {"code": "zh-TW", "label": "繁體中文", "native": "繁體中文"},
    {"code": "zh-CN", "label": "简体中文", "native": "简体中文"},
    {"code": "en", "label": "English", "native": "English"},
    {"code": "ja", "label": "日本語", "native": "日本語"},
    {"code": "ko", "label": "한국어", "native": "한국어"},
    {"code": "es", "label": "Español", "native": "Español"},
    {"code": "fr", "label": "Français", "native": "Français"},
    {"code": "de", "label": "Deutsch", "native": "Deutsch"},
    {"code": "it", "label": "Italiano", "native": "Italiano"},
    {"code": "pt", "label": "Português", "native": "Português"},
    {"code": "ru", "label": "Русский", "native": "Русский"},
    {"code": "vi", "label": "Tiếng Việt", "native": "Tiếng Việt"},
    {"code": "th", "label": "ภาษาไทย", "native": "ภาษาไทย"},
    {"code": "id", "label": "Bahasa Indonesia", "native": "Bahasa Indonesia"},
    {"code": "ar", "label": "العربية", "native": "العربية"},
    {"code": "hi", "label": "हिन्दी", "native": "हिन्दी"},
]


def label_of(code: str) -> str:
    for lang in LANGUAGES:
        if lang["code"] == code:
            return lang["label"]
    return code
