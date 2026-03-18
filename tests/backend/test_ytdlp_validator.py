"""Tests for YouTube URL validation."""

from app.infrastructure.ytdlp import is_youtube_url, validate_youtube_url
from app.core.exceptions import InvalidURLError
import pytest


@pytest.mark.parametrize("url", [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "http://youtube.com/watch?v=abc123",
    "https://youtu.be/dQw4w9WgXcQ",
    "https://www.youtube.com/shorts/abc123",
    "https://www.youtube.com/embed/abc123",
    "youtube.com/watch?v=test123",
])
def test_valid_youtube_urls(url):
    assert is_youtube_url(url)


@pytest.mark.parametrize("url", [
    "https://vimeo.com/123456",
    "https://example.com/video.mp4",
    "not-a-url",
    "",
    "https://youtu.be",
])
def test_invalid_youtube_urls(url):
    assert not is_youtube_url(url)


def test_validate_raises_for_invalid():
    with pytest.raises(InvalidURLError):
        validate_youtube_url("https://vimeo.com/123")


def test_validate_passes_for_valid():
    validate_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
