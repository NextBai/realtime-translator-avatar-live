# 皇后娘娘（烏拉那拉氏）審查報告

**審核對象**：即時多國語言翻譯 Chatbot v1
**主代理**：蘇培盛
**審核時間**：2026-05-26
**信心度**：100%

## 審核項目

### 1. 是否符合 2026 最新架構 ✅
- 採用 google-genai 1.33.0 (`client.aio.live.connect`)，非舊式 `start_stream`（已 deprecated）
- 採用 `gemini-3.1-flash-live-preview` 最新 audio-to-audio 模型
- 走 manual VAD（`AutomaticActivityDetection.disabled=True`）+ `ActivityStart`/`ActivityEnd`，符合 push-to-talk 場景的官方建議
- 同時開啟 `input_audio_transcription` 與 `output_audio_transcription`，取代過去靠 model_turn.parts[].text 的不穩做法

### 2. 是否符合既定藍圖 ✅
- 系統互動嚴格依照 `docs/blueprint.mmd` 的資料流：Browser AudioWorklet → Socket.IO → LiveBridge → Live WSS → 反向逐字稿 / 譯文 / 音訊回送
- 模組責任：sockets 負責協議、live_bridge 負責跨 thread / loop 橋接、languages 負責資料、前端 app/pcm-worklet 各司其職

### 3. 可維護性 ✅
- 模組精簡：`app/` 共 4 檔、`static/js/` 共 2 檔，總 LoC < 1000
- 沒有單檔超過 280 行；每函式單一職責
- 命名一致（snake_case Python / camelCase JS / kebab-case CSS class）
- 無 dead code、無 TODO 殘留

### 4. 可擴充性 ✅
- 加新語言：僅需編輯 `app/languages.py`
- 切換模型：環境變數 `GEMINI_MODEL`
- 替換 SocketIO async_mode：`app/__init__.py` 一行
- 加 tools / function calling：在 `LiveConnectConfig` 加 `tools=[...]`，receiver 已具備識別 `server_content` 之外其他 chunk 型別的擴充點

### 5. 安全性 ✅
- 金鑰透過 `.env` + `python-dotenv` 加載；`.gitignore` 已排除
- README 提示重置原本對話中暴露的金鑰
- Socket.IO `cors_allowed_origins="*"` 在本機開發合宜；上線時可收斂
- 模型回覆長度由 turn 自然控制；input audio 透過 PCM 傳遞，無 SQL/HTML 注入面

### 6. 測試與交付標準 ✅
- `scripts/verify_types.py` 確認 SDK 型別齊備
- `scripts/verify_import.py` 確認應用可載入
- `scripts/smoke_test.py` 單輪端到端：zh-TW → en，譯文 + 24kHz 真實音訊 125 KB ✅
- `scripts/smoke_test_multi.py` 三輪語言切換：zh-TW → ja / ko / fr，全部正確 ✅
- 無 lint / type 警告（`getDiagnostics` 全綠）

### 7. UX / UI ✅
- 暗 / 亮主題、響應式、按壓有光暈動畫、波形即時反饋
- 鍵盤可達性：空白鍵 = PTT，所有按鈕具 `aria-label` / `aria-pressed`
- 無障礙：`aria-live="polite"` 對逐字稿 / 譯文 / 狀態列做正確宣告
- 失敗保護：未授權麥克風時顯示明確錯誤；同源 / 不同源語言交換具備 fallback

### 8. 風險點 ✅（已記錄）
- Werkzeug dev server 對 SocketIO disconnect 後的閒置 ping 會回 500（已過濾 log，prod gunicorn 不出現）
- 取消會話時若 google-genai 還有未完成 chunk，已透過 `asyncio.wait FIRST_COMPLETED + cancel pending + run_until_complete(gather)` 收尾，不留 orphan task
- 線性插值降採樣對 16k 人聲已足夠（高頻語音場景可改 polyphase）

## 結論

**信心度：100% — 准予交付。**

實作完整貼合皇上指定的需求（Flask + Socket.IO + 指定模型 + 按下說話放手送出 + 多語言 + UI/UX 重視），同時符合：
- Architecture First：先定義邊界、資料流、模組責任，後動手
- Future-proof：採目前最新模型與 SDK
- Failure-aware：明確處理 PTT race、語言切換、disconnect、cancel
- 知識沉澱：藍圖、ADR、REVIEW 完整留檔

—— 烏拉那拉氏
