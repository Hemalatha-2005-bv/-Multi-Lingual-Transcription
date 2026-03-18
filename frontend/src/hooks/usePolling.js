/**
 * usePolling — custom hook that polls a status endpoint at a fixed interval
 * until the job reaches a terminal state (completed or error).
 *
 * Usage:
 *   const { status, results, txt, srt, error, progress } =
 *     usePolling(operationName, { interval: 3000 });
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { getTranscriptionStatus } from "../services/api";

const TERMINAL_STATUSES = new Set(["completed", "error"]);

/**
 * @param {string|null} operationName - Start polling when truthy, stop when null.
 * @param {object}      options
 * @param {number}      options.interval - Poll interval in ms (default: 3000).
 */
export function usePolling(operationName, { interval = 3000 } = {}) {
  const [state, setState] = useState({
    status: null,      // "processing" | "completed" | "error" | null
    step: null,        // "Downloading from YouTube…" | "Extracting audio…" | "Transcribing…" | null
    progress: null,    // 0-100 | null
    results: null,     // Array of transcript segments
    txt: null,         // Plain-text transcript
    srt: null,         // SRT subtitle file content
    error: null,       // Error message string
    title: null,       // Video/file title from backend
  });

  const timerRef = useRef(null);
  const isPolling = useRef(false);

  const poll = useCallback(async () => {
    if (!operationName || isPolling.current) return;
    isPolling.current = true;

    try {
      const data = await getTranscriptionStatus(operationName);
      setState((prev) => ({ ...prev, ...data, error: data.error ?? null }));

      if (TERMINAL_STATUSES.has(data.status)) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    } catch (err) {
      setState((prev) => ({
        ...prev,
        status: "error",
        error: err?.response?.data?.detail ?? err.message ?? "Polling failed",
      }));
      clearInterval(timerRef.current);
      timerRef.current = null;
    } finally {
      isPolling.current = false;
    }
  }, [operationName]);

  useEffect(() => {
    if (!operationName) {
      setState({
        status: null,
        step: null,
        progress: null,
        results: null,
        txt: null,
        srt: null,
        error: null,
        title: null,
      });
      return;
    }

    // Poll immediately, then on interval
    poll();
    timerRef.current = setInterval(poll, interval);

    return () => {
      clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [operationName, interval, poll]);

  return state;
}
