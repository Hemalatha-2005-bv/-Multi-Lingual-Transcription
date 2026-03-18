/**
 * App — root component
 *
 * Two tabs:
 *   1. "Upload File"     — batch transcription for video/audio uploads
 *   2. "Live Microphone" — real-time transcription via WebSocket + Whisper
 */

import { useState } from "react";

import DownloadButtons from "./components/DownloadButtons";
import FileUpload from "./components/FileUpload";
import LiveTranscription from "./components/LiveTranscription";
import TranscriptionDisplay from "./components/TranscriptionDisplay";
import { usePolling } from "./hooks/usePolling";

const TABS = [
  { id: "upload", label: "📁 Upload File" },
  { id: "live",   label: "🎙 Live Mic" },
];

export default function App() {
  const [activeTab, setActiveTab] = useState("upload");

  // ── Batch transcription state ──────────────────────────────────────────────
  const [operationName, setOperationName] = useState(null);
  const { status, step, progress, results, txt, srt, error, title } = usePolling(operationName);

  function handleJobStarted(opName) {
    setOperationName(opName);
  }

  function handleNewUpload() {
    setOperationName(null);
  }

  // ── Live transcription state ───────────────────────────────────────────────
  const [liveSegments, setLiveSegments] = useState([]);
  const liveTxt = liveSegments.map((s) => s.transcript).join("\n") || null;

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <h1>Multi-Lingual Transcription</h1>
        <p>Tamil &amp; English · Powered by local Whisper</p>
      </header>

      {/* Tab bar */}
      <nav className="tab-bar">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={`tab-btn ${activeTab === tab.id ? "tab-btn--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Main content */}
      <main className="app-main">
        {activeTab === "upload" && (
          <>
            {!operationName ? (
              <FileUpload onJobStarted={handleJobStarted} />
            ) : (
              <>
                <TranscriptionDisplay
                  status={status}
                  step={step}
                  progress={progress}
                  results={results}
                  error={error}
                  title={title}
                />
                {status === "completed" && (
                  <DownloadButtons txt={txt} srt={srt} />
                )}
                {(status === "completed" || status === "error") && (
                  <div className="card" style={{ textAlign: "center" }}>
                    <button className="btn btn--ghost" onClick={handleNewUpload}>
                      ← Transcribe Another File
                    </button>
                  </div>
                )}
              </>
            )}
          </>
        )}

        {activeTab === "live" && (
          <>
            <LiveTranscription onSegments={setLiveSegments} />
            {liveSegments.length > 0 && (
              <DownloadButtons
                txt={liveTxt}
                srt={null}
                filename="live-transcript"
              />
            )}
          </>
        )}
      </main>

      <footer className="app-footer">
        <p>Powered by OpenAI Whisper (local, offline)</p>
      </footer>
    </div>
  );
}
