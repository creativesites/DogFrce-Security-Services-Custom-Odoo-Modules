import { useConnectivity } from "../lib/connectivity";

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
   * full-width banner. Still hidden entirely when online. */
  compact?: boolean;
}

export function StatusBar({ compact = false }: StatusBarProps) {
  const { state, message } = useConnectivity();
  if (state === "online") return null; // only show when something needs attention

  const label = message || LABEL[state];

  if (compact) {
    return (
      <span className="dg-statusbar-dot-wrap" role="status" title={label}>
        <span className={`dg-statusbar__dot ${DOT_CLASS[state]}`} aria-hidden="true" />
        <span className="dg-sr-only">{label}</span>
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
