try:
    from faster_whisper import WhisperModel
    import logging
    logging.basicConfig(level=logging.INFO)
    print("Attempting to load model 'tiny' with compute_type='int8'...")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")
    print("SUCCESS: Model loaded.")
except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
