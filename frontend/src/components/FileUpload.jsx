/**
 * FileUpload component
 *
 * Two input modes selectable via an inner tab bar:
 *   • "Upload File"  — drag-drop or browse for a local video/audio file
 *   • "YouTube URL"  — paste a YouTube link; backend downloads it via yt-dlp
 *
 * Both modes share the same language selector and call onJobStarted(jobId)
 * when the backend returns a job_id.
 */

import { useRef, useState } from "react";
import { transcribeUrl, uploadVideo } from "../services/api";

const ACCEPTED_TYPES = [
  "video/mp4", "video/x-msvideo", "video/quicktime", "video/webm",
  "video/x-matroska", "audio/mpeg", "audio/wav", "audio/ogg",
  "audio/webm", "audio/flac", "audio/aac",
];
const ACCEPTED_EXTENSIONS = ".mp4,.avi,.mov,.webm,.mkv,.mp3,.wav,.ogg,.flac,.aac";

const LANGUAGE_OPTIONS = [
  { value: "auto",  label: "Auto-detect (Tamil & English)" },
  { value: "ta-IN", label: "Tamil (தமிழ்)" },
  { value: "en-US", label: "English" },
];

const YT_PATTERN = /(?:youtube\.com\/(?:watch\?(?:.*&)?v=|shorts\/|embed\/)|youtu\.be\/)[\w-]+/i;

export default function FileUpload({ onJobStarted }) {
  const [inputMode, setInputMode] = useState("file");   // "file" | "youtube"
  const [language, setLanguage]   = useState("auto");
  const [busy, setBusy]           = useState(false);
  const [error, setError]         = useState(null);

  // File-mode state
  const [file, setFile]           = useState(null);
  const [uploadPct, setUploadPct] = useState(0);
  const inputRef = useRef(null);

  // YouTube-mode state
  const [ytUrl, setYtUrl]         = useState("");

  // ── Handlers ─────────────────────────────────────────────────────────────

  function handleFileChange(e) {
    const selected = e.target.files?.[0];
    if (!selected) return;
    if (selected.type !== "" && !ACCEPTED_TYPES.includes(selected.type)) {
      setError(`Unsupported file type: ${selected.type}`);
      return;
    }
    setFile(selected);
    setError(null);
    setUploadPct(0);
  }

  function handleDrop(e) {
    e.preventDefault();
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) { setFile(dropped); setError(null); setUploadPct(0); }
  }

  async function handleSubmitFile() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const result = await uploadVideo(file, language, setUploadPct);
      onJobStarted(result.job_id);
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitUrl() {
    const trimmed = ytUrl.trim();
    if (!trimmed) { setError("Please enter a YouTube URL."); return; }
    if (!YT_PATTERN.test(trimmed)) {
      setError("That doesn't look like a YouTube URL. Expected youtube.com/watch?v=… or youtu.be/…");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const result = await transcribeUrl(trimmed, language);
      onJobStarted(result.job_id);
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? "Request failed");
    } finally {
      setBusy(false);
    }
  }

  function switchMode(mode) {
    setInputMode(mode);
    setError(null);
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="card">
      <h2>Transcribe Audio / Video</h2>

      {/* Inner source tab bar */}
      <div className="source-tabs">
        <button
          className={`source-tab ${inputMode === "file" ? "source-tab--active" : ""}`}
          onClick={() => switchMode("file")}
          disabled={busy}
        >
          📁 Upload File
        </button>
        <button
          className={`source-tab ${inputMode === "youtube" ? "source-tab--active" : ""}`}
          onClick={() => switchMode("youtube")}
          disabled={busy}
        >
          ▶ YouTube URL
        </button>
      </div>

      {/* ── File upload mode ── */}
      {inputMode === "file" && (
        <>
          <p className="subtitle">
            Supported: MP4, AVI, MOV, WebM, MKV, MP3, WAV, OGG, FLAC, AAC
          </p>
          <div
            className={`dropzone ${file ? "dropzone--has-file" : ""}`}
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
          >
            {file ? (
              <div className="dropzone__file-info">
                <span className="dropzone__filename">{file.name}</span>
                <span className="dropzone__filesize">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </span>
              </div>
            ) : (
              <div className="dropzone__placeholder">
                <span className="dropzone__icon">📁</span>
                <span>Drag &amp; drop a file here, or click to browse</span>
              </div>
            )}
          </div>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            onChange={handleFileChange}
            style={{ display: "none" }}
          />
          {busy && (
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: `${uploadPct}%` }} />
              <span className="progress-label">{uploadPct}%</span>
            </div>
          )}
        </>
      )}

      {/* ── YouTube URL mode ── */}
      {inputMode === "youtube" && (
        <>
          <p className="subtitle">
            Paste any YouTube video link — the server downloads the audio automatically.
          </p>
          <div className="field-group">
            <label className="field-label" htmlFor="yt-url-input">YouTube URL</label>
            <input
              id="yt-url-input"
              type="url"
              className="text-input"
              placeholder="https://www.youtube.com/watch?v=..."
              value={ytUrl}
              onChange={(e) => { setYtUrl(e.target.value); setError(null); }}
              disabled={busy}
              onKeyDown={(e) => e.key === "Enter" && !busy && handleSubmitUrl()}
            />
          </div>
          {ytUrl && !YT_PATTERN.test(ytUrl.trim()) && (
            <p className="hint-text" style={{ color: "var(--color-text-muted)" }}>
              Enter a link like: youtube.com/watch?v=XXXXXXXXXXX or youtu.be/XXXXXXXXXXX
            </p>
          )}
        </>
      )}

      {/* ── Shared: language selector ── */}
      <div className="field-group">
        <label className="field-label" htmlFor="language-select">Language</label>
        <select
          id="language-select"
          className="select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={busy}
        >
          {LANGUAGE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {/* ── Error ── */}
      {error && <p className="error-text">{error}</p>}

      {/* ── Submit button ── */}
      {inputMode === "file" ? (
        <button
          className="btn btn--primary"
          onClick={handleSubmitFile}
          disabled={!file || busy}
        >
          {busy ? "Uploading…" : "Transcribe File"}
        </button>
      ) : (
        <button
          className="btn btn--primary"
          onClick={handleSubmitUrl}
          disabled={!ytUrl.trim() || busy}
        >
          {busy ? "Submitting…" : "Transcribe YouTube Video"}
        </button>
      )}
    </div>
  );
}
