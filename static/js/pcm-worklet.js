// AudioWorkletProcessor：把瀏覽器原生 Float32 (一般 48kHz) 重採樣為 16kHz
// 並轉成 Int16 PCM little-endian，每 ~80ms 一封包送出。
class PCMDownsampler extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetRate = (options.processorOptions && options.processorOptions.targetRate) || 16000;
    this.frameMs = (options.processorOptions && options.processorOptions.frameMs) || 80;
    this.frameSamples = Math.round((this.targetRate * this.frameMs) / 1000); // e.g. 1280
    this.ratio = sampleRate / this.targetRate; // sampleRate is global in worklet
    this.acc = new Float32Array(0);
    this.outBuf = new Int16Array(this.frameSamples);
    this.outPos = 0;
    this.peak = 0;
  }

  // 線性插值降採樣（對人聲 16k 已足夠；耗時極低）
  resample(input) {
    const outLen = Math.floor(input.length / this.ratio);
    const out = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++) {
      const idx = i * this.ratio;
      const i0 = Math.floor(idx);
      const i1 = Math.min(i0 + 1, input.length - 1);
      const t = idx - i0;
      out[i] = input[i0] * (1 - t) + input[i1] * t;
    }
    return out;
  }

  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (!ch) return true;

    const down = this.resample(ch);
    let peak = 0;
    for (let i = 0; i < down.length; i++) {
      const v = down[i];
      const a = v < 0 ? -v : v;
      if (a > peak) peak = a;

      const s = Math.max(-1, Math.min(1, v));
      this.outBuf[this.outPos++] = s < 0 ? s * 0x8000 : s * 0x7fff;

      if (this.outPos === this.frameSamples) {
        // 封包送出
        const packet = this.outBuf.slice().buffer;
        this.port.postMessage({ pcm: packet, peak: peak }, [packet]);
        this.outBuf = new Int16Array(this.frameSamples);
        this.outPos = 0;
        peak = 0;
      }
    }
    return true;
  }
}

registerProcessor("pcm-downsampler", PCMDownsampler);
