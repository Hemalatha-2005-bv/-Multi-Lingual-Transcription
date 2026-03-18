from abc import ABC, abstractmethod


class ITranscriptionService(ABC):
    """Contract for batch transcription orchestration."""

    @abstractmethod
    async def start_file_job(
        self,
        job_id: str,
        source_path: str,
        tmp_dir: str,
        language: str,
    ) -> None:
        """Run FFmpeg + Whisper pipeline for an uploaded file."""

    @abstractmethod
    async def start_youtube_job(
        self,
        job_id: str,
        url: str,
        tmp_dir: str,
        language: str,
    ) -> None:
        """Download YouTube audio, then run FFmpeg + Whisper pipeline."""
