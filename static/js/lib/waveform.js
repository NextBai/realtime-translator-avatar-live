// WaveformRenderer 類別，封裝 canvas 繪製
export class WaveformRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    if (!this.canvas) {
      throw new Error(`Canvas element #${canvasId} not found`);
    }
    this.ctx = this.canvas.getContext("2d");
    this.dpr = window.devicePixelRatio || 1;
    this.buf = null;
    this.accent = null;

    // 初始化尺寸
    this.resize();
    window.addEventListener("resize", () => this.resize());
  }

  resize() {
    const { clientWidth, clientHeight } = this.canvas;
    this.canvas.width = clientWidth * this.dpr;
    this.canvas.height = clientHeight * this.dpr;
    this.w = this.canvas.width;
    this.h = this.canvas.height;
  }

  setAnalyser(analyser) {
    this.analyser = analyser;
    this.buf = new Uint8Array(analyser.frequencyBinCount);
  }

  setPressing(isPressing) {
    this.isPressing = isPressing;
  }

  draw() {
    if (!this.analyser || !this.buf) return;

    const { ctx, w, h, buf, dpr } = this;
    ctx.clearRect(0, 0, w, h);
    this.analyser.getByteTimeDomainData(buf);

    // 取得 accent 顏色
    if (!this.accent) {
      this.accent =
        getComputedStyle(document.documentElement)
          .getPropertyValue("--accent")
          .trim() || "#7c5cff";
    }

    ctx.lineWidth = 2 * dpr;
    ctx.strokeStyle = this.isPressing ? this.accent : "rgba(124,92,255,0.45)";
    ctx.beginPath();

    const slice = w / buf.length;
    let x = 0;
    for (let i = 0; i < buf.length; i++) {
      const v = buf[i] / 128.0;
      const y = (v * h) / 2;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
      x += slice;
    }
    ctx.stroke();
  }
}