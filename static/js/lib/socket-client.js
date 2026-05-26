// Socket.IO client 包裝，統一連線 / 事件訂閱
let socket = null;
const listeners = new Map();

export function initSocket() {
  if (socket) return socket;

  socket = io({ transports: ["websocket"] });

  // 內建事件監聽
  socket.on("connect", () => {
    dispatch("socket:connect");
  });
  socket.on("disconnect", () => {
    dispatch("socket:disconnect");
  });
  socket.on("connect_error", (e) => {
    dispatch("socket:error", e);
  });

  // 轉發伺服器事件
  const serverEvents = [
    "hello",
    "status",
    "transcript",
    "translation",
    "turn_complete",
    "audio_response_chunk",
  ];
  serverEvents.forEach((ev) => {
    socket.on(ev, (data) => {
      dispatch(ev, data);
    });
  });

  return socket;
}

export function getSocket() {
  return socket;
}

export function isConnected() {
  return socket && socket.connected;
}

export function emit(event, data) {
  if (socket && socket.connected) {
    socket.emit(event, data);
  }
}

export function on(event, callback) {
  if (!listeners.has(event)) {
    listeners.set(event, []);
  }
  listeners.get(event).push(callback);
}

export function off(event, callback) {
  if (!listeners.has(event)) return;
  const cbs = listeners.get(event);
  const idx = cbs.indexOf(callback);
  if (idx !== -1) cbs.splice(idx, 1);
}

function dispatch(event, data) {
  if (!listeners.has(event)) return;
  listeners.get(event).forEach((cb) => cb(data));
}

// 便利方法
export function setLanguages(source, target) {
  emit("set_languages", { source, target });
}

export function sessionInit(source, target) {
  emit("session_init", { source, target });
}

export function pttStart() {
  emit("ptt_start");
}

export function pttEnd() {
  emit("ptt_end");
}

export function sendAudioChunk(pcmBase64) {
  emit("audio_chunk", { pcm: pcmBase64 });
}