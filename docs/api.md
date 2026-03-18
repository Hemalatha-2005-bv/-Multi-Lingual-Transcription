# API Reference

Base URL: `http://localhost:8000`

Interactive docs: `http://localhost:8000/docs`

---

## Health

### `GET /health`

```json
{
  "status": "ok",
  "version": "2.0.0",
  "whisper_model": "base",
  "mode": "local (offline)"
}
```

---

## Batch Transcription

### `POST /api/upload-video`

Upload a video or audio file for transcription.

**Query params**
- `language` — `auto` (default) | `en-US` | `ta-IN`

**Body**: `multipart/form-data` with `file` field

**Response** `200`
```json
{ "job_id": "uuid-string" }
```

---

### `POST /api/transcribe-url`

Transcribe a YouTube video.

**Query params**
- `language` — `auto` (default) | `en-US` | `ta-IN`

**Body** (JSON)
```json
{ "url": "https://www.youtube.com/watch?v=..." }
```

**Response** `200`
```json
{ "job_id": "uuid-string" }
```

**Errors**
- `400` — not a valid YouTube URL
- `500` — server error

---

### `GET /api/transcription-status/{job_id}`

Poll the state of a transcription job. Call every 2 seconds.

**Response — processing**
```json
{
  "status": "processing",
  "step": "Transcribing with Whisper…",
  "progress": null,
  "title": "my_video.mp4"
}
```

**Response — error**
```json
{
  "status": "error",
  "error": "FFmpeg not found on PATH.",
  "title": "my_video.mp4"
}
```

**Response — completed**
```json
{
  "status": "completed",
  "title": "my_video.mp4",
  "results": [
    {
      "transcript": "Hello, how are you?",
      "confidence": -0.23,
      "language_code": "en",
      "words": [
        { "word": "Hello", "start_time": 0.5, "end_time": 1.0 }
      ]
    }
  ],
  "txt": "[00:00:00 --> 00:00:05]\nHello, how are you?\n",
  "srt": "1\n00:00:00,500 --> 00:00:05,000\nHello, how are you?\n"
}
```

---

## WebSocket — Live Transcription

### `WS /ws/transcribe-live?language=auto`

**Client → Server**: binary WebM/Opus audio frames (from `MediaRecorder`)

**Server → Client**: JSON result (sent once after client disconnects)

```json
{
  "type": "final",
  "transcript": "Full transcript text",
  "segments": [...],
  "language_code": "en"
}
```

On error:
```json
{ "type": "error", "message": "FFmpeg exited 1 during live conversion." }
```

---

## Language Codes

| Code | Language |
|------|----------|
| `auto` | Whisper auto-detects |
| `en-US` | English |
| `ta-IN` | Tamil |
