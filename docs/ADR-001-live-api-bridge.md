# ADR-001 — Flask-SocketIO ↔ Gemini Live API 橋接策略

- 狀態：Accepted
- 日期：2026-05-26
- 主導：蘇培盛  ｜  審核：皇后娘娘

## Context
Gemini Live API 為 stateful WebSocket，僅提供 async client（`client.aio.live.connect`）。
Flask-SocketIO 同時支援 threading / eventlet / gevent 三種 async_mode，需挑選與 `google-genai` async + gRPC 不衝突的方案。

## Options
| 方案 | 描述 | 優點 | 缺點 |
| --- | --- | --- | --- |
| A. eventlet + asyncio | 用 eventlet patch 後跑 asyncio loop | 與舊 Flask 教學一致 | eventlet 對 gRPC、SSL、Python 3.12 monkey patch 有已知問題，會造成 Live API hang |
| B. **threading + per-sid asyncio thread**（採用） | Flask-SocketIO 用 threading 模式；每個 sid 開一條 daemon thread 跑獨立 asyncio loop，loop 內持續 `connect()` Live session | 與 google-genai 完全相容；單會話隔離乾淨；可水平擴展 | 需自寫 thread/loop 生命週期管理 |
| C. ASGI（Quart + python-socketio） | 全 async 改寫 | 原生 async；無橋接成本 | 偏離皇上指定的 Flask；改寫面大 |

## Decision
採用 **方案 B**：Flask-SocketIO `async_mode='threading'`，每個連線於背景 thread 啟動 `asyncio.new_event_loop()` 並維持 `client.aio.live.connect(...)` 的 async context。
SocketIO event handler 透過 `asyncio.run_coroutine_threadsafe()` 將音訊封包推入 `asyncio.Queue`；接收端用獨立 task 從 `session.receive()` 拉取訊息後以 `socketio.emit()` 回送瀏覽器。

## Tradeoffs
- 多一條 thread / 連線：CPU 與記憶體成本可控（音訊小，主要等 IO）。
- thread 與 SocketIO callback 之間需明確 lifecycle 管理（`disconnect` 時送 sentinel 並 join）。

## Consequences
- 前端押住按鈕一次 = 一個 PTT 回合：發 `activity_start` → 多個 audio chunk → `activity_end` + `audio_stream_end=False`（手動模式下我們只送 activity_end）。
- 後端對每段語音呼叫 `send_realtime_input(activity_start=...)` / `send_realtime_input(audio=Blob(...))` / `send_realtime_input(activity_end=...)` 三段式。
- response 透過 `server_content.input_transcription` 取原文逐字稿，`server_content.model_turn.parts[].text` 取譯文。

## Related
- Blueprint: docs/blueprint.mmd
- Task: 即時翻譯 chatbot v1
