"""列出 17 種語言對應的 Avatar prompt（皇上參考用）。
本腳本不直接呼叫 HF（由 agent 透過 MCP 並行呼叫），這裡只記錄 prompt。
"""
AVATAR_PROMPTS = {
    "auto": (
        "Professional studio portrait, half body shot, AI virtual assistant character, "
        "androgynous friendly digital person, soft holographic glow, futuristic look, "
        "lips closed naturally, clean dark gradient background, photorealistic, 8k"
    ),
    "zh-TW": "Friendly young Taiwanese woman, shoulder-length black hair, modern white blouse, slight smile, lips closed",
    "zh-CN": "Friendly young Chinese woman, long straight black hair, elegant red qipao with subtle patterns, gentle smile, lips closed",
    "en":    "Confident young American woman, blonde wavy hair, smart casual blue blazer over white shirt, warm smile, lips closed",
    "ja":    "Polite young Japanese woman, neat shoulder-length black hair, navy office blazer over white shirt, soft smile, lips closed",
    "ko":    "Stylish young Korean woman, long straight dark brown hair, modern beige knit sweater, calm smile, lips closed",
    "es":    "Warm young Spanish woman, dark wavy hair, red elegant blouse, expressive smile, lips closed",
    "fr":    "Elegant young French woman, brunette bob haircut, navy striped Breton shirt with silk scarf, subtle smile, lips closed",
    "de":    "Professional young German woman, blonde hair tied back, gray business turtleneck, confident expression, lips closed",
    "it":    "Cheerful young Italian woman, dark curly hair, cream linen blouse with gold accessories, warm smile, lips closed",
    "pt":    "Vibrant young Brazilian-Portuguese woman, brown curly hair, green tropical print top, big smile, lips closed",
    "ru":    "Sophisticated young Russian woman, light blonde hair, white turtleneck with subtle pearl earrings, calm expression, lips closed",
    "vi":    "Graceful young Vietnamese woman, long black hair, traditional white ao dai with delicate embroidery, gentle smile, lips closed",
    "th":    "Polite young Thai woman, dark hair in elegant updo, soft purple silk traditional top, serene smile, lips closed",
    "id":    "Warm young Indonesian woman, dark hair with batik headband, batik print blouse, friendly smile, lips closed",
    "ar":    "Dignified young Middle-Eastern woman, dark hair with elegant beige hijab, modern beige modest blouse, calm smile, lips closed",
    "hi":    "Beautiful young Indian woman, long dark hair, royal blue saree with gold border, small bindi, warm smile, lips closed",
}

COMMON_SUFFIX = (
    ", professional studio portrait photography, half body shot framing chest up, "
    "looking directly at camera, soft studio lighting, clean dark gradient background "
    "(navy to deep purple), sharp focus on face, mouth area neutral and clearly visible, "
    "photorealistic, 8k, centered composition"
)

if __name__ == "__main__":
    for code, p in AVATAR_PROMPTS.items():
        print(f"=== {code} ===")
        print(p + COMMON_SUFFIX)
        print()
