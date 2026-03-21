/**
 * WebSocket client for live microphone transcription.
 * Returns an object with send(), close(), and an onMessage callback setter.
 */
export function createLiveSocket(language = 'auto', onMessage, onError, onClose) {
  const url = import.meta.env.VITE_WS_BASE_URL
    ? `${import.meta.env.VITE_WS_BASE_URL}/ws/transcribe-live?language=${language}`
    : `wss://multi-lingual-transcription.onrender.com/ws/transcribe-live?language=${language}`
  const ws = new WebSocket(url)
  ws.binaryType = 'arraybuffer'

  // Buffer chunks sent while the socket is still connecting.
  // The first MediaRecorder chunk (250ms) contains the EBML/container header
  // and must not be dropped — without it the server gets headerless audio data.
  const _pending = []
  ws.onopen = () => {
    _pending.splice(0).forEach((chunk) => ws.send(chunk))
  }

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      onMessage(msg)
    } catch {
      /* ignore non-JSON frames */
    }
  }
  ws.onerror = (err) => onError && onError(err)
  ws.onclose = () => onClose && onClose()

  return {
    send: (bytes) => {
      if (ws.readyState === WebSocket.CONNECTING) {
        _pending.push(bytes)
      } else if (ws.readyState === WebSocket.OPEN) {
        ws.send(bytes)
      }
    },
    close: () => ws.close(),
  }
}
