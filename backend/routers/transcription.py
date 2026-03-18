"""
HTTP endpoints for batch transcription via local Whisper.

Flow:
  POST /api/upload-video   → saves file, starts background job (FFmpeg → Whisper)
                            → returns {job_id} immediately
  POST /api/transcribe-url → downloads YouTube audio (yt-dlp), then runs pipeline
                            → returns {job_id} immediately
  GET  /api/transcription-status/{job_id} → polls job state

Job lifecycle:
  "extracting"   — FFmpeg is converting the uploaded file to WAV
  "downloading"  — yt-dlp is fetching YouTube audio
  "transcribing" — Whisper is transcribing
  "completed"    — done; results available in state
  "error"        — failed; error message in state
"""

import asyncio
import logging
import shutil
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Body, File, HTTPException, Query, UploadFile

from config import get_settings
from services.audio_service import extract_audio
from services.speech_service import transcribe_audio
from services.youtube_service import download_youtube_audio, is_youtube_url
from utils.formatters import format_as_srt, format_as_txt

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()

# ── In-memory job state ───────────────────────────────────────────────────────
_job_state: dict[str, dict] = {}


# ── Helper: always produce a non-empty error string ──────────────────────────

def _err(e: Exception) -> str:
    msg = str(e).strip()
    if not msg:
        msg = f"{type(e).__name__}: {repr(e)}"
    
    # Check for specific known errors
    if "ffmpeg" in msg.lower() and ("not found" in msg.lower() or "WinError 2" in msg):
        return (
            "FFmpeg not found. "
            "Install FFmpeg and ensure it's on your PATH, "
            "or set FFMPEG_PATH in backend/.env."
        )
    
    # Generic error formatting
    return f"{type(e).__name__}: {msg}"


# ── Shared background pipeline ────────────────────────────────────────────────

async def _run_pipeline(
    job_id: str,
    source_path: str,   # path to already-saved input file
    audio_path: str,    # where FFmpeg writes the WAV
    language: str,
    tmp_dir: str,
) -> None:
    """FFmpeg → Whisper → update _job_state. Cleans up tmp_dir on exit."""
    try:
        logger.info("FFmpeg starting  job_id=%s", job_id)
        _job_state[job_id]["status"] = "extracting"
        await extract_audio(source_path, audio_path)
        logger.info("FFmpeg done      job_id=%s", job_id)

        logger.info("Whisper starting job_id=%s  language=%s", job_id, language)
        _job_state[job_id]["status"] = "transcribing"
        results = await transcribe_audio(audio_path, language)
        logger.info("Whisper done     job_id=%s  segments=%d", job_id, len(results))

        _job_state[job_id].update({
            "status":  "completed",
            "results": results,
            "txt":     format_as_txt(results),
            "srt":     format_as_srt(results),
        })

    except asyncio.TimeoutError:
        _job_state[job_id].update({
            "status": "error",
            "error": "Audio extraction timed out. The file may be too large or corrupted.",
        })
        logger.error("FFmpeg timeout   job_id=%s", job_id)

    except Exception as e:
        error_detail = _err(e)
        _job_state[job_id].update({"status": "error", "error": error_detail})
        logger.error("Pipeline failed for job_id=%s: %s", job_id, error_detail, exc_info=True)

    finally:
        _cleanup_dir(tmp_dir)


# ── File upload endpoint ──────────────────────────────────────────────────────

@router.post("/upload-video")
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Query(
        default="auto",
        description="'ta-IN' (Tamil), 'en-US' (English), or 'auto' (Whisper auto-detect).",
    ),
):
    """
    Accept a video/audio file and return a job_id immediately.
    FFmpeg + Whisper run in a background task; poll /api/transcription-status/{job_id}.
    """
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    tmp_dir = Path(settings.get_temp_dir()) / str(uuid.uuid4())
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "upload").suffix or ".mp4"
    video_path = str(tmp_dir / f"input{ext}")
    audio_path = str(tmp_dir / "audio.wav")

    try:
        async with aiofiles.open(video_path, "wb") as f:
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    _cleanup_dir(str(tmp_dir))
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum is {settings.MAX_FILE_SIZE_MB} MB.",
                    )
                await f.write(chunk)
        logger.info("Upload saved: %s (%d bytes)", video_path, total)

    except HTTPException:
        raise
    except Exception as e:
        _cleanup_dir(str(tmp_dir))
        raise HTTPException(status_code=500, detail=f"Failed to save file: {_err(e)}")

    job_id = str(uuid.uuid4())
    _job_state[job_id] = {
        "status":  "extracting",
        "error":   None,
        "title":   file.filename,
        "results": None,
        "txt":     None,
        "srt":     None,
    }

    background_tasks.add_task(_run_pipeline, job_id, video_path, audio_path, language, str(tmp_dir))

    logger.info("Job queued job_id=%s  language=%s", job_id, language)
    return {"job_id": job_id}


