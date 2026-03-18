"""
YouTube audio download service using yt-dlp.

yt-dlp downloads the best-quality audio stream directly (no video downloaded),
then FFmpeg converts it to WAV in the next pipeline step.

Install: pip install yt-dlp

Note: Only use this to transcribe videos you have rights to transcribe.
"""

import asyncio
import logging
import os
import re

logger = logging.getLogger(__name__)

# Regex patterns that match YouTube video URLs in common formats
_YT_PATTERNS = [
    r"(?:https?://)?(?:www\.)?youtube\.com/watch\?(?:.*&)?v=[\w-]+",
    r"(?:https?://)?youtu\.be/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/shorts/[\w-]+",
    r"(?:https?://)?(?:www\.)?youtube\.com/embed/[\w-]+",
]


def is_youtube_url(url: str) -> bool:
    """Return True if the string looks like a YouTube video URL."""
    return any(re.search(p, url.strip()) for p in _YT_PATTERNS)


async def download_youtube_audio(url: str, output_dir: str) -> tuple[str, str]:
    """
    Download the best audio stream from a YouTube URL into output_dir.

    Returns:
        (downloaded_file_path, video_title)

    The downloaded file is typically .webm or .m4a.
    Pass it to audio_service.extract_audio() to convert to WAV.

    Raises:
        RuntimeError: on download failure with a human-readable message.
    """
    loop = asyncio.get_running_loop()

    def _download() -> tuple[str, str]:
        try:
            import yt_dlp
        except ImportError:
            raise RuntimeError(
                "yt-dlp is not installed. Run: pip install yt-dlp"
            )

        outtmpl = os.path.join(output_dir, "yt_audio.%(ext)s")

        ydl_opts = {
            # Best audio only — no video track (much faster download)
            "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
            "outtmpl": outtmpl,
            "noplaylist": True,       # Single video only, ignore playlists
            "quiet": True,
            "no_warnings": True,
            "ignoreerrors": False,
            "nocheckcertificate": True,
            # Common user-agent to avoid 403
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "referer": "https://www.google.com/",
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get("title", "YouTube Video") if info else "YouTube Video"

                # Resolve the actual filename yt-dlp wrote
                filename = ydl.prepare_filename(info)

                # yt-dlp sometimes changes the extension — scan output_dir
                if not os.path.exists(filename):
                    for fname in os.listdir(output_dir):
                        if fname.startswith("yt_audio"):
                            filename = os.path.join(output_dir, fname)
                            break

                if not os.path.exists(filename):
                    raise RuntimeError("yt-dlp ran but no output file was found.")

                logger.info("Downloaded: %s → %s", title, filename)
                return filename, title

        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            if "Private video" in msg:
                raise RuntimeError("This YouTube video is private and cannot be downloaded.")
            if "This video is not available" in msg or "Video unavailable" in msg:
                raise RuntimeError("This YouTube video is unavailable in your region or has been removed.")
            if "Sign in" in msg or "age" in msg.lower():
                raise RuntimeError("This YouTube video requires sign-in or is age-restricted.")
            raise RuntimeError(f"YouTube download failed: {msg}")

    return await loop.run_in_executor(None, _download)
