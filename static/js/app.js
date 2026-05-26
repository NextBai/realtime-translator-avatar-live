// 主程式：Avatar Live - 自動偵測來源 + 真人 Avatar + 口型同步
import {
  initSocket,
  on,
  setLanguages,
  sessionInit,
  pttStart,
  pttEnd,
  sendAudioChunk,
} from "./lib/socket-client.js";
import { ensureMic, resumeAudio, cleanup } from "./lib/audio-context.js";
import { AvatarController } from "./lib/avatar-sync.js";
import {
  initCardModule,
  setLanguagesInfo,
  updateCurrentLangs,
  pushBubble,
  speak,
  setStatus,
  ingestAudioChunk,
  clearAudioBuffer,
  flushAudioBuffer,
  arrayBufferToBase64,
} from "./lib/translation-card.js";

(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const els = {
    src: $("#srcLang"),
    tgt: $("#tgtLang"),
    targetBtn: $("#targetLangBtn"),
    targetValue: $("#targetLangValue"),
    historyBtn: $("#historyBtn"),
    historyCount: $("#historyCount"),
    historyList: $("#historyList"),

    avatarFrame: $("#avatarFrame"),
    avatarImg: $("#avatarImg"),
    avatarMouth: $("#avatarMouth")?.querySelector(".avatar-mouth__shape"),
    avatarFlag: $("#avatarFlag"),
    avatarLang: $("#avatarLang"),

    translationDisplay: $("#translationDisplay"),
    liveTranscript: $("#liveTranscript"),
    liveTranslation: $("#liveTranslation"),

    ptt: $("#pttBtn"),
    pttHint: $("#pttHint"),
    status: $("#statusPill"),
    theme: $("#themeBtn"),
    model: $("#modelTag"),
    bubbleTpl: $("#bubbleTpl"),

    langModal: $("#langModal"),
    langModalList: $("#langModalList"),
    historyModal: $("#historyModal"),
  };

  const avatarCtrl = new AvatarController({
    frame: els.avatarFrame,
    img: els.avatarImg,
    mouth: els.avatarMouth,
    flag: els.avatarFlag,
    langName: els.avatarLang,
  });

  // 翻譯卡片模組（專為歷史 modal 用）
  initCardModule({
    convo: els.historyList,
    empty: els.historyList.querySelector(".empty-state"),
    bubbleTpl: els.bubbleTpl,
    status: els.status,
  });

  const state = {
    languages: [],
    src: "auto",  // 永遠 auto
    tgt: localStorage.getItem("ptt.tgt") || "zh-TW",
    pressing: false,
    sessionReady: false,
    historyCount: 0,
    activeModal: null,
  };

  // -------------------- Theme --------------------
  const savedTheme = localStorage.getItem("ptt.theme");
  if (savedTheme) document.documentElement.setAttribute("data-theme", savedTheme);
  els.theme.addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme");
    const next = cur === "light" ? "" : "light";
    if (next) document.documentElement.setAttribute("data-theme", next);
    else document.documentElement.removeAttribute("data-theme");
    localStorage.setItem("ptt.theme", next);
  });

  // -------------------- Status pill (auto-fade) --------------------
  let statusFadeTimer = null;
  function showStatus(text, kind, autoHide = false) {
    setStatus(els.status, text, kind);
    els.status.classList.add("is-visible");
    if (statusFadeTimer) clearTimeout(statusFadeTimer);
    if (autoHide) {
      statusFadeTimer = setTimeout(() => {
        els.status.classList.remove("is-visible");
      }, 2200);
    }
  }
  function hideStatus() {
    els.status.classList.remove("is-visible");
  }

  // -------------------- Language --------------------
  function labelOf(code) {
    const f = state.languages.find((l) => l.code === code);
    return f ? f.label : code;
  }

  function refreshLangDisplay() {
    if (els.targetValue) els.targetValue.textContent = labelOf(state.tgt);
    avatarCtrl.setLanguage(state.tgt);
  }

  function fillNativeSelect(select, current, includeAuto = true) {
    if (!select) return;
    select.innerHTML = "";
    state.languages
      .filter((l) => includeAuto || l.code !== "auto")
      .forEach((lang) => {
        const opt = document.createElement("option");
        opt.value = lang.code;
        opt.textContent = lang.label;
        if (lang.code === current) opt.selected = true;
        select.appendChild(opt);
      });
  }

  function notifyLanguageChange() {
    localStorage.setItem("ptt.tgt", state.tgt);
    updateCurrentLangs(state.src, state.tgt);
    refreshLangDisplay();
    setLanguages(state.src, state.tgt);
    showStatus(`切換為 ${labelOf(state.tgt)}…`, "warn", true);
  }

  // -------------------- Modal helpers --------------------
  function openModal(modal) {
    state.activeModal = modal;
    modal.hidden = false;
    document.body.style.overflow = "hidden";
  }
  function closeModal(modal) {
    modal.hidden = true;
    if (state.activeModal === modal) state.activeModal = null;
    document.body.style.overflow = "";
  }

  // -------------------- Lang picker --------------------
  function openLangPicker() {
    const list = els.langModalList;
    list.innerHTML = "";
    // 排除 auto（因為 source 永遠 auto，這裡只選 target）
    state.languages
      .filter((l) => l.code !== "auto")
      .forEach((lang) => {
        const li = document.createElement("li");
        li.className = "lang-option";
        li.setAttribute("role", "option");
        li.setAttribute("tabindex", "0");
        li.dataset.code = lang.code;
        if (lang.code === state.tgt) li.setAttribute("aria-selected", "true");

        const ext = ["zh-TW", "zh-CN", "en", "ja", "ko"].includes(lang.code) ? "webp" : "jpg";
        li.innerHTML = `
          <img class="lang-option__avatar" src="/static/avatars/${lang.code}.${ext}" alt="" loading="lazy" />
          <div class="lang-option__name">
            <strong>${lang.label}</strong>
            <span>${lang.native || ""}</span>
          </div>
          <svg class="lang-option__check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        `;
        const select = () => {
          state.tgt = lang.code;
          closeModal(els.langModal);
          notifyLanguageChange();
        };
        li.addEventListener("click", select);
        li.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            select();
          }
        });
        list.appendChild(li);
      });
    openModal(els.langModal);
  }

  els.targetBtn?.addEventListener("click", openLangPicker);
  document.addEventListener("click", (e) => {
    if (e.target.matches("[data-close]")) {
      const modal = e.target.closest(".modal");
      if (modal) closeModal(modal);
    }
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && state.activeModal) closeModal(state.activeModal);
  });

  // -------------------- History --------------------
  els.historyBtn?.addEventListener("click", () => openModal(els.historyModal));

  function bumpHistoryCount() {
    state.historyCount++;
    if (els.historyCount) {
      els.historyCount.textContent = String(state.historyCount);
      els.historyCount.hidden = false;
    }
  }

  // -------------------- Socket events --------------------
  function initSocketEvents() {
    on("socket:connect", () => showStatus("已連線", "good", true));
    on("socket:disconnect", () => {
      showStatus("已斷線", "bad");
      state.sessionReady = false;
    });
    on("socket:error", (e) => showStatus("連線失敗：" + e.message, "bad"));

    on("hello", (payload) => {
      state.languages = payload.languages || [];
      els.model.textContent = payload.model || "Gemini Live";
      avatarCtrl.setLanguagesInfo(state.languages);
      setLanguagesInfo(state.languages, state.src, state.tgt);
      fillNativeSelect(els.src, state.src, true);
      fillNativeSelect(els.tgt, state.tgt, false);
      refreshLangDisplay();
      sessionInit(state.src, state.tgt);
    });

    on("status", (s) => {
      switch (s.state) {
        case "connecting":
          showStatus("連線 Live API…", "warn");
          break;
        case "ready":
          showStatus("就緒", "good", true);
          state.sessionReady = true;
          break;
        case "listening":
          showStatus("聆聽中…", "listen");
          els.translationDisplay.classList.add("is-streaming");
          els.liveTranscript.textContent = "";
          els.liveTranslation.textContent = "";
          break;
        case "translating":
          showStatus("翻譯中…", "warn");
          break;
        case "error":
          showStatus("錯誤：" + (s.message || "未知"), "bad");
          break;
      }
    });

    on("transcript", (t) => {
      els.liveTranscript.textContent = t.text || "";
    });

    on("translation", (t) => {
      els.liveTranslation.textContent = t.text || "";
    });

    on("turn_complete", (t) => {
      els.translationDisplay.classList.remove("is-streaming");
      if (t.skipped) {
        showStatus("未偵測到語音", "warn", true);
        clearAudioBuffer();
        els.liveTranscript.textContent = "";
        els.liveTranslation.textContent = "準備好就按住下方按鈕說話 ↓";
        return;
      }
      // 拿到完整 audio blob，啟動 Avatar 說話 + 口型同步
      const audioUrl = flushAudioBuffer();
      if (audioUrl) {
        avatarCtrl.speak(audioUrl).catch((e) => console.warn("speak failed:", e));
      }
      // 寫入歷史（不顯示在主畫面，譯文已在 translation-display 中）
      pushBubble(t.transcript || "", t.translation || "", audioUrl);
      bumpHistoryCount();
      // 主畫面保留譯文（直到下次按 PTT）
      els.liveTranscript.textContent = t.transcript || "";
      els.liveTranslation.textContent = t.translation || "";
      hideStatus();
    });

    on("audio_response_chunk", (chunk) => ingestAudioChunk(chunk.pcm));
  }

  // -------------------- PTT --------------------
  async function onAudioChunk(pcm) {
    if (!state.pressing || !state.sessionReady) return;
    sendAudioChunk(arrayBufferToBase64(pcm));
  }

  async function pttDown(e) {
    if (e) e.preventDefault();
    if (state.pressing) return;
    if (!state.sessionReady) {
      showStatus("尚未就緒…", "warn", true);
      return;
    }
    try {
      await ensureMic(onAudioChunk, () => {});
      await resumeAudio();
      state.pressing = true;
      els.ptt.setAttribute("aria-pressed", "true");
      els.pttHint.textContent = "鬆開翻譯";
      pttStart();
    } catch (err) {
      showStatus("無法取得麥克風", "bad");
    }
  }
  function pttUp(e) {
    if (e) e.preventDefault();
    if (!state.pressing) return;
    state.pressing = false;
    els.ptt.setAttribute("aria-pressed", "false");
    els.pttHint.textContent = "按住說話";
    pttEnd();
  }

  els.ptt.addEventListener("pointerdown", pttDown);
  els.ptt.addEventListener("pointerup", pttUp);
  els.ptt.addEventListener("pointercancel", pttUp);
  els.ptt.addEventListener("pointerleave", (e) => {
    if (state.pressing) pttUp(e);
  });

  // 空白鍵
  let spaceHeld = false;
  document.addEventListener("keydown", (e) => {
    if (e.code === "Space" && !spaceHeld && !isTypingTarget(e.target) && !state.activeModal) {
      spaceHeld = true;
      e.preventDefault();
      pttDown();
    }
  });
  document.addEventListener("keyup", (e) => {
    if (e.code === "Space" && spaceHeld) {
      spaceHeld = false;
      e.preventDefault();
      pttUp();
    }
  });
  function isTypingTarget(el) {
    return el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA" || el.isContentEditable);
  }

  // -------------------- Init --------------------
  function init() {
    initSocketEvents();
    initSocket();
  }

  window.addEventListener("beforeunload", () => {
    cleanup();
    avatarCtrl.destroy();
  });

  init();
})();
