import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "../lib/tauri";
import type { SessionEvent, SessionInfo } from "./types";

interface SessionState {
  status: "checking" | "signed_in" | "signed_out";
  session: SessionInfo | null;
  isExpired?: boolean;
}

interface SessionContextValue extends SessionState {
  signOut: () => Promise<void>;
  markExpired: () => void;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function sameSession(a: SessionInfo | null, b: SessionInfo | null): boolean {
  if (!a || !b) return a === b;
  return a.uid === b.uid && a.db === b.db && a.login === b.login && a.name === b.name;
}

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
  const [state, setState] = useState<SessionState>({ status: "checking", session: null, isExpired: false });

  useEffect(() => {
    let cancelled = false;

    invoke<SessionInfo | null>("get_current_session")
      .then((session) => {
        if (cancelled) return;
        setState((s) =>
          s.status === "checking" ? { status: session ? "signed_in" : "signed_out", session, isExpired: false } : s,
        );
      })
      .catch(() => {
        if (!cancelled) setState((s) => (s.status === "checking" ? { status: "signed_out", session: null, isExpired: false } : s));
      });

    const unlistenPromise = listen<SessionEvent>("deployguard://session-changed", (event) => {
      if (cancelled) return;
      const payload = event.payload;
      if (payload.status === "signed_in") {
        // Rust re-announces "signed in" after every Odoo page load. Keep the
        // existing state when nothing changed -- a fresh object each time
        // made every effect keyed on `session` re-run as if someone had just
        // signed in (onboarding reappearing, the module probe flickering the
        // menu, the app view re-opening).
        setState((prev) =>
          prev.status === "signed_in" && !prev.isExpired && sameSession(prev.session, payload.session)
            ? prev
            : { status: "signed_in", session: payload.session, isExpired: false },
        );
      } else {
        setState((prev) => ({
          status: "signed_out",
          session: null,
          isExpired: prev.status === "signed_in" || prev.isExpired,
        }));
      }
    });

    return () => {
      cancelled = true;
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {});
    };
  }, []);

  const signOut = async () => {
    await invoke<void>("auth_sign_out");
    setState({ status: "signed_out", session: null, isExpired: false });
  };

  const markExpired = () => {
    setState((s) => ({ ...s, isExpired: true }));
  };

  return <SessionContext.Provider value={{ ...state, signOut, markExpired }}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession() must be used within <SessionProviderRoot>");
  return ctx;
}
