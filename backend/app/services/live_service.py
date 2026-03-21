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
        tmp_audio: Optional[str] = None  # input: .webm or .ogg
        tmp_wav: Optional[str] = None    # output: 16kHz PCM WAV
        try:
            if not self._chunks:
                return

            audio_data = b"".join(self._chunks)

            magic = audio_data[:8].hex()
            logger.info("Audio data: %d bytes, magic=%s", len(audio_data), magic)

            # Write to a seekable temp file — stdin pipe breaks WebM/EBML
            # parsing because the demuxer needs random-access for header seeks.
            # Use .webm suffix so FFmpeg tries matroska demuxer first.
            fd, tmp_audio = tempfile.mkstemp(suffix=".webm")
            try:
                os.write(fd, audio_data)
            finally:
                os.close(fd)

            fd, tmp_wav = tempfile.mkstemp(suffix=".wav")
            os.close(fd)

            # Try multiple input formats — browser may send WebM, OGG, or MP4
            # depending on browser/OS. Auto-detect first, then force each format.
            formats_to_try: list[Optional[str]] = [None, "webm", "ogg", "matroska", "mp4"]
            result = None
            for fmt in formats_to_try:
                cmd = [FFMPEG_CMD, "-y", "-fflags", "+igndts+genpts"]
                if fmt:
                    cmd += ["-f", fmt]
                cmd += ["-i", tmp_audio, "-vn", "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", tmp_wav]
                result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
                if result.returncode == 0:
                    logger.info("FFmpeg succeeded with format=%s", fmt or "auto")
                    break
                logger.warning("FFmpeg format=%s failed: %s", fmt or "auto",
                               result.stderr.decode(errors="replace")[-200:])

            if result is None or result.returncode != 0:
                err = result.stderr.decode(errors="replace") if result else "no result"
                raise RuntimeError(
                    f"FFmpeg failed all formats (magic={magic}, size={len(audio_data)}):\n{err}"
                )

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
            for path in (tmp_audio, tmp_wav):
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            self._put(None)  # sentinel — end of stream

    def _put(self, msg: Optional[dict]) -> None:
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._queue.put(msg), self._loop)
