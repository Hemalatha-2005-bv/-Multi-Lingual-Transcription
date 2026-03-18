"""Tests for TXT and SRT formatters."""

from app.utils.formatters import format_as_txt, format_as_srt

SAMPLE_RESULTS = [
    {
        "transcript": "Hello, how are you?",
        "confidence": -0.2,
        "language_code": "en",
        "words": [
            {"word": "Hello,", "start_time": 0.5, "end_time": 1.0},
            {"word": "how", "start_time": 1.1, "end_time": 1.4},
            {"word": "are", "start_time": 1.5, "end_time": 1.7},
            {"word": "you?", "start_time": 1.8, "end_time": 2.2},
        ],
    },
    {
        "transcript": "நான் நலமாக இருக்கிறேன்.",
        "confidence": -0.3,
        "language_code": "ta",
        "words": [
            {"word": "நான்", "start_time": 3.0, "end_time": 3.5},
            {"word": "நலமாக", "start_time": 3.6, "end_time": 4.1},
            {"word": "இருக்கிறேன்.", "start_time": 4.2, "end_time": 5.0},
        ],
    },
]


def test_format_as_txt_contains_timestamps():
    txt = format_as_txt(SAMPLE_RESULTS)
    assert "[00:00:00 --> 00:00:02]" in txt
    assert "Hello, how are you?" in txt
    assert "நான் நலமாக இருக்கிறேன்." in txt


def test_format_as_txt_skips_empty():
    results = [{"transcript": "", "confidence": 0.0, "language_code": "en", "words": []}]
    assert format_as_txt(results).strip() == ""


def test_format_as_srt_index_and_timestamps():
    srt = format_as_srt(SAMPLE_RESULTS)
    assert srt.startswith("1\n")
    assert "00:00:00,500 --> 00:00:02,200" in srt
    assert "Hello, how are you?" in srt
    assert "2\n" in srt


def test_format_as_srt_skips_no_words():
    results = [{"transcript": "No words", "confidence": 0.0, "language_code": "en", "words": []}]
    assert format_as_srt(results).strip() == ""


def test_format_as_srt_milliseconds():
    results = [
        {
            "transcript": "Test",
            "confidence": 0.0,
            "language_code": "en",
            "words": [{"word": "Test", "start_time": 61.5, "end_time": 62.75}],
        }
    ]
    srt = format_as_srt(results)
    assert "00:01:01,500 --> 00:01:02,750" in srt
