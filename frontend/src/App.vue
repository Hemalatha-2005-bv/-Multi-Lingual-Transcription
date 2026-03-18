<template>
  <div class="app-wrapper">
    <header class="app-header">
      <div class="header-content">
        <span class="header-icon">🎙</span>
        <div>
          <h1>Multi-Lingual Transcription</h1>
          <p class="header-sub">Powered by OpenAI Whisper &mdash; fully offline</p>
        </div>
      </div>
      <nav class="app-nav">
        <RouterLink to="/" class="nav-link">Upload / YouTube</RouterLink>
        <RouterLink to="/live" class="nav-link">Live Mic</RouterLink>
      </nav>
    </header>

    <main class="app-main">
      <RouterView />
    </main>

    <footer class="app-footer">
      <span>Powered by OpenAI Whisper (local, offline) &bull; Tamil &amp; English</span>
    </footer>
  </div>
</template>

<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>
