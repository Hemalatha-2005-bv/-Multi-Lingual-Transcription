<template>
  <div class="download-bar">
    <button class="btn btn-secondary" @click="downloadTxt">Download TXT</button>
    <button class="btn btn-secondary" @click="downloadSrt">Download SRT</button>
    <button class="btn btn-outline" @click="copyToClipboard">
      {{ copied ? 'Copied!' : 'Copy Text' }}
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  txt: String,
  srt: String,
  title: { type: String, default: 'transcript' },
})

const copied = ref(false)

function slug() {
  return (props.title || 'transcript').replace(/[^a-z0-9]/gi, '_').toLowerCase().slice(0, 40)
}

function download(content, ext, mime) {
  const blob = new Blob([content], { type: mime })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${slug()}.${ext}`
  a.click()
  URL.revokeObjectURL(a.href)
}

function downloadTxt() { download(props.txt, 'txt', 'text/plain') }
function downloadSrt() { download(props.srt, 'srt', 'text/plain') }

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(props.txt)
    copied.value = true
    setTimeout(() => (copied.value = false), 2000)
  } catch {
    /* fallback: do nothing */
  }
}
</script>
