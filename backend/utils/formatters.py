"""
Transcript formatting utilities.

Converts the list of result dicts produced by speech_service into
human-readable TXT and SRT subtitle files.

Expected result dict shape:
    {
        "transcript": str,
        "confidence": float,
        "language_code": str,
        "words": [{"word": str, "start_time": float, "end_time": float}, ...]
    }
"""


def _seconds_to_txt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _seconds_to_srt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm (SRT timestamp format)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_as_txt(results: list[dict]) -> str:
    """
    Plain-text transcript with timestamps.

    Example output:
        [00:00:01 --> 00:00:04]
        Hello, how are you?

        [00:00:05 --> 00:00:09]
        நான் நலமாக இருக்கிறேன்.
    """
    lines: list[str] = []

    for result in results:
        words = result.get("words", [])
        transcript = result.get("transcript", "").strip()
        if not transcript:
            continue

        if words:
            start = _seconds_to_txt_time(words[0]["start_time"])
            end = _seconds_to_txt_time(words[-1]["end_time"])
            lines.append(f"[{start} --> {end}]")
        else:
            lines.append("[--:--:-- --> --:--:--]")

        lines.append(transcript)
        lines.append("")  # blank line between segments

    return "\n".join(lines)


def format_as_srt(results: list[dict]) -> str:
    """
    SRT subtitle format.

    Example output:
        1
        00:00:01,000 --> 00:00:04,500
        Hello, how are you?

        2
        00:00:05,000 --> 00:00:09,200
        நான் நலமாக இருக்கிறேன்.
    """
    blocks: list[str] = []
    index = 1

    for result in results:
        words = result.get("words", [])
        transcript = result.get("transcript", "").strip()
        if not transcript or not words:
            continue

        start = _seconds_to_srt_time(words[0]["start_time"])
        end = _seconds_to_srt_time(words[-1]["end_time"])

        blocks.append(str(index))
        blocks.append(f"{start} --> {end}")
        blocks.append(transcript)
        blocks.append("")  # SRT blocks must be separated by a blank line

        index += 1

    return "\n".join(blocks)
