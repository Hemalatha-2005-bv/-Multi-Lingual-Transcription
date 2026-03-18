"""
WebSocket endpoint for live microphone transcription using local Whisper.

Protocol:
  Client → Server : binary frames containing WebM/Opus audio chunks
                    from the browser's MediaRecorder API.
  Server → Client : JSON message (after user stops recording):
                    {
                      "type":         "final" | "error",
                      "transcript":   str,
                      "segments":     [{transcript, confidence, language_code, words}],
                      "language_code": str
                    }

How it works:
  1. Browser MediaRecorder sends audio chunks every 250 ms.
  2. Server accumulates all chunks in memory.
  3. When the client disconnects (stops recording), the session:
     a. Saves accumulated bytes to a temporary .webm file.
     b. Converts to 16 kHz mono WAV using FFmpeg.
     c. Runs Whisper on the WAV.
     d. Sends back the full transcript as one "final" message.

Origin validation:
  FastAPI CORSMiddleware does NOT apply to WebSocket upgrades.
  We validate the Origin header manually.
"""

import asyncio
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import get_settings
from services.speech_service import LiveTranscriptionSession

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


def _is_origin_allowed(origin: str | None) -> bool:
    """Return True if the WebSocket upgrade Origin is in our CORS allow-list."""
    if origin is None:
        return True  # Allow connections with no Origin (e.g. curl, native clients)
    return any(
        origin.rstrip("/") == allowed.rstrip("/")
        for allowed in settings.CORS_ORIGINS
    )


@router.websocket("/ws/transcribe-live")
async def websocket_transcribe_live(
    websocket: WebSocket,
    language: str = "auto",
):
    """
    Live microphone transcription via WebSocket.

    Query params:
      ?language=ta-IN | en-US | auto (default)

    The client sends raw audio bytes (WebM/Opus from MediaRecorder).
    After the client disconnects, Whisper transcribes and the server
    sends back one JSON "final" result message.
    """
    origin = websocket.headers.get("origin")
    if not _is_origin_allowed(origin):
        await websocket.close(code=4403, reason="Origin not allowed")
        logger.warning("Rejected WebSocket from unauthorized origin: %s", origin)
        return

    await websocket.accept()
    logger.info(
        "WebSocket connection accepted. origin=%s, language=%s", origin, language
    )

    loop = asyncio.get_running_loop()
    session = LiveTranscriptionSession(
        language_code=language,
        ffmpeg_path=settings.FFMPEG_PATH,
    )
    session.start(loop)

    try:
        # ── Receive audio chunks from MediaRecorder ───────────────────────────
        try:
            while True:
                data = await websocket.receive_bytes()
                session.feed_audio(data)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected — running Whisper transcription.")
        except Exception as e:
            logger.error("WebSocket receive error: %s", e)

        # ── Trigger transcription and wait for result ─────────────────────────
        session.stop()

        async for msg in session.results():
            try:
                await websocket.send_json(msg)
            except Exception as e:
                logger.warning("Failed to send result to client: %s", e)
                break

    except Exception as e:
        logger.error("Unexpected WebSocket error: %s", e, exc_info=True)
    finally:
        session.stop()
        logger.info("WebSocket session cleaned up.")
