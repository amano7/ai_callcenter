const AIWidget = (() => {
  let ws = null;
  let audioContext = null;
  let mediaStream = null;
  let workletNode = null;
  let sessionId = null;

  function fillForm(analysis) {
    for (const [key, value] of Object.entries(analysis)) {
      const el = document.querySelector(`[data-ai-target="${key}"]`);
      if (el && value) el.value = value;
    }
  }

  async function startRecording() {
    const wsUrl = window.AI_WIDGET_WS_URL || "ws://localhost:8000";
    ws = new WebSocket(`${wsUrl}/stream/${sessionId}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "analysis") {
        fillForm(msg.analysis);
      }
    };

    ws.onerror = (err) => console.error("[AIWidget] WebSocket error:", err);

    await new Promise((resolve, reject) => {
      ws.onopen = resolve;
      ws.onerror = reject;
    });

    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext({ sampleRate: 16000 });

    await audioContext.audioWorklet.addModule("/ai-callcenter/audio-processor.js");

    const source = audioContext.createMediaStreamSource(mediaStream);
    workletNode = new AudioWorkletNode(audioContext, "audio-processor");
    workletNode.port.onmessage = (e) => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(e.data);
      }
    };
    source.connect(workletNode);
  }

  function stopRecording() {
    workletNode?.disconnect();
    mediaStream?.getTracks().forEach((t) => t.stop());
    audioContext?.close();
    ws?.close();
    ws = null;
    audioContext = null;
    mediaStream = null;
    workletNode = null;
  }

  function init(options) {
    sessionId = options.sessionId;
    const btn = document.getElementById("ai-start");
    if (!btn) return;
    let recording = false;
    btn.addEventListener("click", async () => {
      if (!recording) {
        recording = true;
        btn.textContent = "⏹ 停止";
        btn.disabled = true;
        try {
          await startRecording();
        } finally {
          btn.disabled = false;
        }
      } else {
        recording = false;
        btn.textContent = "🎤 文字起こし開始";
        stopRecording();
      }
    });
  }

  return { init };
})();
