import { defineStore } from 'pinia'
import { ref } from 'vue'
import { createLiveSocket } from '../services/websocket.js'

export const useLiveStore = defineStore('live', () => {
  const isRecording = ref(false)
  const isProcessing = ref(false)
  const transcript = ref('')
  const segments = ref([])
  const languageCode = ref('')
  const error = ref('')

  let _mediaRecorder = null
  let _socket = null
  let _stream = null

  function reset() {
    transcript.value = ''
    segments.value = []
    languageCode.value = ''
    error.value = ''
  }

  async function startRecording(language = 'auto') {
    reset()
    try {
      _stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      error.value = 'Microphone access denied. Please allow microphone permission.'
      return
    }

    _socket = createLiveSocket(
      language,
      (msg) => {
        isProcessing.value = false
        if (msg.type === 'final') {
          transcript.value = msg.transcript || ''
          segments.value = msg.segments || []
          languageCode.value = msg.language_code || ''
        } else if (msg.type === 'error') {
          error.value = msg.message || 'Transcription error.'
        }
        _socket?.close()  // close AFTER result is received
      },
      () => {
        isProcessing.value = false
        isRecording.value = false
        error.value = 'WebSocket connection error. Check that the backend is running on port 8001.'
      },
      () => {
        // Server closed the socket before we got a result
        if (isProcessing.value) {
          isProcessing.value = false
          isRecording.value = false
          error.value = 'Connection closed unexpectedly. Check backend is running and accessible.'
        }
      },
    )

    _mediaRecorder = new MediaRecorder(_stream)
    _mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) _socket.send(e.data)
    }
    _mediaRecorder.start(250) // send chunk every 250ms
    isRecording.value = true
  }

  function stopRecording() {
    if (!_mediaRecorder) return
    _stream?.getTracks().forEach((t) => t.stop())
    _mediaRecorder.onstop = () => {
      // Send empty frame as stop signal — keeps socket open for the result
      _socket?.send(new Uint8Array(0))
    }
    _mediaRecorder.stop()
    isRecording.value = false
    isProcessing.value = true
  }

  return {
    isRecording, isProcessing, transcript, segments, languageCode, error,
    startRecording, stopRecording, reset,
  }
})
