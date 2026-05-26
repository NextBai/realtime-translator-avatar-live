// 泡泡卡片產生與管理
let languages = [];
let srcLang = "auto";
let tgtLang = "en";

// DOM 元素快取
let els = {};

export function initCardModule(elements) {
  els = elements;
}

export function setLanguagesInfo(langs, src, tgt) {
  languages = langs;
  srcLang = src;
  tgtLang = tgt;
}

export function updateCurrentLangs(src, tgt) {
  srcLang = src;
  tgtLang = tgt;
}

function labelOf(code) {
  const f = languages.find((l) => l.code === code);
  return f ? f.label : code;
}

export function pushBubble(transcript, translation, audioUrl) {
  if (els.empty) els.empty.style.display = "none";

  const node = els.bubbleTpl.content.firstElementChild.cloneNode(true);
  // 新的 tag 結構：用語言代碼當 tag (例如 zh-TW, en)
  node.querySelector(".bubble__src-tag").textContent =
    srcLang === "auto" ? "auto" : srcLang;
  node.querySelector(".bubble__tgt-tag").textContent = tgtLang;
  node.querySelector(".bubble__time").textContent = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  node.querySelector(".bubble__transcript").textContent = transcript || "（無原文）";
  node.querySelector(".bubble__translation").textContent = translation;

  // 複製譯文按鈕
  node.querySelector(".bubble__copy").addEventListener("click", () => {
    navigator.clipboard.writeText(translation).then(() => {
      if (els.status) flashStatus(els.status, "已複製譯文", "good");
    });
  });

  // 朗讀按鈕
  const speakBtn = node.querySelector(".bubble__speak");
  speakBtn.addEventListener("click", () => {
    if (audioUrl) {
      const a = new Audio(audioUrl);
      a.play().catch(() => speak(translation, tgtLang));
    } else {
      speak(translation, tgtLang);
    }
  });

  // 自動播放音頻
  if (audioUrl) {
    const a = new Audio(audioUrl);
    a.play().catch(() => {
      /* 自動播放被擋；按鈕仍可手動播 */
    });
  }

  els.convo.appendChild(node);
  els.convo.scrollTop = els.convo.scrollHeight;
}

export function speak(text, lang) {
  if (!("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang === "zh-TW" ? "zh-TW" : lang === "zh-CN" ? "zh-CN" : lang;
  speechSynthesis.cancel();
  speechSynthesis.speak(u);
}

function flashStatus(statusEl, text, kind) {
  if (!statusEl) return;
  const prev = { text: flashStatusText(statusEl), kind: getStatusKind(statusEl) };
  setStatus(statusEl, text, kind);
  setTimeout(() => setStatus(statusEl, prev.text, prev.kind), 1200);
}

function getStatusKind(statusEl) {
  return ["good", "warn", "bad", "listen"].find((k) =>
    statusEl.classList.contains("is-" + k)
  ) || null;
}

export function setStatus(statusEl, text, kind) {
  if (!statusEl) return;
  // 新 HTML 結構：status-pill 內含 .status-pill__text 子節點
  const textEl = statusEl.querySelector(".status-pill__text");
  if (textEl) textEl.textContent = text;
  else statusEl.textContent = text;
  statusEl.classList.remove("is-good", "is-warn", "is-bad", "is-listen");
  if (kind) statusEl.classList.add("is-" + kind);
}

function flashStatusText(statusEl) {
  const textEl = statusEl.querySelector(".status-pill__text");
  return textEl ? textEl.textContent : statusEl.textContent;
}

// -------------------- Output audio assembly --------------------
// 模型回傳 24kHz 16-bit PCM，多塊累積；turn_complete 時包成 WAV 一次播放
let audioChunks = []; // Uint8Array[]

export function ingestAudioChunk(b64) {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  audioChunks.push(arr);
}

export function clearAudioBuffer() {
  audioChunks = [];
}

export function flushAudioBuffer() {
  if (!audioChunks.length) return null;
  let total = 0;
  for (const c of audioChunks) total += c.length;
  const pcm = new Uint8Array(total);
  let off = 0;
  for (const c of audioChunks) {
    pcm.set(c, off);
    off += c.length;
  }
  audioChunks = [];
  const wav = pcmToWav(pcm, 24000, 1);
  return URL.createObjectURL(new Blob([wav], { type: "audio/wav" }));
}

function pcmToWav(pcmBytes, sampleRate, channels) {
  const blockAlign = channels * 2;
  const byteRate = sampleRate * blockAlign;
  const dataSize = pcmBytes.length;
  const buffer = new ArrayBuffer(44 + dataSize);
  const dv = new DataView(buffer);
  let p = 0;
  function w(s) {
    for (let i = 0; i < s.length; i++) dv.setUint8(p++, s.charCodeAt(i));
  }
  function u32(v) {
    dv.setUint32(p, v, true);
    p += 4;
  }
  function u16(v) {
    dv.setUint16(p, v, true);
    p += 2;
  }
  w("RIFF");
  u32(36 + dataSize);
  w("WAVE");
  w("fmt ");
  u32(16);
  u16(1);
  u16(channels);
  u32(sampleRate);
  u32(byteRate);
  u16(blockAlign);
  u16(16);
  w("data");
  u32(dataSize);
  new Uint8Array(buffer, 44).set(pcmBytes);
  return buffer;
}

// 將 ArrayBuffer 轉 Base64
export function arrayBufferToBase64(buf) {
  const bytes = new Uint8Array(buf);
  let bin = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    bin += String.fromCharCode.apply(null, bytes.subarray(i, i + chunkSize));
  }
  return btoa(bin);
}