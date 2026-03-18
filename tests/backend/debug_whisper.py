"""
Debug script — verifies faster-whisper loads and transcribes a short WAV file.

Usage:
    cd backend
    uv run python ../tests/backend/debug_whisper.py [path/to/audio.wav]

If no file is provided, a 1-second silent WAV is generated and used.
"""

import sys
import struct
import wave
import io
import tempfile
import os


def make_silent_wav(duration_sec=1, sample_rate=16000) -> str:
    """Generate a minimal silent WAV file and return its path."""
    num_samples = sample_rate * duration_sec
    fd, path = tempfile.mkstemp(suffix=".wav")
    with os.fdopen(fd, "wb") as f:
        with wave.open(f, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(sample_rate)
            wav.writeframes(b"\x00\x00" * num_samples)
    return path


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None
    generated = False

    if not audio_path:
        print("No audio file provided — generating 1-second silent WAV…")
        audio_path = make_silent_wav()
        generated = True

    print(f"Audio file: {audio_path}")

    try:
        from faster_whisper import WhisperModel
        print("Loading faster-whisper 'tiny' model…")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("Model loaded.")

        segments, info = model.transcribe(audio_path, language=None, beam_size=1)
        print(f"Detected language: {info.language} (prob={info.language_probability:.2f})")
        results = list(segments)
        print(f"Segments: {len(results)}")
        for seg in results:
            print(f"  [{seg.start:.2f}s - {seg.end:.2f}s] {seg.text.strip()}")

        print("\nfaster-whisper is working correctly.")

    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if generated and os.path.exists(audio_path):
            os.remove(audio_path)


if __name__ == "__main__":
    main()
