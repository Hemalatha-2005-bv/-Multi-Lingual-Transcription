/**
 * TranscriptionDisplay component
 *
 * Shows the current state of a batch transcription job.
 *
 * Props:
 *   status:   "processing" | "completed" | "error" | null
 *   step:     string | null  — e.g. "Extracting audio…" or "Transcribing…"
 *   progress: number | null  — 0-100
 *   results:  Array | null
 *   error:    string | null
 */

export default function TranscriptionDisplay({ status, step, progress, results, error, title }) {
  // Immediately after upload: operationName is set but first poll hasn't returned yet.
  // Show a quick "Upload received" state so the user sees feedback right away.
  if (!status) {
    return (
      <div className="card transcription-display">
        <div className="processing-state">
          <div className="spinner" aria-label="Starting…" />
          <p>Upload received — starting processing…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="card transcription-display">

      {/* ── Processing ── */}
      {status === "processing" && (
        <div className="processing-state">
          {title && <p className="job-title">{title}</p>}
          <div className="spinner" aria-label="Processing…" />
          <p className="step-label">{step || "Processing…"}</p>

          {progress != null ? (
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: `${progress}%` }} />
              <span className="progress-label">{progress}%</span>
            </div>
          ) : (
            <p className="hint-text">
              {step === "Extracting audio (FFmpeg)…"
                ? "FFmpeg is converting your file to WAV. This takes a few seconds."
                : "Whisper is transcribing your audio locally. This may take 30–60 seconds for longer files."}
            </p>
          )}
        </div>
      )}

      {/* ── Error ── */}
      {status === "error" && (
        <div className="error-state">
          <p className="error-text">
            ✕ Transcription failed: {error}
          </p>
        </div>
      )}

      {/* ── Completed ── */}
      {status === "completed" && results && (
        <div className="results-state">
          <h3>✓ Transcription Complete</h3>
          {title && <p className="job-title">{title}</p>}
          <div className="segments-container">
            {results.length === 0 && (
              <p className="hint-text">
                No speech detected in the audio. Try a different file or language setting.
              </p>
            )}
            {results.map((seg, i) => (
              <div key={i} className="segment-block">
                <div className="segment-meta">
                  {seg.words?.length > 0 && (
                    <span className="segment-time">
                      {formatTime(seg.words[0].start_time)}
                      {" → "}
                      {formatTime(seg.words[seg.words.length - 1].end_time)}
                    </span>
                  )}
                  {seg.language_code && (
                    <span className="segment-lang">{seg.language_code}</span>
                  )}
                  {seg.language_code && (
                    <span className="segment-confidence">
                      Whisper local
                    </span>
                  )}
                </div>
                <p className="segment-text">{seg.transcript}</p>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}

function formatTime(seconds) {
  if (seconds == null) return "--:--";
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}
