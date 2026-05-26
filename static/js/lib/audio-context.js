// AudioContext 與 AudioWorklet 管理
let audioCtx = null;
let workletNode = null;
let micStream = null;
let sourceNode = null;
let analyser = null;
let rafId = null;

export function getAnalyser() {
  return analyser;
}

export function getAudioContext() {
  return audioCtx;
}

export async function ensureMic(onAudioChunk, drawWaveFn) {
  if (audioCtx && workletNode) return true;
  try {
    const AC = window.AudioContext || window.webkitAudioContext;
    const ctx = new AC({ latencyHint: "interactive" });
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    await ctx.audioWorklet.addModule("/static/js/pcm-worklet.js");
    const src = ctx.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(ctx, "pcm-downsampler", {
      numberOfInputs: 1,
      numberOfOutputs: 0,
      channelCount: 1,
      processorOptions: { targetRate: 16000, frameMs: 80 },
    });

    const analyserNode = ctx.createAnalyser();
    analyserNode.fftSize = 1024;
    src.connect(analyserNode);
    src.connect(node);

    node.port.onmessage = (ev) => {
      const { pcm, peak } = ev.data;
      if (onAudioChunk) {
        onAudioChunk(pcm, peak);
      }
    };

    audioCtx = ctx;
    workletNode = node;
    micStream = stream;
    sourceNode = src;
    analyser = analyserNode;

    if (drawWaveFn) {
      drawWave(drawWaveFn);
    }
    return true;
  } catch (err) {
    console.error(err);
    throw err;
  }
}

function drawWave(drawWaveFn) {
  const loop = () => {
    rafId = requestAnimationFrame(loop);
    drawWaveFn();
  };
  if (!rafId) loop();
}

export function cancelRaf() {
  if (rafId) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
}

export function resumeAudio() {
  if (audioCtx && audioCtx.state === "suspended") {
    return audioCtx.resume();
  }
  return Promise.resolve();
}

export function cleanup() {
  cancelRaf();
  if (micStream) {
    micStream.getTracks().forEach((t) => t.stop());
    micStream = null;
  }
  if (sourceNode) {
    sourceNode.disconnect();
    sourceNode = null;
  }
  if (workletNode) {
    workletNode.port.close();
    workletNode.disconnect();
    workletNode = null;
  }
  if (analyser) {
    analyser.disconnect();
    analyser = null;
  }
  if (audioCtx) {
    audioCtx.close();
    audioCtx = null;
  }
}