# Setup Guide

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Python | 3.11+ | python.org |
| Node.js | 18+ | nodejs.org |
| FFmpeg | any | ffmpeg.org |
| UV | latest | `pip install uv` or `winget install astral-sh.uv` |

Verify FFmpeg: `ffmpeg -version`

---

## Backend Setup (UV)

```bash
cd backend

# Install dependencies with UV
uv sync

# Copy and edit configuration
cp .env.example .env
# Edit .env — set WHISPER_MODEL, FFMPEG_PATH if needed

# Start the API server
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts at http://localhost:8000
API docs at http://localhost:8000/docs

### Whisper model sizes

| Model  | Size   | Speed  | Accuracy |
|--------|--------|--------|----------|
| tiny   | 39 MB  | Fastest | Basic |
| base   | 74 MB  | Fast   | Good (default) |
| small  | 244 MB | Medium | Better Tamil |
| medium | 769 MB | Slow   | Best CPU option |
| large  | 1.5 GB | Slowest | Best overall |

Model downloads automatically to `~/.cache/huggingface/` on first run.

---

## Frontend Setup (Vue 3)

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

Frontend runs at http://localhost:5173

---

## Running Tests

```bash
cd backend
uv run pytest ../tests/backend -v
```

---

## Production Build

```bash
# Build frontend
cd frontend && npm run build

# Run backend (production)
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
```
