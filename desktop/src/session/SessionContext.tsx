import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "../lib/tauri";
import type { SessionEvent, SessionInfo, SessionStatus } from "./types";
import { nextSessionState, type SessionState } from "./sessionState";

interface SessionContextValue extends SessionState {
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export { sameSession } from "./sessionState";
export type { SessionStatus };

/**
 * There is no sign-IN action here — authentication happens entirely inside
 * Odoo's own login page, rendered in the separate "odoo" webview (see
 * src-tauri/src/windowing.rs). This context only reflects what Rust
 * observed after the fact: it listens for `deployguard://session-changed`
 * and seeds its initial state from `get_current_session` (in case the
 * event already fired before this webview finished loading — a real race,
 * since Odoo can navigate and sync before React mounts).
 */
export function SessionProviderRoot({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SessionState>({ status: "checking", session: null });

  useEffect(() => {
    let cancelled = false;

    invoke<SessionInfo | null>("get_current_session")
      .then((session) => {
        if (cancelled) return;
        setState((s) => (s.status === "checking" ? { status: session ? "signed_in" : "signed_out", session } : s));
      })
      .catch(() => {
        if (!cancelled) setState((s) => (s.status === "checking" ? { status: "signed_out", session: null } : s));
      });

    const unlistenPromise = listen<SessionEvent>("deployguard://session-changed", (event) => {
      if (!cancelled) setState((prev) => nextSessionState(prev, event.payload));
    });

    return () => {
      cancelled = true;
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {});
    };
  }, []);

  const signOut = async () => {
    await invoke<void>("auth_sign_out");
    setState({ status: "signed_out", session: null });
  };

  return <SessionContext.Provider value={{ ...state, signOut }}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession() must be used within <SessionProviderRoot>");
  return ctx;
}
