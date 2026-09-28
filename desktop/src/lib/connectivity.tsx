import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { invoke } from "./tauri";
import { useSession } from "../session/SessionContext";

/**
 * Honest connectivity (mission §18):
 * - `connecting`: startup, before the first check has answered
 * - `online`: DogForce ERP answered its health check
 * - `odoo_unreachable`: the network works, DogForce ERP doesn't answer
 * - `offline`: this computer has no network route
 * - `auth_expired`: Odoo rejected the session; sign in again
 */
export type ConnectivityState = "online" | "connecting" | "odoo_unreachable" | "offline" | "auth_expired";

export interface ConnectivityReport {
  state: ConnectivityState;
  message: string;
}

const POLL_MS = 20000;
const ConnectivityContext = createContext<ConnectivityReport | null>(null);

/** Combines the network report with the session state. Expiry wins while the
 * network is fine, because that is what the employee has to act on. */
export function effectiveConnectivity(network: ConnectivityReport, sessionExpired: boolean): ConnectivityReport {
  if (sessionExpired && network.state === "online") {
    return { state: "auth_expired", message: "Your session expired. Sign in again to continue." };
  }
  return network;
}

/** One poller for the whole shell. Every status indicator reads this context. */
export function ConnectivityProvider({ children }: { children: ReactNode }) {
  const { status } = useSession();
  const [network, setNetwork] = useState<ConnectivityReport>({ state: "connecting", message: "Checking connection…" });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    async function check() {
      try {
        const result = await invoke<ConnectivityReport>("connectivity_check");
        if (!cancelled) setNetwork(result);
      } catch {
        // The IPC call itself failed: the native side is unwell, not the network.
        if (!cancelled) setNetwork({ state: "odoo_unreachable", message: "Can't check the connection right now." });
      } finally {
        if (!cancelled) timer = setTimeout(check, POLL_MS);
      }
    }
    void check();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return (
    <ConnectivityContext.Provider value={effectiveConnectivity(network, status === "expired")}>
      {children}
    </ConnectivityContext.Provider>
  );
}

export function useConnectivity(): ConnectivityReport {
  const ctx = useContext(ConnectivityContext);
  if (!ctx) throw new Error("useConnectivity() must be used within <ConnectivityProvider>");
  return ctx;
}
