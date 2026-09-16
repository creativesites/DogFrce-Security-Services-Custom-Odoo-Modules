import { useEffect, useState } from "react";
import { invoke } from "./tauri";

export type ConnectivityState =
  | "online"
  | "connecting"
  | "odoo_unreachable"
  | "offline"
  | "auth_expired";

interface ConnectivityReport {
  state: ConnectivityState;
  message: string;
}

/**
 * Polls Rust-side reachability (network + Odoo /web/health) every 20s.
 * Mission spec §7: never fail silently — the user always knows why
 * something isn't working.
 */
export function useConnectivity(): ConnectivityReport {
  const [report, setReport] = useState<ConnectivityReport>({
    state: "connecting",
    message: "Checking connection…",
  });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    async function check() {
      try {
        const result = await invoke<ConnectivityReport>("connectivity_check");
        if (!cancelled) setReport(result);
      } catch {
        if (!cancelled) {
          setReport({ state: "offline", message: "Can't reach DogForce right now." });
        }
      } finally {
        if (!cancelled) timer = setTimeout(check, 20000);
      }
    }

    check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return report;
}
