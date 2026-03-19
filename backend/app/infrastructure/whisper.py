"""
Transcription layer using faster-whisper (CTranslate2, int8 quantization).

faster-whisper is ~4x faster than openai-whisper on CPU at the same accuracy.
Tamil audio gets language="ta" forced + initial prompt for better script output.

Install: pip install faster-whisper
"""

import asyncio
import logging
import re
import threading
import unicodedata
from typing import Optional

from app.core.exceptions import WhisperError

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()

_LANGUAGE_MAP: dict = {
    "ta-IN": "ta",
    "en-US": "en",
    "auto":  None,
}


# ── Model management ──────────────────────────────────────────────────────────

def load_model(model_name: str = "medium") -> None:
    """Load faster-whisper model once at startup."""
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel
            # "auto" lets CTranslate2 pick the best compute type the CPU supports.
            # "int8" can raise NotImplementedError on CPUs without AVX-VNNI/BLAS support.
            logger.info("Loading faster-whisper '%s' (int8)...", model_name)
            _model = WhisperModel(model_name, device="cpu", compute_type="int8")
            logger.info("faster-whisper '%s' loaded.", model_name)


def get_model():
    if _model is None:
        raise WhisperError("Whisper model is still loading, please wait a moment and try again.")
    return _model


def resolve_language(language_code: str) -> Optional[str]:
    return _LANGUAGE_MAP.get(language_code)


# ── Tamil text cleaning ───────────────────────────────────────────────────────

_TAMIL_CORRECTIONS: dict[str, str] = {
    "ஜைத்திரும்":   "ஜெயித்தாலும்",
    "தோப்பராதலாம்": "தொடர்வதாலும்",
    "முக்கியால்":    "முக்கியமாக",
    "வேனும்":        "வேண்டும்",
    "பண்றோம்":      "செய்கிறோம்",
    "பண்றான்":      "செய்கிறான்",
    "பண்றா":        "செய்கிறாள்",
    "ஆனா":          "ஆனால்",
    "இல்லன்னா":     "இல்லையென்றால்",
    "சரியா":        "சரியாக",
    "நல்லா":        "நன்றாக",
    "இப்போ":        "இப்போது",
    "அப்போ":        "அப்போது",
    "எப்போ":        "எப்போது",
    "ரொம்ப":        "மிகவும்",
    "தெரியல":       "தெரியவில்லை",
    "வேண்டா":       "வேண்டாம்",
    "போகணும்":      "போகவேண்டும்",
    "பார்க்கணும்":  "பார்க்கவேண்டும்",
    "பண்ணணும்":     "செய்யவேண்டும்",
}


def _apply_corrections(text: str) -> str:
    for wrong, correct in _TAMIL_CORRECTIONS.items():
        text = text.replace(wrong, correct)
    return text


def _remove_repeated_words(text: str) -> str:
    words = text.split()
    if not words:
        return text
    deduped = [words[0]]
    for word in words[1:]:
        if word.strip(".,!?;:") != deduped[-1].strip(".,!?;:"):
            deduped.append(word)
    return " ".join(deduped)


def _remove_repeated_phrases(text: str) -> str:
    for n in range(5, 1, -1):
        pattern = r"\b((?:\S+\s+){" + str(n - 1) + r"}\S+)(\s+\1)+"
        text = re.sub(pattern, r"\1", text, flags=re.UNICODE)
    return text


def _fix_sentence_structure(text: str) -> str:
    text = text.replace("।", ".")
    sentences = re.split(r"(?<=[.!?])\s+", text)
    result = []
    for s in sentences:
        s = s.strip()
        if s and s[-1] not in ".!?":
            s += "."
        if s:
            result.append(s)
    return " ".join(result)


def clean_tamil_text(text: str) -> str:
    if not text:
        return text
    text = unicodedata.normalize("NFC", text)
    text = _apply_corrections(text)
    text = _remove_repeated_words(text)
    text = _remove_repeated_phrases(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[^\u0B80-\u0BFF\u0020-\u007E\u00A0\n.,!?;:()\"\'-]", "", text)
    text = re.sub(r"\s([.,!?;:])", r"\1", text)
    text = _fix_sentence_structure(text)
    return text.strip()


# ── Audio loading ─────────────────────────────────────────────────────────────

def _load_wav(wav_path: str):
    import wave
    import numpy as np
    with wave.open(wav_path, "rb") as w:
        frames = w.readframes(w.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


# ── Transcription ─────────────────────────────────────────────────────────────

def transcribe_sync(wav_path: str, language: Optional[str]) -> list:
    """
    faster-whisper transcription.
    Tamil:  language='ta' + initial_prompt for Tamil script
    Others: auto-detect or forced language
    """
    model = get_model()
    is_tamil = (language == "ta")

    tamil_prompt = (
        "இந்த ஆடியோ தெளிவான, சரியான எழுத்துருவிலான தமிழ் வாக்கியங்களைக் கொண்டுள்ளது."
        if is_tamil else None
    )

    logger.info("faster-whisper transcribing: %s (lang=%s)", wav_path, language or "auto")

    try:
        segments_iter, info = model.transcribe(
            wav_path,
            language=language,
            beam_size=1,                    # greedy — fastest on CPU
            best_of=1,
            temperature=0.0,
            condition_on_previous_text=True,
            no_speech_threshold=0.6,
            initial_prompt=tamil_prompt,
            word_timestamps=True,
            vad_filter=False,               # disabled: silero VAD raises NotImplementedError
                                            # on CPUs without onnxruntime AVX support
        )
    except NotImplementedError as e:
        raise WhisperError(
            f"faster-whisper failed ({e or 'NotImplementedError'}). "
            "Try setting WHISPER_MODEL=base or check that ctranslate2 supports your CPU."
        ) from e
    except Exception as e:
        raise WhisperError(f"faster-whisper transcription error: {e}") from e

    detected_lang = info.language
    results = []

    for seg in segments_iter:
        raw = (seg.text or "").strip()
        if not raw:
            continue

        words = []
        if seg.words:
            for w in seg.words:
                words.append({
                    "word":       (w.word or "").strip(),
                    "start_time": round(w.start, 3),
                    "end_time":   round(w.end, 3),
                })

        cleaned = clean_tamil_text(raw) if detected_lang == "ta" else raw

        results.append({
            "transcript":    raw,
            "cleaned_text":  cleaned,
            "confidence":    round(seg.avg_logprob, 4),
            "language_code": detected_lang,
            "words":         words,
        })

    logger.info("faster-whisper done: %d segments, lang=%s", len(results), detected_lang)
    return results


async def transcribe(audio_path: str, language_code: str = "auto") -> list:
    """Async wrapper — runs in a thread-pool executor."""
    language = resolve_language(language_code)
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, transcribe_sync, audio_path, language)
