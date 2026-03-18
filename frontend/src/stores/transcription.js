import { defineStore } from 'pinia'
import { ref } from 'vue'
import { uploadVideo, transcribeUrl, pollStatus } from '../services/api.js'

export const useTranscriptionStore = defineStore('transcription', () => {
  const jobId = ref(null)
  const status = ref(null)   // null | 'processing' | 'completed' | 'error'
  const step = ref('')
  const progress = ref(null)
  const title = ref('')
  const results = ref([])
  const txt = ref('')
  const srt = ref('')
  const error = ref('')
  const uploadProgress = ref(0)

  let _pollTimer = null

  function reset() {
    stopPolling()
    jobId.value = null
    status.value = null
    step.value = ''
    progress.value = null
    title.value = ''
    results.value = []
    txt.value = ''
    srt.value = ''
    error.value = ''
    uploadProgress.value = 0
  }

  async function submitFile(file, language) {
    reset()
    status.value = 'processing'
    step.value = 'Uploading…'
    try {
      const data = await uploadVideo(file, language, (e) => {
        if (e.total) uploadProgress.value = Math.round((e.loaded / e.total) * 100)
      })
      jobId.value = data.job_id
      startPolling()
    } catch (e) {
      status.value = 'error'
      error.value = e.response?.data?.detail || e.message || 'Upload failed.'
    }
  }

  async function submitUrl(url, language) {
    reset()
    status.value = 'processing'
    step.value = 'Queuing…'
    try {
      const data = await transcribeUrl(url, language)
      jobId.value = data.job_id
      startPolling()
    } catch (e) {
      status.value = 'error'
      error.value = e.response?.data?.detail || e.message || 'Request failed.'
    }
  }

  function startPolling() {
    stopPolling()
    _pollTimer = setInterval(async () => {
      if (!jobId.value) return stopPolling()
      try {
        const data = await pollStatus(jobId.value)
        if (data.status === 'processing') {
          step.value = data.step || 'Processing…'
          progress.value = data.progress ?? null
          title.value = data.title || ''
        } else if (data.status === 'completed') {
          stopPolling()
          status.value = 'completed'
          results.value = data.results || []
          txt.value = data.txt || ''
          srt.value = data.srt || ''
          title.value = data.title || ''
        } else if (data.status === 'error') {
          stopPolling()
          status.value = 'error'
          error.value = data.error || 'An unknown error occurred.'
          title.value = data.title || ''
        }
      } catch (e) {
        stopPolling()
        status.value = 'error'
        error.value = 'Lost connection to server.'
      }
    }, 2000)
  }

  function stopPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
  }

  return {
    jobId, status, step, progress, title,
    results, txt, srt, error, uploadProgress,
    submitFile, submitUrl, reset,
  }
})
