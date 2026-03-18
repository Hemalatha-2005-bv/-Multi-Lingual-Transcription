"""
Transcription service — orchestrates infrastructure and persistence layers.

Pipeline for file uploads:
  FFmpeg (extract_audio) → Whisper (transcribe) → JobRepository (complete/fail)

Pipeline for YouTube URLs:
  yt-dlp (download_audio) → FFmpeg → Whisper → JobRepository
"""

import asyncio
import logging
import shutil
from pathlib import Path

from app.core.exceptions import AppError
from app.infrastructure import audio, whisper, ytdlp
from app.repositories.interfaces import IJobRepository
from app.services.interfaces import ITranscriptionService
from app.utils.formatters import format_as_srt, format_as_txt

logger = logging.getLogger(__name__)


class TranscriptionService(ITranscriptionService):
    def __init__(self, job_repo: IJobRepository) -> None:
        self._repo = job_repo

    async def start_file_job(
        self,
        job_id: str,
        source_path: str,
        tmp_dir: str,
        language: str,
    ) -> None:
        await self._run_pipeline(job_id, source_path, tmp_dir, language)

    async def start_youtube_job(
        self,
        job_id: str,
        url: str,
        tmp_dir: str,
        language: str,
    ) -> None:
        try:
            logger.info("yt-dlp starting job_id=%s", job_id)
            await self._set_status(job_id, "downloading")
            downloaded_path, title = await ytdlp.download_audio(url, tmp_dir)
            await self._update_title(job_id, title)
            logger.info("yt-dlp done job_id=%s title=%s", job_id, title)
            await self._run_pipeline(job_id, downloaded_path, tmp_dir, language)
        except AppError as e:
            await self._fail(job_id, str(e))
            logger.error("YouTube job failed job_id=%s: %s", job_id, e)
            _cleanup(tmp_dir)
        except Exception as e:
            await self._fail(job_id, f"{type(e).__name__}: {e}")
            logger.error("YouTube job error job_id=%s", job_id, exc_info=True)
            _cleanup(tmp_dir)

    async def _run_pipeline(
        self,
        job_id: str,
        source_path: str,
        tmp_dir: str,
        language: str,
    ) -> None:
        """
        FFmpeg → Whisper pipeline.
        Uses fresh DB sessions for every write so this is safe to run as a
        background task long after the original HTTP request session has closed.
        """
        audio_path = str(Path(tmp_dir) / "audio.wav")
        try:
            logger.info("FFmpeg starting job_id=%s", job_id)
            await self._set_status(job_id, "extracting")
            await audio.extract_audio(source_path, audio_path)
            logger.info("FFmpeg done job_id=%s", job_id)

            logger.info("Whisper starting job_id=%s language=%s", job_id, language)
            await self._set_status(job_id, "transcribing")
            results = await whisper.transcribe(audio_path, language)
            logger.info("Whisper done job_id=%s segments=%d", job_id, len(results))

            await self._complete(job_id, results)

        except asyncio.TimeoutError:
            await self._fail(
                job_id,
                "Audio extraction timed out. The file may be too large or corrupted.",
            )
            logger.error("FFmpeg timeout job_id=%s", job_id)
        except AppError as e:
            await self._fail(job_id, str(e))
            logger.error("Pipeline AppError job_id=%s: %s", job_id, e)
        except Exception as e:
            await self._fail(job_id, f"{type(e).__name__}: {e}")
            logger.error("Pipeline error job_id=%s", job_id, exc_info=True)
        finally:
            _cleanup(tmp_dir)

    # ── Fresh-session helpers for background operations ───────────────────────

    async def _set_status(self, job_id: str, status: str) -> None:
        from app.core.database import AsyncSessionLocal
        from app.repositories.job_repository import JobRepository
        async with AsyncSessionLocal() as session:
            await JobRepository(session).update_status(job_id, status)

    async def _complete(self, job_id: str, results: list) -> None:
        from app.core.database import AsyncSessionLocal
        from app.repositories.job_repository import JobRepository
        async with AsyncSessionLocal() as session:
            await JobRepository(session).complete(
                job_id,
                results,
                format_as_txt(results),
                format_as_srt(results),
            )

    async def _fail(self, job_id: str, error: str) -> None:
        from app.core.database import AsyncSessionLocal
        from app.repositories.job_repository import JobRepository
        async with AsyncSessionLocal() as session:
            await JobRepository(session).fail(job_id, error)

    async def _update_title(self, job_id: str, title: str) -> None:
        from app.core.database import AsyncSessionLocal
        from app.repositories.job_repository import JobRepository

        async with AsyncSessionLocal() as session:
            repo = JobRepository(session)
            job = await repo.get(job_id)
            if job:
                job.title = title
                await session.commit()


def _cleanup(directory: str) -> None:
    try:
        shutil.rmtree(directory, ignore_errors=True)
        logger.info("Cleaned up: %s", directory)
    except Exception as e:
        logger.warning("Cleanup failed %s: %s", directory, e)
