"""
Transcript output formatters — converts segment dicts to TXT and SRT.

Segment dict shape:
  {
    "transcript": str,
    "cleaned_text": str,   # Tamil-cleaned version (same as transcript for non-Tamil)
    "confidence": float,
    "language_code": str,
    "words": [{"word": str, "start_time": float, "end_time": float}]
  }
"""


def _to_txt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _to_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_as_txt(results: list[dict]) -> str:
    lines: list[str] = []
    for result in results:
        words = result.get("words", [])
        # Prefer cleaned_text for readability; fall back to raw transcript
        transcript = (result.get("cleaned_text") or result.get("transcript", "")).strip()
        if not transcript:
            continue
        if words:
            start = _to_txt_time(words[0]["start_time"])
            end = _to_txt_time(words[-1]["end_time"])
            lines.append(f"[{start} --> {end}]")
        else:
            lines.append("[--:--:-- --> --:--:--]")
        lines.append(transcript)
        lines.append("")
    return "\n".join(lines)


def format_as_srt(results: list[dict]) -> str:
    blocks: list[str] = []
    index = 1
    for result in results:
        words = result.get("words", [])
        transcript = result.get("transcript", "").strip()
        if not transcript or not words:
            continue
        start = _to_srt_time(words[0]["start_time"])
        end = _to_srt_time(words[-1]["end_time"])
        transcript = (result.get("cleaned_text") or transcript)
        blocks.extend([str(index), f"{start} --> {end}", transcript, ""])
        index += 1
    return "\n".join(blocks)
