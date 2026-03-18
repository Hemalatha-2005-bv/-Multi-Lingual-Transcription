import os
import logging
import asyncio
import sys
from contextlib import asynccontextmanager

# Solve NotImplementedError for subprocesses on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import get_settings
from routers import transcription, websocket

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Temp directory ────────────────────────────────────────────────────────
    tmp_dir = settings.get_temp_dir()
    os.makedirs(tmp_dir, exist_ok=True)
    logger.info("Temp directory: %s", tmp_dir)

    # ── Load Whisper model once at startup ────────────────────────────────────
    # This prevents a long delay on the first transcription request.
    from services.speech_service import load_model
    load_model(settings.WHISPER_MODEL)

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Multi-Lingual Transcription API",
    description="Local video/audio to text transcription using OpenAI Whisper. "
                "Supports Tamil and English. Fully offline — no cloud services required.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcription.router, prefix="/api", tags=["Transcription"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/health", tags=["Health"])
async def health_check():
    from services.speech_service import get_model
    try:
        model = get_model()
        model_name = getattr(model, "name", settings.WHISPER_MODEL)
    except Exception:
        model_name = "not loaded"
    return {
        "status": "ok",
        "version": "2.0.0",
        "whisper_model": model_name,
        "mode": "local (offline)",
    }
