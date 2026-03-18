"""
Local Whisper transcription service using openai-whisper.

Install: pip install openai-whisper
Model downloads automatically on first run to ~/.cache/whisper/
No cloud credentials required — fully offline.
"""

import asyncio
import logging
import os
import re
import subprocess
import tempfile
import threading
import unicodedata
from typing import AsyncGenerator, Optional

logger = logging.getLogger(__name__)


from app.infrastructure.whisper import clean_tamil_text  # single source of truth

_model = None
_model_lock = threading.Lock()

_LANGUAGE_MAP = {
    "ta-IN": "ta",
    "en-US": "en",
    "auto":  None,
}


def _resolve_language(language_code: str) -> Optional[str]:
    return _LANGUAGE_MAP.get(language_code)


def load_model(model_name: str = "medium"):
    """Load faster-whisper model once at startup."""
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel
            logger.info("Loading faster-whisper '%s' (auto)...", model_name)
            _model = WhisperModel(model_name, device="cpu", compute_type="auto")
            logger.info("faster-whisper '%s' loaded.", model_name)
    return _model


def get_model():
    if _model is None:
        raise RuntimeError("Whisper model not loaded. Call load_model() at startup.")
    return _model


def _run_whisper(audio_path: str, language: Optional[str]) -> list:
    """faster-whisper transcription in a thread-pool executor."""
    model = get_model()
    is_tamil = (language == "ta")
    tamil_prompt = (
        "இந்த ஆடியோ தெளிவான, சரியான எழுத்துருவிலான தமிழ் வாக்கியங்களைக் கொண்டுள்ளது."
        if is_tamil else None
    )
    logger.info("faster-whisper: %s (lang=%s)", audio_path, language or "auto")

    segments_iter, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=1,
        best_of=1,
        temperature=0.0,
        condition_on_previous_text=True,
        no_speech_threshold=0.6,
        initial_prompt=tamil_prompt,
        word_timestamps=True,
        vad_filter=False,   # silero VAD raises NotImplementedError on some CPUs
    )

    detected_lang = info.language
    segments_out = []

    for seg in segments_iter:
        raw_transcript = (seg.text or "").strip()
        if not raw_transcript:
            continue

        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "word":       (w.word or "").strip(),
                    "start_time": round(w.start, 3),
                    "end_time":   round(w.end, 3),
                })

        cleaned = clean_tamil_text(raw_transcript) if detected_lang == "ta" else raw_transcript
        segments_out.append({
            "transcript":    raw_transcript,
            "cleaned_text":  cleaned,
            "confidence":    round(seg.avg_logprob, 4),
            "language_code": detected_lang,
            "words":         words,
        })

    logger.info("Whisper done: %d segments, lang=%s", len(segments_out), detected_lang)
    return segments_out


async def transcribe_audio(audio_path: str, language_code: str = "auto") -> list:
    """Async wrapper — runs Whisper in a thread-pool executor."""
    language = _resolve_language(language_code)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run_whisper, audio_path, language)


# ── Live mic transcription session ───────────────────────────────────────────

class LiveTranscriptionSession:
    """Accumulate WebM/Opus audio chunks, transcribe with Whisper on stop()."""

    def __init__(self, language_code: str = "auto", ffmpeg_path: str = "ffmpeg"):
        self._audio_chunks = []
        self._result_queue = asyncio.Queue()
        self._loop = None
        self._language_code = language_code
        self._ffmpeg_path = ffmpeg_path
        self._stopped = False
        self._thread = None

    def start(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        logger.info("LiveTranscriptionSession started.")

    def feed_audio(self, chunk: bytes):
        if not self._stopped:
            self._audio_chunks.append(chunk)

    def stop(self):
        if self._stopped:
            return
        self._stopped = True
        self._thread = threading.Thread(
            target=self._transcribe_thread, daemon=True, name="whisper-live"
        )
        self._thread.start()

    async def results(self) -> AsyncGenerator:
        while True:
            msg = await self._result_queue.get()
            if msg is None:
                break
            yield msg

    def _transcribe_thread(self):
        tmp_webm = None
        tmp_wav = None
        try:
            if not self._audio_chunks:
                return

            fd, tmp_webm = tempfile.mkstemp(suffix=".webm")
            with os.fdopen(fd, "wb") as f:
                for chunk in self._audio_chunks:
                    f.write(chunk)

            tmp_wav = tmp_webm.replace(".webm", ".wav")
            result = subprocess.run(
                [
                    self._ffmpeg_path, "-y",
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

            language = _resolve_language(self._language_code)
            segments = _run_whisper(tmp_wav, language)

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
            self._put(None)

    def _put(self, msg):
        if self._loop:
            asyncio.run_coroutine_threadsafe(self._result_queue.put(msg), self._loop)
