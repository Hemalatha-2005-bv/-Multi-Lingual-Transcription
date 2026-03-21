import os
import tempfile
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


def _default_temp_dir() -> str:
    return os.path.join(tempfile.gettempdir(), "transcription")


class Settings(BaseSettings):
    # Whisper model: tiny | base | small | medium | large
    WHISPER_MODEL: str = "base"

    # Storage
    TEMP_DIR: str = ""
    MAX_FILE_SIZE_MB: int = 500

    # Database — SQLite file path (relative to backend dir)
    DATABASE_URL: str = "sqlite+aiosqlite:///./transcription.db"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://multi-lingual-transcription.vercel.app",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v):
        if isinstance(v, str) and not v.strip():
            return [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:8000",
                "https://multi-lingual-transcription.vercel.app",
            ]
        return v

    # FFmpeg / FFprobe paths (use system PATH by default)
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    def get_temp_dir(self) -> str:
        return self.TEMP_DIR or _default_temp_dir()

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
