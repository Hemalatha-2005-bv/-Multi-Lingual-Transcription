import asyncio
import logging
import sys
from contextlib import asynccontextmanager

# Windows requires ProactorEventLoop for asyncio.create_subprocess_exec
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_tables
from app.api.routes import health, transcription
from app.api.websocket import live

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables
    await create_tables()
    logger.info("Database ready.")

    # Load Whisper model in a background thread so startup is non-blocking.
    # Requests that arrive before the model is ready will get a 503.
    import threading
    from app.infrastructure.whisper import load_model
    threading.Thread(
        target=load_model, args=(settings.WHISPER_MODEL,), daemon=True
    ).start()

    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Multi-Lingual Transcription API",
    description=(
        "Local video/audio to text transcription using OpenAI Whisper. "
        "Supports Tamil and English. Fully offline — no cloud services required."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(transcription.router, prefix="/api")
app.include_router(live.router)
