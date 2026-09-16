import { useConnectivity } from "../lib/connectivity";

const LABEL: Record<string, string> = {
  online: "Connected",
  connecting: "Connecting…",
  odoo_unreachable: "DeployGuard ERP is unavailable",
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

export function StatusBar() {
  const { state, message } = useConnectivity();
  if (state === "online") return null; // only show when something needs attention
  return (
    <div className="dg-statusbar" role="status">
      <span className={`dg-statusbar__dot ${DOT_CLASS[state]}`} aria-hidden="true" />
      <span>{message || LABEL[state]}</span>
    </div>
  );
}
