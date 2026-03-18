import os
import tempfile
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


def _default_temp_dir() -> str:
    """Return a platform-appropriate temp directory (works on Windows and Linux)."""
    return os.path.join(tempfile.gettempdir(), "transcription")


class Settings(BaseSettings):
    # Whisper model size: "tiny", "base", "small", "medium", "large"
    # "base" is a good default — fast on CPU, decent accuracy for Tamil & English.
    # Upgrade to "small" or "medium" for better Tamil accuracy (slower).
    WHISPER_MODEL: str = "base"

    # Local file storage
    # Leave blank to auto-detect system temp dir (cross-platform: works on Windows & Linux)
    TEMP_DIR: str = ""
    MAX_FILE_SIZE_MB: int = 500

    # CORS — add your frontend origin here
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8001",
    ]

    # Optional: absolute path to ffmpeg binary (leave empty to use system PATH)
    FFMPEG_PATH: str = "ffmpeg"
    FFPROBE_PATH: str = "ffprobe"

    def get_temp_dir(self) -> str:
        """Return the resolved temp directory path."""
        return self.TEMP_DIR or _default_temp_dir()

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
