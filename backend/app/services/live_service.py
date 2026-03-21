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
        tmp_wav: Optional[str] = None
        try:
            if not self._chunks:
                return

            audio_data = b"".join(self._chunks)

            # Pipe audio directly to FFmpeg with explicit format — avoids
            # "EBML header parsing failed" that occurs when the browser's
            # MediaRecorder chunks don't form a perfectly valid WebM file
            # when written to disk and auto-detected.
            fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            result = subprocess.run(
                [
                    FFMPEG_CMD, "-y",
                    "-fflags", "+igndts+genpts",
                    "-f", "webm",       # force input format — skip auto-detection
                    "-i", "pipe:0",     # read from stdin
                    "-vn",
                    "-ar", "16000",
                    "-ac", "1",
                    "-acodec", "pcm_s16le",
                    tmp_wav,
                ],
                input=audio_data,
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
            if tmp_wav and os.path.exists(tmp_wav):
                try:
                    os.remove(tmp_wav)
                except OSError:
                    pass
            self._put(None)  # sentinel — end of stream

    def _put(self, msg: Optional[dict]) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._queue.put(msg), self._loop)
