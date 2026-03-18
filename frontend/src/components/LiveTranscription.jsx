/**
 * LiveTranscription component
 *
 * Manages microphone capture (MediaRecorder) and streams audio to the
 * backend WebSocket endpoint. Instead of real-time streaming, audio is
 * collected while recording and Whisper transcribes it all at once when
 * the user stops recording.
 *
 * Flow:
 *   1. User clicks "Start Recording" → open WebSocket + start MediaRecorder
 *   2. Audio chunks (WebM/Opus) are sent to backend every 250 ms
 *   3. User clicks "Stop Recording" → WebSocket closes
 *   4. Backend runs Whisper on all accumulated audio → sends back one "final" result
 *   5. Full transcript is displayed
 *
 * Props:
 *   onSegments(segments: Array) — called whenever segments update
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { WS_STATE, useWebSocket } from "../hooks/useWebSocket";
import { getLiveTranscriptionWsUrl } from "../services/api";

const LANGUAGE_OPTIONS = [
  { value: "auto",  label: "Auto-detect (Tamil & English)" },
  { value: "ta-IN", label: "Tamil (தமிழ்)" },
  { value: "en-US", label: "English" },
];

// Preferred MIME types in priority order
const MIME_PREFERENCE = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
];

function getSupportedMimeType() {
  for (const mime of MIME_PREFERENCE) {
    if (MediaRecorder.isTypeSupported(mime)) return mime;
  }
  return null;
}

export default function LiveTranscription({ onSegments }) {
  const [recording, setRecording]         = useState(false);
  const [language, setLanguage]           = useState("auto");
  const [finalSegments, setFinalSegments] = useState([]);
  const [processingMsg, setProcessingMsg] = useState(""); // "Transcribing with Whisper…"
  const [error, setError]                 = useState(null);
  const [browserSupported, setBrowserSupported] = useState(true);

  const mediaRecorderRef = useRef(null);
  const streamRef        = useRef(null);

  // Notify parent whenever final segments change
  useEffect(() => {
    onSegments?.(finalSegments);
  }, [finalSegments, onSegments]);

  const handleMessage = useCallback((msg) => {
    setProcessingMsg("");

    if (msg.type === "final") {
      // Whisper returns all segments at once when recording stops
      const segments = msg.segments?.length
        ? msg.segments
        : [{ transcript: msg.transcript, language_code: msg.language_code, words: [] }];
      setFinalSegments((prev) => [...prev, ...segments]);
    } else if (msg.type === "error") {
      setError("Transcription error: " + (msg.message || "Unknown error"));
    }
  }, []);

  const handleError = useCallback((errMsg) => {
    setError(errMsg);
    setRecording(false);
    setProcessingMsg("");
  }, []);

  const { connect, disconnect, sendAudio, connectionState } = useWebSocket({
    onMessage: handleMessage,
    onError: handleError,
    wsUrl: getLiveTranscriptionWsUrl(language),
  });

  async function startRecording() {
    setError(null);
    setProcessingMsg("");

    const mimeType = getSupportedMimeType();
    if (!mimeType) {
      setBrowserSupported(false);
      setError(
        "Your browser does not support WebM/Opus recording. " +
        "Please use Chrome, Edge, or Firefox."
      );
      return;
    }

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 48000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
    } catch (err) {
      setError("Microphone access denied. Please allow microphone permission.");
      return;
    }

    streamRef.current = stream;
    connect(); // Open WebSocket before starting MediaRecorder

    const recorder = new MediaRecorder(stream, {
      mimeType,
      audioBitsPerSecond: 64000,
    });

    recorder.ondataavailable = (evt) => {
      if (evt.data && evt.data.size > 0) {
        sendAudio(evt.data);
      }
    };

    recorder.start(250); // Fire ondataavailable every 250 ms
    mediaRecorderRef.current = recorder;
    setRecording(true);
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    disconnect(); // Closing the WebSocket signals the backend to run Whisper
    setRecording(false);
    setProcessingMsg("Transcribing with Whisper… this may take a few seconds.");
  }

  function clearTranscript() {
    setFinalSegments([]);
    setProcessingMsg("");
    setError(null);
  }

  const isConnecting =
    connectionState === WS_STATE.CONNECTING ||
    (recording && connectionState !== WS_STATE.CONNECTED);

  return (
    <div className="card">
      <h2>Live Microphone Transcription</h2>
      <p className="subtitle">
        Tamil &amp; English — speak, then stop to transcribe with Whisper
      </p>

      {/* Connection status badge */}
      <div className={`status-badge status-badge--${connectionState}`}>
        {connectionState === WS_STATE.CONNECTED    && "● Connected — recording"}
        {connectionState === WS_STATE.CONNECTING   && "◌ Connecting…"}
        {connectionState === WS_STATE.DISCONNECTED && "○ Disconnected"}
        {connectionState === WS_STATE.ERROR        && "✕ Connection error"}
        {connectionState === WS_STATE.IDLE         && "○ Idle — press Start to begin"}
      </div>

      {/* Controls */}
      <div className="live-controls">
        {!recording ? (
          <button
            className="btn btn--record"
            onClick={startRecording}
            disabled={!browserSupported}
          >
            🎙 Start Recording
          </button>
        ) : (
          <button className="btn btn--stop" onClick={stopRecording}>
            ■ Stop &amp; Transcribe
          </button>
        )}

        {finalSegments.length > 0 && (
          <button className="btn btn--ghost" onClick={clearTranscript}>
            Clear
          </button>
        )}
      </div>

      {/* Language selector — disabled while recording */}
      <div className="field-group">
        <label className="field-label" htmlFor="live-lang-select">Language</label>
        <select
          id="live-lang-select"
          className="select"
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          disabled={recording}
        >
          {LANGUAGE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      {error && <p className="error-text">{error}</p>}

      {/* Processing indicator */}
      {processingMsg && (
        <div className="processing-state" style={{ marginBottom: "12px" }}>
          <div className="spinner" />
          <p>{processingMsg}</p>
        </div>
      )}

      {/* Live transcript area */}
      <div className="live-transcript">
        {finalSegments.map((seg, i) => (
          <p key={i} className="segment segment--final">
            {seg.language_code && (
              <span className="segment__lang">[{seg.language_code}]</span>
            )}
            {" "}{seg.transcript}
          </p>
        ))}

        {!recording && finalSegments.length === 0 && !processingMsg && !error && (
          <p className="placeholder-text">
            Press "Start Recording", speak, then press "Stop &amp; Transcribe"…
          </p>
        )}

        {recording && (
          <p className="segment segment--interim">
            🔴 Recording… press "Stop &amp; Transcribe" when done.
          </p>
        )}
      </div>
    </div>
  );
}
