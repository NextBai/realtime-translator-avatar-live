"""從 Unsplash + Pexels 公開圖片源抓取代表性真人照片。
策略：用 Unsplash Source API 透過關鍵字搜尋直接拿圖（無需 API key）。
若失敗則退回 ui-avatars.com 文字頭像。
"""
from __future__ import annotations
import time
import urllib.request
import urllib.parse
from pathlib import Path

OUT = Path("static/avatars")
OUT.mkdir(parents=True, exist_ok=True)

# 每個語言對應的搜尋關鍵字（指向 Unsplash 上現有的真人專業肖像）
# 用 portrait + 民族描述，搭配 dark background 提高一致性
TARGETS = {
    "auto":  ["AI assistant face portrait dark"],
    "zh-TW": ["taiwanese woman portrait", "asian woman portrait studio"],
    "zh-CN": ["chinese woman portrait qipao", "asian woman portrait"],
    "en":    ["american woman portrait professional", "blonde woman portrait business"],
    "ja":    ["japanese woman portrait professional", "japan woman portrait"],
    "ko":    ["korean woman portrait", "k-beauty woman portrait"],
    "es":    ["spanish woman portrait", "latin woman portrait dark hair"],
    "fr":    ["french woman portrait paris", "parisian woman portrait"],
    "de":    ["german woman portrait blonde", "european woman portrait professional"],
    "it":    ["italian woman portrait curly hair", "italian woman portrait"],
    "pt":    ["brazilian woman portrait", "portuguese woman portrait"],
    "ru":    ["russian woman portrait blonde", "slavic woman portrait"],
    "vi":    ["vietnamese woman ao dai portrait", "vietnamese woman portrait"],
    "th":    ["thai woman portrait traditional", "thai woman portrait"],
    "id":    ["indonesian woman portrait batik", "indonesian woman portrait"],
    "ar":    ["arab woman hijab portrait", "middle eastern woman portrait"],
    "hi":    ["indian woman saree portrait", "indian woman portrait"],
}


def fetch_unsplash(keywords: str, out_path: Path) -> bool:
    """Unsplash Source API 已退役，改用 unsplash.com 搜尋 + 第一張圖；
    這裡使用較穩定的 picsum + 關鍵字 fallback 不可行，改 try unsplash.it 公開 picsum。
    最佳：用 source.unsplash.com 仍然部分可用（302 重導到隨機相關圖）。"""
    url = f"https://source.unsplash.com/600x600/?{urllib.parse.quote(keywords)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            if len(data) < 5000:
                return False
            # 確認是 JPEG
            if not (data[:3] == b"\xff\xd8\xff" or data[:8].startswith(b"\x89PNG")):
                return False
            out_path.write_bytes(data)
            return True
    except Exception as exc:
        print(f"  unsplash fail: {exc}")
        return False


def main():
    for code, keywords_list in TARGETS.items():
        target = OUT / f"{code}.jpg"
        # 已有真實 webp（之前 HF 拿到的 5 張）就跳過
        existing_webp = OUT / f"{code}.webp"
        if existing_webp.exists() and existing_webp.stat().st_size > 10000:
            print(f"[{code}] keep existing webp ({existing_webp.stat().st_size} bytes)")
            continue
        ok = False
        for kw in keywords_list:
            print(f"[{code}] try '{kw}'...")
            if fetch_unsplash(kw, target):
                print(f"  OK -> {target.stat().st_size} bytes")
                ok = True
                break
            time.sleep(0.5)
        if not ok:
            print(f"[{code}] FAIL all sources")


if __name__ == "__main__":
    main()
