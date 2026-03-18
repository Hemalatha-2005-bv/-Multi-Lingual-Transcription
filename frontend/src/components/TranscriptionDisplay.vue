<template>
  <div class="card result-card">
    <!-- Processing -->
    <div v-if="status === 'processing'" class="status-processing">
      <span class="spinner"></span>
      <div>
        <p class="status-title">{{ step || 'Processing…' }}</p>
        <p v-if="title" class="status-sub">{{ title }}</p>
        <div v-if="uploadProgress > 0 && uploadProgress < 100" class="progress-bar-wrap">
          <div class="progress-bar" :style="{ width: uploadProgress + '%' }"></div>
          <span class="progress-label">{{ uploadProgress }}%</span>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div v-else-if="status === 'error'" class="status-error">
      <span class="status-icon">❌</span>
      <div>
        <p class="status-title">Transcription failed</p>
        <p class="error-detail">{{ error }}</p>
      </div>
    </div>

    <!-- Completed -->
    <div v-else-if="status === 'completed'">
      <div class="result-header">
        <span class="status-icon">✅</span>
        <div>
          <p class="status-title">Transcription complete</p>
          <p v-if="title" class="status-sub">{{ title }}</p>
        </div>
      </div>

      <!-- Segments (read-only timestamps) -->
      <div class="segments">
        <div v-for="(seg, i) in results" :key="i" class="segment">
          <span v-if="seg.words?.length" class="segment-time">
            {{ formatTime(seg.words[0].start_time) }} &rarr; {{ formatTime(seg.words[seg.words.length - 1].end_time) }}
          </span>
          <p class="segment-text">{{ seg.cleaned_text || seg.transcript }}</p>
        </div>
      </div>

      <!-- Editable full transcript -->
      <div class="edit-section">
        <div class="edit-header">
          <label class="edit-label">Edit Transcript (தமிழ் திருத்தம்)</label>
          <div class="edit-actions">
            <button class="btn-copy" @click="copyText">{{ copied ? 'Copied!' : 'Copy' }}</button>
            <button class="btn-reset" @click="resetEdit">Reset</button>
          </div>
        </div>
        <textarea
          v-model="editableText"
          class="edit-textarea"
          dir="auto"
          spellcheck="false"
          placeholder="Transcription will appear here. You can edit it directly."
        />
        <p class="edit-hint">
          Tip: For Tamil typing use
          <a href="https://www.google.com/inputtools/try/" target="_blank" rel="noopener">Google Input Tools</a>
          or enable Tamil keyboard in Windows Settings.
        </p>
      </div>

      <DownloadButtons :txt="editableText" :srt="srt" :title="title" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import DownloadButtons from './DownloadButtons.vue'

const props = defineProps({
  status: String,
  step: String,
  title: String,
  results: Array,
  txt: String,
  srt: String,
  error: String,
  uploadProgress: Number,
})

// Build editable text from cleaned segments
const fullText = computed(() =>
  (props.results || [])
    .map(s => s.cleaned_text || s.transcript)
    .filter(Boolean)
    .join('\n')
)

const editableText = ref('')
const copied = ref(false)

// Populate editable box when results arrive
watch(fullText, (val) => { editableText.value = val }, { immediate: true })

function resetEdit() {
  editableText.value = fullText.value
}

async function copyText() {
  try {
    await navigator.clipboard.writeText(editableText.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // fallback
    const el = document.createElement('textarea')
    el.value = editableText.value
    document.body.appendChild(el)
    el.select()
    document.execCommand('copy')
    document.body.removeChild(el)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

function formatTime(sec) {
  const h = Math.floor(sec / 3600).toString().padStart(2, '0')
  const m = Math.floor((sec % 3600) / 60).toString().padStart(2, '0')
  const s = Math.floor(sec % 60).toString().padStart(2, '0')
  return `${h}:${m}:${s}`
}
</script>

<style scoped>
.edit-section {
  margin: 1.2rem 0 0.8rem;
}
.edit-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.4rem;
}
.edit-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--color-text-muted, #aaa);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.edit-actions {
  display: flex;
  gap: 0.5rem;
}
.btn-copy, .btn-reset {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 0.8rem;
  font-weight: 600;
}
.btn-copy {
  background: #4f8ef7;
  color: #fff;
}
.btn-reset {
  background: #444;
  color: #ddd;
}
.edit-textarea {
  width: 100%;
  min-height: 180px;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  border: 1px solid #444;
  background: #1a1a2e;
  color: #e8e8e8;
  font-size: 1rem;
  line-height: 1.8;
  font-family: 'Latha', 'Noto Sans Tamil', 'Arial Unicode MS', sans-serif;
  resize: vertical;
  box-sizing: border-box;
}
.edit-textarea:focus {
  outline: none;
  border-color: #4f8ef7;
}
.edit-hint {
  font-size: 0.75rem;
  color: #888;
  margin-top: 0.4rem;
}
.edit-hint a {
  color: #4f8ef7;
}
</style>
