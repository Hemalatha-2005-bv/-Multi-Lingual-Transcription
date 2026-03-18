<template>
  <div class="upload-card card">
    <h2 class="card-title">Upload File</h2>

    <div
      class="drop-zone"
      :class="{ 'drop-zone--active': isDragging }"
      @dragover.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      @drop.prevent="onDrop"
      @click="fileInput.click()"
    >
      <input
        ref="fileInput"
        type="file"
        accept="video/*,audio/*,.mp4,.mkv,.avi,.mov,.webm,.mp3,.wav,.m4a,.flac"
        class="hidden"
        @change="onFileChange"
      />
      <div v-if="!selectedFile" class="drop-zone__hint">
        <span class="drop-icon">📂</span>
        <p>Click or drag &amp; drop a video / audio file</p>
        <p class="drop-sub">MP4, MKV, AVI, MOV, WebM, MP3, WAV, M4A, FLAC — up to 500 MB</p>
      </div>
      <div v-else class="drop-zone__file">
        <span class="drop-icon">🎬</span>
        <p class="file-name">{{ selectedFile.name }}</p>
        <p class="file-size">{{ formatSize(selectedFile.size) }}</p>
      </div>
    </div>

    <div class="form-row">
      <label class="form-label">Language</label>
      <select v-model="language" class="form-select">
        <option value="auto">Auto-detect</option>
        <option value="en-US">English</option>
        <option value="ta-IN">Tamil</option>
      </select>
    </div>

    <button
      class="btn btn-primary"
      :disabled="!selectedFile || disabled"
      @click="submit"
    >
      Transcribe
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({ disabled: Boolean })
const emit = defineEmits(['submit'])

const fileInput = ref(null)
const selectedFile = ref(null)
const language = ref('auto')
const isDragging = ref(false)

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null
}
function onDrop(e) {
  isDragging.value = false
  selectedFile.value = e.dataTransfer.files[0] || null
}
function formatSize(bytes) {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
function submit() {
  if (selectedFile.value) emit('submit', { file: selectedFile.value, language: language.value })
}
</script>
