"""
FFmpeg wrapper — extracts/converts audio to 16kHz mono LINEAR16 WAV.
Runs FFmpeg in a thread-pool executor so it never blocks the asyncio event loop,
and works on Windows without requiring ProactorEventLoop.
"""

import asyncio
import logging
import os
import shutil
import subprocess

from app.core.config import get_settings
from app.core.exceptions import FFmpegError

logger = logging.getLogger(__name__)
settings = get_settings()


def _resolve_bin(configured: str, fallback: str = "ffmpeg") -> str:
    """Return configured path if it exists on disk, else find fallback on PATH."""
    if os.path.isfile(configured):
        return configured
    found = shutil.which(configured) or shutil.which(fallback)
    return found or configured


FFMPEG_CMD = _resolve_bin(settings.FFMPEG_PATH, "ffmpeg")


async def extract_audio(video_path: str, output_path: str) -> str:
    """
    Convert any video/audio file to a WAV suitable for Whisper:
      - Codec       : PCM signed 16-bit little-endian (LINEAR16)
      - Sample rate : 16 000 Hz
      - Channels    : mono

    Runs the blocking subprocess in a thread-pool executor.
    Returns output_path on success. Raises FFmpegError on failure.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        FFMPEG_CMD,
        "-y",
        "-i", video_path,
        "-vn",
        "-af", "silenceremove=start_periods=1:start_threshold=-50dB:detection=peak",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path,
    ]

    logger.info("FFmpeg: %s", " ".join(cmd))

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _run_ffmpeg, cmd)
    except FFmpegError:
        raise
    except Exception as e:
        raise FFmpegError(str(e))

    logger.info("FFmpeg done: %s", output_path)
    return output_path


def _run_ffmpeg(cmd: list) -> None:
    """Blocking FFmpeg call — run inside a thread executor."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
    except FileNotFoundError:
        msg = f"FFmpeg not found at '{cmd[0]}'."
        if os.name == "nt":
            msg += " Set the full path in FFMPEG_PATH in backend/.env"
        raise FFmpegError(msg)
    except subprocess.TimeoutExpired:
        raise FFmpegError("FFmpeg timed out after 10 minutes.")

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise FFmpegError(f"FFmpeg exited {result.returncode}:\n{stderr}")
