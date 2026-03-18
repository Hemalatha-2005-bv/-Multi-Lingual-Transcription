# Architecture

## Overview

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (Vue 3 + Vite)                                │
│  ┌──────────┐  ┌──────────┐  ┌────────────────────┐    │
│  │ Views    │  │ Stores   │  │ Services           │    │
│  │ HomeView │  │ transcr. │  │ api.js (Axios)     │    │
│  │ LiveView │  │ live     │  │ websocket.js (WS)  │    │
│  └──────────┘  └──────────┘  └────────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP / WebSocket
┌──────────────────────▼──────────────────────────────────┐
│  Backend (FastAPI + UV)                                 │
│                                                         │
│  API Layer                                              │
│  ┌────────────────┐  ┌──────────────────────────┐      │
│  │ /api routes    │  │ /ws/transcribe-live      │      │
│  │ transcription  │  │ (WebSocket)              │      │
│  │ health         │  └──────────────────────────┘      │
│  └───────┬────────┘                                    │
│          │ Depends()                                   │
│  Service Layer                                          │
│  ┌────────────────────────────────────────┐            │
│  │ TranscriptionService (ITranscription.) │            │
│  │ LiveTranscriptionSession               │            │
│  └───────┬────────────────────────────────┘            │
│          │                                             │
│  ┌───────┴──────────┐  ┌──────────────────────┐       │
│  │ Infrastructure   │  │ Repository Layer     │       │
│  │ audio.py (FFmpeg)│  │ IJobRepository       │       │
│  │ whisper.py       │  │ JobRepository (SQL.) │       │
│  │ ytdlp.py         │  └──────────────────────┘       │
│  └──────────────────┘          │                      │
│                                │                      │
│  ┌─────────────────────────────▼──────────────────┐   │
│  │  SQLite (aiosqlite + SQLAlchemy async)          │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## N-Tier Layers

| Layer | Location | Responsibility |
|-------|----------|---------------|
| **API** | `app/api/` | HTTP routing, request validation, response shaping |
| **Service** | `app/services/` | Business logic, pipeline orchestration |
| **Infrastructure** | `app/infrastructure/` | External tools: FFmpeg, Whisper, yt-dlp |
| **Repository** | `app/repositories/` | Database CRUD — isolated behind interface |
| **Models** | `app/models/` | SQLAlchemy ORM table definitions |
| **Schemas** | `app/schemas/` | Pydantic request/response contracts |
| **Core** | `app/core/` | Config, DB engine, custom exceptions |
| **Utils** | `app/utils/` | Pure formatting helpers (no I/O) |

## SOLID Principles Applied

- **Single Responsibility**: each class/module has one reason to change
- **Open/Closed**: `IJobRepository` and `ITranscriptionService` allow swapping implementations without touching callers
- **Liskov Substitution**: `JobRepository` satisfies `IJobRepository` fully
- **Interface Segregation**: repositories and services have focused, minimal interfaces
- **Dependency Inversion**: API routes depend on abstractions via FastAPI `Depends()`

## Job Lifecycle

```
POST /api/upload-video
  │
  ├─ Save file to temp dir
  ├─ Create Job record (status=pending)
  ├─ Return {job_id} immediately
  └─ BackgroundTask: TranscriptionService.start_file_job()
       ├─ status=extracting → FFmpeg → WAV
       ├─ status=transcribing → Whisper → segments[]
       └─ status=completed | error

GET /api/transcription-status/{job_id}
  └─ Read Job from SQLite → return current state
```

## WebSocket Live Mic Flow

```
Browser MediaRecorder
  └─ binary WebM/Opus chunks every 250ms → WS send
       │
Server WebSocket handler
  └─ LiveTranscriptionSession.feed_audio()
       │
On disconnect:
  └─ session.stop()
       ├─ Write .webm to temp file
       ├─ FFmpeg converts to 16kHz WAV (blocking thread)
       └─ Whisper transcribes → push JSON to asyncio.Queue
           └─ WebSocket sends JSON result to client
```
