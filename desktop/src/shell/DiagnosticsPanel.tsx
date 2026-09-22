import { useCallback, useState } from "react";
import { invoke } from "../lib/tauri";

interface Diagnostics {
  app_version: string;
  os: string;
  os_version: string;
  odoo_base_url: string;
  odoo_reachable: boolean;
  signed_in: boolean;
  last_sync_note: string | null;
  log_dir: string | null;
  generated_at: string;
}

function formatDiagnostics(d: Diagnostics): string {
  return [
    `DogForce Desktop v${d.app_version}`,
    `OS: ${d.os} ${d.os_version}`,
    `Server: ${d.odoo_base_url}`,
    `Server reachable: ${d.odoo_reachable ? "yes" : "no"}`,
    `Signed in: ${d.signed_in ? "yes" : "no"}`,
    `Last sign-in check: ${d.last_sync_note ?? "(no attempt yet this session)"}`,
    `Log files: ${d.log_dir ?? "(not available on this machine)"}`,
    `Generated: ${d.generated_at}`,
  ].join("\n");
}

/**
 * A "trouble signing in?" self-service report, reachable from the signed-
 * out empty state -- exactly where someone stuck failing to log in would
 * be looking. Distinguishes "can't reach the server at all" from "reached
 * it and it rejected the session" from "never even set a session cookie",
 * since those point at completely different fixes (network/firewall vs.
 * credentials vs. a webview quirk) and previously all looked identical:
 * the same "sign in to continue" screen with nothing to go on.
 */
export function DiagnosticsPanel() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<Diagnostics | null>(null);
  const [copied, setCopied] = useState(false);

  const reveal = useCallback(() => {
    setOpen(true);
    void invoke<Diagnostics>("diagnostics_get").then(setData);
  }, []);

  const copy = useCallback(() => {
    if (!data) return;
    void navigator.clipboard.writeText(formatDiagnostics(data)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [data]);

  if (!open) {
    return (
      <button type="button" className="dg-diagnostics__toggle" onClick={reveal}>
        Trouble signing in? Show diagnostics
      </button>
    );
  }

  return (
    <div className="dg-diagnostics">
      {data ? (
        <>
          <pre className="dg-diagnostics__body">{formatDiagnostics(data)}</pre>
          <button type="button" className="dg-btn dg-btn--secondary" onClick={copy}>
            {copied ? "Copied" : "Copy to send to support"}
          </button>
        </>
      ) : (
        <p className="dg-diagnostics__body">Collecting diagnostics…</p>
      )}
    </div>
  );
}
