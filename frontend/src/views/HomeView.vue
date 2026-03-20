<template>
  <div class="home-view">
    <div class="tab-bar">
      <button
        class="tab"
        :class="{ 'tab--active': activeTab === 'file' }"
        @click="activeTab = 'file'"
      >
        Upload File
      </button>
      <button
        class="tab"
        :class="{ 'tab--active': activeTab === 'youtube' }"
        @click="activeTab = 'youtube'"
      >
        YouTube URL
      </button>
    </div>

    <FileUpload
      v-if="activeTab === 'file'"
      :disabled="store.status === 'processing'"
      @submit="({ file, language }) => store.submitFile(file, language)"
    />
    <YoutubeUpload
      v-else
      :disabled="store.status === 'processing'"
      @submit="({ url, language }) => store.submitUrl(url, language)"
    />

    <TranscriptionDisplay
      v-if="store.status"
      :status="store.status"
      :step="store.step"
      :title="store.title"
      :results="store.results"
      :txt="store.txt"
      :srt="store.srt"
      :error="store.error"
      :upload-progress="store.uploadProgress"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useTranscriptionStore } from '../stores/transcription.js'
import FileUpload from '../components/FileUpload.vue'
import YoutubeUpload from '../components/YoutubeUpload.vue'
import TranscriptionDisplay from '../components/TranscriptionDisplay.vue'
import { checkHealth } from '../services/api.js'

const activeTab = ref('file')
const store = useTranscriptionStore()

// Wake up the Render free-tier backend on page load so it's ready when the user submits
onMounted(() => { checkHealth().catch(() => {}) })
</script>
