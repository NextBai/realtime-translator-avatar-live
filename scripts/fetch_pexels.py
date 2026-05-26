"""從 Pexels 抓取代表性人像。
Pexels 圖片授權 = 免費、可商用、無需署名（雖建議）。
這裡只用作 demo，不做商業散布。
所有 photo_id 都已人工驗證為合適的半身人像、深色背景、嘴部清晰可見。
"""
from __future__ import annotations
import urllib.request
from pathlib import Path

OUT = Path("static/avatars")
OUT.mkdir(parents=True, exist_ok=True)

# 已驗證可下載的 Pexels photo IDs（女性半身專業人像、清晰嘴部）
# Format: "language_code": (photo_id, photographer_slug)
PEXELS_PHOTOS = {
    # zh-TW/CN/en/ja/ko 已有 HF 生成的 webp，跳過
    "es":   "1382731",  # latina woman
    "fr":   "1239288",  # french woman
    "de":   "415829",   # blonde woman portrait
    "it":   "774909",   # italian-style woman
    "pt":   "1382726",  # brazilian
    "ru":   "1043471",  # blonde
    "vi":   "3621953",  # asian woman
    "th":   "1758144",  # thai-style
    "id":   "1138103",  # indonesian
    "ar":   "1181686",  # hijab woman
    "hi":   "1239291",  # indian woman
    "auto": "1181519",  # neutral assistant
}


def fetch(photo_id: str, out: Path) -> bool:
    # Pexels CDN 直連，使用 cropped/portrait 格式
    urls = [
        f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&cs=tinysrgb&fit=crop&w=600&h=600",
        f"https://images.pexels.com/photos/{photo_id}/pexels-photo-{photo_id}.jpeg?auto=compress&w=600",
    ]
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.pexels.com/",
            })
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
            if len(data) < 5000:
                continue
            out.write_bytes(data)
            return True
        except Exception as exc:
            print(f"    {url[:50]}... -> {exc}")
    return False


def main() -> None:
    for code, pid in PEXELS_PHOTOS.items():
        existing = OUT / f"{code}.webp"
        if existing.exists() and existing.stat().st_size > 10000:
            print(f"[{code}] keep existing")
            continue
        target = OUT / f"{code}.jpg"
        print(f"[{code}] fetch pexels {pid}...")
        if fetch(pid, target):
            print(f"  OK ({target.stat().st_size} bytes)")
        else:
            print(f"  FAIL")


if __name__ == "__main__":
    main()
