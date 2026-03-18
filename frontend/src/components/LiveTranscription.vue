<template>
  <div class="card live-card">
    <h2 class="card-title">Live Microphone Transcription</h2>

    <div class="form-row">
      <label class="form-label">Language</label>
      <select v-model="language" :disabled="isRecording || isProcessing" class="form-select">
        <option value="auto">Auto-detect</option>
        <option value="en-US">English</option>
        <option value="ta-IN">Tamil</option>
      </select>
    </div>

    <div class="live-controls">
      <button
        v-if="!isRecording"
        class="btn btn-danger"
        :disabled="isProcessing"
        @click="start"
      >
        🎙 Start Recording
      </button>
      <button v-else class="btn btn-secondary" @click="stop">
        ⏹ Stop &amp; Transcribe
      </button>
    </div>

    <div v-if="isRecording" class="recording-indicator">
      <span class="pulse-dot"></span> Recording…
    </div>

    <div v-if="isProcessing" class="status-processing">
      <span class="spinner"></span>
      <p>Transcribing with Whisper…</p>
    </div>

    <div v-if="error" class="status-error">
      <span class="status-icon">❌</span>
      <p>{{ error }}</p>
    </div>

    <div v-if="transcript && !isProcessing" class="live-result">
      <p class="live-lang">Language: {{ languageCode }}</p>
      <div class="segments">
        <div v-for="(seg, i) in segments" :key="i" class="segment">
          <span v-if="seg.words?.length" class="segment-time">
            {{ formatTime(seg.words[0].start_time) }} &rarr;
            {{ formatTime(seg.words[seg.words.length - 1].end_time) }}
          </span>
          <p class="segment-text">{{ seg.transcript }}</p>
        </div>
      </div>
      <DownloadButtons :txt="transcript" :srt="''" title="live_recording" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useLiveStore } from '../stores/live.js'
import DownloadButtons from './DownloadButtons.vue'
import { storeToRefs } from 'pinia'

const store = useLiveStore()
const { isRecording, isProcessing, transcript, segments, languageCode, error } = storeToRefs(store)
const language = ref('auto')

function start() { store.startRecording(language.value) }
function stop() { store.stopRecording() }

function formatTime(sec) {
  const h = Math.floor(sec / 3600).toString().padStart(2, '0')
  const m = Math.floor((sec % 3600) / 60).toString().padStart(2, '0')
  const s = Math.floor(sec % 60).toString().padStart(2, '0')
  return `${h}:${m}:${s}`
}
</script>
