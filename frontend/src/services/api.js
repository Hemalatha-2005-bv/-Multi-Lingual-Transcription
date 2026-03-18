import axios from 'axios'

const BASE = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api'

const http = axios.create({
  baseURL: BASE,
  timeout: 0, // No timeout — large file uploads can take a long time
})

export async function uploadVideo(file, language = 'auto', onUploadProgress) {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post(`/upload-video?language=${language}`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  })
  return data // { job_id }
}

export async function transcribeUrl(url, language = 'auto') {
  const { data } = await http.post(`/transcribe-url?language=${language}`, { url })
  return data // { job_id }
}

export async function pollStatus(jobId) {
  const { data } = await http.get(`/transcription-status/${jobId}`)
  return data
}

export async function checkHealth() {
  const url = import.meta.env.VITE_API_BASE_URL
    ? `${import.meta.env.VITE_API_BASE_URL}/health`
    : '/health'
  const { data } = await axios.get(url)
  return data
}
