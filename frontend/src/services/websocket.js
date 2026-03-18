/**
 * WebSocket client for live microphone transcription.
 * Returns an object with send(), close(), and an onMessage callback setter.
 */
export function createLiveSocket(language = 'auto', onMessage, onError, onClose) {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const url = `${protocol}://${location.host}/ws/transcribe-live?language=${language}`
  const ws = new WebSocket(url)
  ws.binaryType = 'arraybuffer'

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
    send: (bytes) => ws.readyState === WebSocket.OPEN && ws.send(bytes),
    close: () => ws.close(),
  }
}
