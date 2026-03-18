"""
HTTP endpoints for batch transcription.

POST /api/upload-video      → save file, queue FFmpeg+Whisper, return {job_id}
POST /api/transcribe-url    → validate YouTube URL, queue download+pipeline, return {job_id}
GET  /api/transcription-status/{job_id} → poll job state
"""

import logging
import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, Query, UploadFile

from app.api.deps import get_job_repository, get_transcription_service
from app.core.config import get_settings
from app.core.exceptions import InvalidURLError, JobNotFoundError
from app.infrastructure.ytdlp import validate_youtube_url
from app.repositories.job_repository import JobRepository
from app.services.transcription_service import TranscriptionService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter()


@router.post("/upload-video", tags=["Transcription"])
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Query(default="auto", description="ta-IN | en-US | auto"),
    repo: JobRepository = Depends(get_job_repository),
    service: TranscriptionService = Depends(get_transcription_service),
):
    """Save uploaded file and start transcription pipeline in the background."""
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    tmp_dir = Path(settings.get_temp_dir()) / str(uuid.uuid4())
    tmp_dir.mkdir(parents=True, exist_ok=True)

    ext = Path(file.filename or "upload").suffix or ".mp4"
    source_path = str(tmp_dir / f"input{ext}")

    try:
        async with aiofiles.open(source_path, "wb") as f:
            total = 0
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    import shutil
                    shutil.rmtree(str(tmp_dir), ignore_errors=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum is {settings.MAX_FILE_SIZE_MB} MB.",
                    )
                await f.write(chunk)
        logger.info("Upload saved: %s (%d bytes)", source_path, total)
    except HTTPException:
        raise
    except Exception as e:
        import shutil
        shutil.rmtree(str(tmp_dir), ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    job_id = str(uuid.uuid4())
    await repo.create(job_id, file.filename or "upload")

    background_tasks.add_task(
        service.start_file_job, job_id, source_path, str(tmp_dir), language
    )
    logger.info("Job queued job_id=%s language=%s", job_id, language)
    return {"job_id": job_id}


@router.post("/transcribe-url", tags=["Transcription"])
async def transcribe_url(
    background_tasks: BackgroundTasks,
    url: str = Body(..., embed=True),
    language: str = Query(default="auto", description="ta-IN | en-US | auto"),
    repo: JobRepository = Depends(get_job_repository),
    service: TranscriptionService = Depends(get_transcription_service),
):
    """Accept a YouTube URL and start the download+transcription pipeline."""
    url = url.strip()
    try:
        validate_youtube_url(url)
    except InvalidURLError:
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
    await repo.create(job_id, url)

    background_tasks.add_task(
        service.start_youtube_job, job_id, url, str(tmp_dir), language
    )
    logger.info("YouTube job queued job_id=%s url=%s language=%s", job_id, url, language)
    return {"job_id": job_id}


@router.get("/transcription-status/{job_id}", tags=["Transcription"])
async def transcription_status(
    job_id: str,
    repo: JobRepository = Depends(get_job_repository),
):
    """Poll the state of a transcription job."""
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail=f"Job '{job_id}' not found. It may have expired or the server was restarted.",
        )

    title = job.title or ""
    status = job.status

    if status in ("pending", "downloading"):
        step = "Downloading from YouTube…" if status == "downloading" else "Starting…"
        return {"status": "processing", "step": step, "progress": None, "title": title}

    if status == "extracting":
        return {"status": "processing", "step": "Extracting audio…", "progress": None, "title": title}

    if status == "transcribing":
        return {"status": "processing", "step": "Transcribing with Whisper…", "progress": None, "title": title}

    if status == "error":
        return {"status": "error", "error": job.error or "An unknown error occurred.", "title": title}

    if status == "completed":
        return {
            "status": "completed",
            "results": job.get_results(),
            "txt": job.txt or "",
            "srt": job.srt or "",
            "title": title,
        }

    return {"status": "processing", "step": "Processing…", "progress": None, "title": title}
