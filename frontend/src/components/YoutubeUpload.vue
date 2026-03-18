<template>
  <div class="upload-card card">
    <h2 class="card-title">YouTube URL</h2>

    <div class="form-row">
      <label class="form-label">YouTube URL</label>
      <input
        v-model="url"
        type="url"
        class="form-input"
        placeholder="https://www.youtube.com/watch?v=…"
        @keyup.enter="submit"
      />
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
      :disabled="!url.trim() || disabled"
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

const url = ref('')
const language = ref('auto')

function submit() {
  if (url.value.trim()) emit('submit', { url: url.value.trim(), language: language.value })
}
</script>
