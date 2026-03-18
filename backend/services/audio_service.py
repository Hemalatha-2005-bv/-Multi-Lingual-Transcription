"""
Audio processing service using FFmpeg via subprocess in a thread executor.
Works on Windows without requiring ProactorEventLoop.
"""

import asyncio
import logging
import os
import subprocess

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def extract_audio(video_path: str, output_path: str) -> str:
    """
    Extract and convert audio to 16kHz mono PCM WAV.
    Runs FFmpeg in a thread-pool executor — never blocks the event loop.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    cmd = [
        settings.FFMPEG_PATH,
        "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        output_path,
    ]

    logger.info("Running FFmpeg: %s", " ".join(cmd))

    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, _run_ffmpeg, cmd)
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
        raise RuntimeError(
            f"FFmpeg not found at '{cmd[0]}'. "
            "Set the full path in FFMPEG_PATH in backend/.env"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 10 minutes.")

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise RuntimeError(f"FFmpeg failed (exit {result.returncode}):\n{stderr}")
