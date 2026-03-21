"""
Live microphone transcription session.

Protocol:
  1. Browser MediaRecorder sends WebM/Opus binary frames every ~250 ms.
  2. Server accumulates all chunks.
  3. On stop(): saves to .webm, FFmpeg converts to 16kHz WAV, Whisper transcribes.
  4. One "final" JSON result is pushed to an asyncio.Queue for the WebSocket handler.
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import threading
from typing import AsyncGenerator, Optional

from app.infrastructure.whisper import resolve_language, transcribe_sync
from app.infrastructure.audio import FFMPEG_CMD

logger = logging.getLogger(__name__)


class LiveTranscriptionSession:
    def __init__(self, language_code: str = "auto") -> None:
        self._chunks: list[bytes] = []
        self._queue: asyncio.Queue = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._language_code = language_code
        self._stopped = False
        self._thread: Optional[threading.Thread] = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        logger.info("LiveTranscriptionSession started (language=%s).", self._language_code)

    def feed_audio(self, chunk: bytes) -> None:
        if not self._stopped:
            self._chunks.append(chunk)

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        self._thread = threading.Thread(
            target=self._transcribe_thread, daemon=True, name="whisper-live"
        )
        self._thread.start()

    async def results(self) -> AsyncGenerator[dict, None]:
        while True:
            msg = await self._queue.get()
            if msg is None:
                break
            yield msg

    def _transcribe_thread(self) -> None:
        tmp_webm: Optional[str] = None
        tmp_wav: Optional[str] = None
        try:
            if not self._chunks:
                return

            fd, tmp_webm = tempfile.mkstemp(suffix=".webm")
            with os.fdopen(fd, "wb") as f:
                for chunk in self._chunks:
                    f.write(chunk)

            tmp_wav = tmp_webm.replace(".webm", ".wav")
            result = subprocess.run(
                [
                    FFMPEG_CMD, "-y",
                    "-i", tmp_webm,
                    "-ar", "16000",
                    "-ac", "1",
                    "-acodec", "pcm_s16le",
                    tmp_wav,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=60,
            )
            if result.returncode != 0:
                err = result.stderr.decode(errors="replace")
                raise RuntimeError(f"FFmpeg failed (exit {result.returncode}):\n{err}")

            language = resolve_language(self._language_code)
            segments = transcribe_sync(tmp_wav, language)

            if segments:
                msg = {
                    "type": "final",
                    "transcript": " ".join(s["transcript"] for s in segments),
                    "segments": segments,
                    "language_code": segments[0]["language_code"],
                }
            else:
                msg = {
                    "type": "final",
                    "transcript": "",
                    "segments": [],
                    "language_code": language or "unknown",
                }

            self._put(msg)

        except Exception as e:
            logger.error("LiveSession error: %s", e, exc_info=True)
            self._put({"type": "error", "message": str(e)})
        finally:
            for path in (tmp_webm, tmp_wav):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            self._put(None)  # sentinel — end of stream

    def _put(self, msg: Optional[dict]) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._queue.put(msg), self._loop)
