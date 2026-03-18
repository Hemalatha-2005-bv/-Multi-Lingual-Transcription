"""
yt-dlp wrapper for downloading YouTube audio streams.
"""

import asyncio
import logging
import os
import re

from app.core.exceptions import DownloadError, InvalidURLError

logger = logging.getLogger(__name__)

_YT_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=[\w-]+",
    r"(?:https?://)?youtu\.be/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
]


def is_youtube_url(url: str) -> bool:
    return any(re.search(p, url.strip()) for p in _YT_PATTERNS)


def validate_youtube_url(url: str) -> None:
    if not is_youtube_url(url):
        raise InvalidURLError(url)


async def download_audio(url: str, output_dir: str) -> tuple[str, str]:
    """
    Download best-quality audio from a YouTube URL.

    Returns (file_path, video_title).
    The downloaded file is .webm or .m4a — pass to audio.extract_audio() next.

    Raises DownloadError on failure.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _download_sync, url, output_dir)


def _download_sync(url: str, output_dir: str) -> tuple[str, str]:
    try:
        import yt_dlp
    except ImportError:
        raise DownloadError("yt-dlp is not installed. Run: uv add yt-dlp")

    outtmpl = os.path.join(output_dir, "yt_audio.%(ext)s")
    ydl_opts = {
        "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": False,
        "nocheckcertificate": True,
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "referer": "https://www.google.com/",
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = (info.get("title", "YouTube Video") if info else "YouTube Video")
            filename = ydl.prepare_filename(info)

            if not os.path.exists(filename):
                for fname in os.listdir(output_dir):
                    if fname.startswith("yt_audio"):
                        filename = os.path.join(output_dir, fname)
                        break

            if not os.path.exists(filename):
                raise DownloadError("yt-dlp ran but produced no output file.")

            logger.info("Downloaded: %s → %s", title, filename)
            return filename, title

    except yt_dlp.utils.DownloadError as e:
        msg = str(e)
        if "Private video" in msg:
            raise DownloadError("This YouTube video is private.")
        if "Video unavailable" in msg or "not available" in msg:
            raise DownloadError("This YouTube video is unavailable or has been removed.")
        if "Sign in" in msg or "age" in msg.lower():
            raise DownloadError("This YouTube video requires sign-in or is age-restricted.")
        raise DownloadError(f"YouTube download failed: {msg}") from e
