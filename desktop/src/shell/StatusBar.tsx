import { useConnectivity } from "../lib/connectivity";
import { useIsSyncing, useLastSyncedAt } from "../lib/queryCache";

const LABEL: Record<string, string> = {
  online: "Connected",
  connecting: "Connecting…",
  odoo_unreachable: "DogForce ERP is unavailable",
  offline: "You're offline",
  auth_expired: "Your session expired — sign in again",
};

const DOT_CLASS: Record<string, string> = {
  online: "dg-statusbar__dot--online",
  connecting: "dg-statusbar__dot--connecting",
  odoo_unreachable: "dg-statusbar__dot--degraded",
  offline: "dg-statusbar__dot--offline",
  auth_expired: "dg-statusbar__dot--degraded",
};

interface StatusBarProps {
  /** Toolbar-friendly rendering: a small dot with a tooltip instead of a
   * full-width banner. Shows live/syncing state when online. */
  compact?: boolean;
}

export function StatusBar({ compact = false }: StatusBarProps) {
  const { state, message } = useConnectivity();
  const isSyncing = useIsSyncing();
  const lastSyncedAt = useLastSyncedAt();

  if (state === "online") {
    // Only the compact toolbar indicator renders when online; the canvas banner stays hidden
    if (!compact) return null;

    const syncTitle = isSyncing
      ? "Syncing latest data with DogForce ERP…"
      : `Connected to DogForce ERP (synced ${new Date(lastSyncedAt).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })})`;

    return (
      <span
        className={`dg-statusbar-dot-wrap dg-statusbar-dot-wrap--compact ${isSyncing ? "is-syncing" : "is-live"}`}
        role="status"
        title={syncTitle}
      >
        <span
          className={`dg-statusbar__dot ${isSyncing ? "dg-statusbar__dot--syncing" : "dg-statusbar__dot--online"}`}
          aria-hidden="true"
        />
        <span className="dg-statusbar__label">{isSyncing ? "Syncing…" : "Live"}</span>
      </span>
    );
  }

  const label = message || LABEL[state];

  if (compact) {
    return (
      <span
        className="dg-statusbar-dot-wrap dg-statusbar-dot-wrap--compact"
        role="status"
        title={label}
      >
        <span className={`dg-statusbar__dot ${DOT_CLASS[state]}`} aria-hidden="true" />
        <span className="dg-statusbar__label">{label}</span>
      </span>
    );
  }

  return (
    <div className="dg-statusbar" role="status">
      <span className={`dg-statusbar__dot ${DOT_CLASS[state]}`} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}
