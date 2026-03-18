/**
 * LocalModeBanner
 *
 * Replaces the old CredentialsBanner (Google Cloud credentials warning).
 * Shows a simple "running offline" notice — no credentials needed.
 */

export default function CredentialsBanner() {
  return (
    <div className="credentials-banner credentials-banner--ok">
      <span className="credentials-banner__icon">🔒</span>
      <span className="credentials-banner__msg">
        Running fully offline — powered by local OpenAI Whisper. No cloud or API keys required.
      </span>
    </div>
  );
}
