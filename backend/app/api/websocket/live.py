"""
WebSocket endpoint for live microphone transcription.

Protocol:
  Client → Server : binary WebM/Opus audio chunks (from MediaRecorder)
  Server → Client : JSON {"type": "final"|"error", "transcript": str, "segments": [...]}

Origin is validated manually because FastAPI CORSMiddleware does not cover WebSocket upgrades.
"""

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.services.live_service import LiveTranscriptionSession

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


def _origin_allowed(origin: str | None) -> bool:
    import re
    if origin is None:
        return True
    cleaned = origin.rstrip("/")
    if any(cleaned == a.rstrip("/") for a in settings.CORS_ORIGINS):
        return True
    # Also allow all Vercel deployment URLs (previews have unique subdomains)
    if re.match(r"https://[^.]+\.vercel\.app$", cleaned):
        return True
    return False


@router.websocket("/ws/transcribe-live")
async def websocket_transcribe_live(
    websocket: WebSocket,
    language: str = "auto",
):
    """
    Live mic transcription over WebSocket.
    Query: ?language=ta-IN | en-US | auto
    """
    origin = websocket.headers.get("origin")
    if not _origin_allowed(origin):
        await websocket.close(code=4403, reason="Origin not allowed")
        logger.warning("Rejected WebSocket from: %s", origin)
        return

    await websocket.accept()
    logger.info("WebSocket accepted origin=%s language=%s", origin, language)

    loop = asyncio.get_running_loop()
    session = LiveTranscriptionSession(language_code=language)
    session.start(loop)

    try:
        # Receive audio chunks until client sends empty frame (stop signal)
        try:
            while True:
                data = await websocket.receive_bytes()
                if len(data) == 0:
                    logger.info("Stop signal received — running Whisper.")
                    break
                session.feed_audio(data)
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected early.")
        except Exception as e:
            logger.error("WebSocket receive error: %s", e)

        session.stop()

        # WebSocket is still open — send result back to client
        async for msg in session.results():
            try:
                await websocket.send_json(msg)
            except Exception as e:
                logger.warning("Failed to send result: %s", e)
                break

    except Exception as e:
        logger.error("Unexpected WebSocket error: %s", e, exc_info=True)
    finally:
        session.stop()
        logger.info("WebSocket session cleaned up.")
