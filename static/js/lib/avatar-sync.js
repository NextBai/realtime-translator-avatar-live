/**
 * Avatar 控制器：負責切換 Avatar 圖片、播放譯文音訊、口型同步動畫
 *
 * 口型同步原理：
 *   1. 將 turn_complete 時收到的 24kHz PCM Blob 餵給一個 <audio> + AudioContext + AnalyserNode
 *   2. requestAnimationFrame 內讀取 RMS 音量
 *   3. 將 RMS 映射到嘴部 SVG 的 scaleY（0.3 ~ 2.4）形成自然開合
 *   4. 同時切換 Avatar 為當前 target 語言對應的人物照片
 */

const FLAG_BY_LANG = {
  auto: "🌐",
  "zh-TW": "🇹🇼",
  "zh-CN": "🇨🇳",
  en: "🇺🇸",
  ja: "🇯🇵",
  ko: "🇰🇷",
  es: "🇪🇸",
  fr: "🇫🇷",
  de: "🇩🇪",
  it: "🇮🇹",
  pt: "🇵🇹",
  ru: "🇷🇺",
  vi: "🇻🇳",
  th: "🇹🇭",
  id: "🇮🇩",
  ar: "🇸🇦",
  hi: "🇮🇳",
};

// 已驗證可用的 avatar 副檔名（可以是 webp 或 jpg）
const AVATAR_EXT_BY_LANG = {
  "zh-TW": "webp",
  "zh-CN": "webp",
  en: "webp",
  ja: "webp",
  ko: "webp",
  // 其餘為 jpg（Pexels 抓取）
};

export class AvatarController {
  /**
   * @param {object} els
   * @param {HTMLElement} els.frame - .avatar-frame
   * @param {HTMLImageElement} els.img - .avatar-img
   * @param {SVGElement} els.mouth - .avatar-mouth__shape (ellipse)
   * @param {HTMLElement} els.flag - .avatar-badge__flag
   * @param {HTMLElement} els.langName - .avatar-badge__lang
   */
  constructor(els) {
    this.els = els;
    this.currentLang = null;
    this.languages = [];
    this.audioCtx = null;
    this.analyser = null;
    this.audioElem = null;
    this.mediaSource = null;
    this.rafId = null;
    this.smoothedVolume = 0;
  }

  setLanguagesInfo(languages) {
    this.languages = languages;
  }

  /** 切換 Avatar 圖片 */
  async setLanguage(code) {
    if (this.currentLang === code) return;
    this.currentLang = code;

    // 切換動畫：fade out → 換圖 → fade in
    this.els.frame.classList.add("is-switching");
    await new Promise((r) => setTimeout(r, 180));

    const ext = AVATAR_EXT_BY_LANG[code] || "jpg";
    this.els.img.src = `/static/avatars/${code}.${ext}`;
    this.els.img.alt = `${this._labelOf(code)} avatar`;

    // 等圖載入
    await new Promise((res) => {
      if (this.els.img.complete) return res();
      this.els.img.onload = () => res();
      this.els.img.onerror = () => res();
    });

    this.els.frame.classList.remove("is-switching");

    // 更新徽章
    this.els.flag.textContent = FLAG_BY_LANG[code] || "🌐";
    this.els.langName.textContent = this._labelOf(code);
  }

  _labelOf(code) {
    const lang = this.languages.find((l) => l.code === code);
    return lang ? lang.label : code;
  }

  /**
   * 播放 24kHz PCM blob 並驅動口型同步
   * @param {string} audioUrl - 由 PCM 包裝後的 WAV blob URL
   */
  async speak(audioUrl) {
    this._stopSpeaking();

    if (!audioUrl) return;

    // 建立或重用 AudioContext
    if (!this.audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      this.audioCtx = new AC();
    }
    if (this.audioCtx.state === "suspended") {
      await this.audioCtx.resume();
    }

    // 建立 audio element 並接到 analyser
    const audio = new Audio(audioUrl);
    audio.crossOrigin = "anonymous";
    this.audioElem = audio;

    const source = this.audioCtx.createMediaElementSource(audio);
    const analyser = this.audioCtx.createAnalyser();
    analyser.fftSize = 1024;
    analyser.smoothingTimeConstant = 0.6;
    source.connect(analyser);
    analyser.connect(this.audioCtx.destination);
    this.analyser = analyser;
    this.mediaSource = source;

    this.els.frame.classList.add("is-speaking");

    // 口型同步動畫
    const buffer = new Uint8Array(analyser.fftSize);
    const animate = () => {
      this.rafId = requestAnimationFrame(animate);
      analyser.getByteTimeDomainData(buffer);
      // 計算 RMS
      let sum = 0;
      for (let i = 0; i < buffer.length; i++) {
        const v = (buffer[i] - 128) / 128; // -1..1
        sum += v * v;
      }
      const rms = Math.sqrt(sum / buffer.length); // 0..~0.5

      // 映射 RMS 到 scaleY (0.4 ~ 2.6)
      const target = Math.min(2.6, 0.4 + rms * 12);
      // 平滑過渡
      this.smoothedVolume = this.smoothedVolume * 0.55 + target * 0.45;

      if (this.els.mouth) {
        this.els.mouth.style.transform = `scaleY(${this.smoothedVolume.toFixed(2)})`;
      }
    };
    animate();

    // 播放完畢 → 停止動畫
    audio.addEventListener("ended", () => this._stopSpeaking());
    audio.addEventListener("error", () => this._stopSpeaking());

    try {
      await audio.play();
    } catch (err) {
      console.warn("[avatar] auto-play blocked:", err);
      this._stopSpeaking();
    }
  }

  _stopSpeaking() {
    if (this.rafId) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
    this.smoothedVolume = 0;
    if (this.els.mouth) {
      this.els.mouth.style.transform = "scaleY(0.3)";
    }
    this.els.frame.classList.remove("is-speaking");
    if (this.audioElem) {
      try { this.audioElem.pause(); } catch (_) { /* ignore */ }
      this.audioElem.src = "";
      this.audioElem = null;
    }
    if (this.mediaSource) {
      try { this.mediaSource.disconnect(); } catch (_) { /* ignore */ }
      this.mediaSource = null;
    }
  }

  destroy() {
    this._stopSpeaking();
    if (this.audioCtx) {
      try { this.audioCtx.close(); } catch (_) { /* ignore */ }
      this.audioCtx = null;
    }
  }
}
