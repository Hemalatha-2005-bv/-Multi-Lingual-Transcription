/**
 * DownloadButtons component
 *
 * Renders download buttons for TXT and SRT transcript formats.
 * Uses the Blob + Object URL approach so no server round-trip is needed.
 *
 * Props:
 *   txt:      string | null  — plain-text transcript content
 *   srt:      string | null  — SRT subtitle file content
 *   filename: string         — base filename (without extension), default "transcript"
 */

export default function DownloadButtons({ txt, srt, filename = "transcript" }) {
  if (!txt && !srt) return null;

  return (
    <div className="download-buttons">
      <h3>Download Transcript</h3>
      <div className="download-buttons__row">
        {txt && (
          <DownloadButton
            content={txt}
            mimeType="text/plain"
            filename={`${filename}.txt`}
            label="Download .TXT"
          />
        )}
        {srt && (
          <DownloadButton
            content={srt}
            mimeType="text/srt"
            filename={`${filename}.srt`}
            label="Download .SRT"
          />
        )}
        {txt && (
          <CopyButton content={txt} />
        )}
      </div>
    </div>
  );
}

function DownloadButton({ content, mimeType, filename, label }) {
  function handleClick() {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button className="btn btn--download" onClick={handleClick}>
      ⬇ {label}
    </button>
  );
}

function CopyButton({ content }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback for non-HTTPS or unsupported browsers
      const ta = document.createElement("textarea");
      ta.value = content;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  return (
    <button className="btn btn--ghost" onClick={handleCopy}>
      {copied ? "✓ Copied!" : "Copy Text"}
    </button>
  );
}

// useState is needed for CopyButton
import { useState } from "react";
