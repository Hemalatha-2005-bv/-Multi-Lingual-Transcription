/**
 * useWebSocket — manages a WebSocket connection for live transcription.
 *
 * Responsibilities:
 *   • Connect / disconnect lifecycle
 *   • Send binary audio chunks
 *   • Parse incoming JSON messages and dispatch to a callback
 *   • Expose connection state to the UI
 *
 * Usage:
 *   const { connect, disconnect, sendAudio, connectionState } =
 *     useWebSocket({ onMessage, onError });
 */

import { useCallback, useEffect, useRef, useState } from "react";

export const WS_STATE = {
  IDLE:         "idle",
  CONNECTING:   "connecting",
  CONNECTED:    "connected",
  DISCONNECTED: "disconnected",
  ERROR:        "error",
};

/**
 * @param {object}   options
 * @param {string}   options.wsUrl     - Full WebSocket URL (including query params).
 * @param {Function} options.onMessage - Called with a parsed transcript message object.
 * @param {Function} options.onError   - Called with an error message string.
 */
export function useWebSocket({ wsUrl, onMessage, onError } = {}) {
  const [connectionState, setConnectionState] = useState(WS_STATE.IDLE);
  const wsRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  // Keep callbacks up to date without re-running effects
  useEffect(() => { onMessageRef.current = onMessage; }, [onMessage]);
  useEffect(() => { onErrorRef.current = onError; }, [onError]);

  const wsUrlRef = useRef(wsUrl);
  useEffect(() => { wsUrlRef.current = wsUrl; }, [wsUrl]);

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    setConnectionState(WS_STATE.CONNECTING);
    const url = wsUrlRef.current;
    if (!url) {
      setConnectionState(WS_STATE.ERROR);
      onErrorRef.current?.("WebSocket URL is not configured");
      return;
    }
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setConnectionState(WS_STATE.CONNECTED);
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "error") {
          onErrorRef.current?.(msg.message || "Transcription error");
          return;
        }

        onMessageRef.current?.(msg);
      } catch (e) {
        console.warn("Failed to parse WebSocket message:", event.data);
      }
    };

    ws.onerror = () => {
      setConnectionState(WS_STATE.ERROR);
      onErrorRef.current?.("WebSocket connection error");
    };

    ws.onclose = (evt) => {
      setConnectionState(
        evt.wasClean ? WS_STATE.DISCONNECTED : WS_STATE.ERROR
      );
    };

    wsRef.current = ws;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, "User stopped recording");
      wsRef.current = null;
    }
    setConnectionState(WS_STATE.DISCONNECTED);
  }, []);

  /**
   * Send a binary audio chunk to the backend.
   * @param {Blob|ArrayBuffer} data
   */
  const sendAudio = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return { connect, disconnect, sendAudio, connectionState };
}