# ── YouTube URL endpoint ──────────────────────────────────────────────────────

@router.post("/transcribe-url")
async def transcribe_url(
    background_tasks: BackgroundTasks,
    url: str = Body(..., embed=True, description="YouTube video URL"),
    language: str = Query(
        default="auto",
        description="'ta-IN' (Tamil), 'en-US' (English), or 'auto'.",
    ),
):
    """
    Accept a YouTube URL and return a job_id immediately.
    yt-dlp download + FFmpeg + Whisper all run in a background task.
    """
    url = url.strip()
    if not is_youtube_url(url):
        raise HTTPException(
            status_code=400,
            detail=(
                "Only YouTube URLs are supported (youtube.com/watch?v=… or youtu.be/…). "
                "To transcribe other sources, upload the file directly."
            ),
        )

    tmp_dir = Path(settings.get_temp_dir()) / str(uuid.uuid4())
    tmp_dir.mkdir(parents=True, exist_ok=True)

    job_id = str(uuid.uuid4())
    _job_state[job_id] = {
        "status":  "downloading",
        "error":   None,
        "title":   url,
        "results": None,
        "txt":     None,
        "srt":     None,
    }

    background_tasks.add_task(
        _download_and_run_pipeline, job_id, url, str(tmp_dir), language
    )

    logger.info("YouTube job queued job_id=%s  url=%s  language=%s", job_id, url, language)
    return {"job_id": job_id}


async def _download_and_run_pipeline(
    job_id: str,
    url: str,
    tmp_dir: str,
    language: str,
) -> None:
    """Background task: yt-dlp download → FFmpeg → Whisper."""
    audio_path = str(Path(tmp_dir) / "audio.wav")
    try:
        logger.info("yt-dlp starting  job_id=%s", job_id)
        downloaded_path, title = await download_youtube_audio(url, tmp_dir)
        _job_state[job_id]["title"] = title
        logger.info("yt-dlp done      job_id=%s  title=%s", job_id, title)

        await _run_pipeline(job_id, downloaded_path, audio_path, language, tmp_dir)

    except Exception as e:
        _job_state[job_id].update({"status": "error", "error": _err(e)})
        logger.exception("YouTube download failed  job_id=%s", job_id)
        _cleanup_dir(tmp_dir)


# ── Status polling endpoint ───────────────────────────────────────────────────

@router.get("/transcription-status/{job_id}")
async def transcription_status(job_id: str):
    """
    Poll a batch job.

    Returns one of:
      {"status": "processing", "step": "…",  "progress": null, "title": "…"}
      {"status": "error",      "error": "…", "title": "…"}
      {"status": "completed",  "results": […], "txt": "…", "srt": "…", "title": "…"}
    """
    state = _job_state.get(job_id)
    if state is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may have expired or the server was restarted.",
        )

    title = state.get("title") or ""
    status = state["status"]

    if status == "downloading":
        return {"status": "processing", "step": "Downloading from YouTube…", "progress": None, "title": title}

    if status == "extracting":
        return {"status": "processing", "step": "Extracting audio (FFmpeg)…", "progress": None, "title": title}

    if status == "transcribing":
        return {"status": "processing", "step": "Transcribing with Whisper…", "progress": None, "title": title}

    if status == "error":
        error_msg = state.get("error") or "An unknown error occurred."
        _job_state.pop(job_id, None)
        return {"status": "error", "error": error_msg, "title": title}

    if status == "completed":
        results = state.get("results", [])
        txt     = state.get("txt", "")
        srt     = state.get("srt", "")
        _job_state.pop(job_id, None)
        return {
            "status":  "completed",
            "results": results,
            "txt":     txt,
            "srt":     srt,
            "title":   title,
        }

    return {"status": "processing", "step": "Starting…", "progress": None, "title": title}


# ── Helper ────────────────────────────────────────────────────────────────────

def _cleanup_dir(directory: str) -> None:
    try:
        shutil.rmtree(directory, ignore_errors=True)
        logger.info("Cleaned up: %s", directory)
    except Exception as e:
        logger.warning("Cleanup failed %s: %s", directory, e)
