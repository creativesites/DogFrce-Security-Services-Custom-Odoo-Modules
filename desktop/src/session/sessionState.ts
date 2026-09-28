import type { SessionEvent, SessionInfo, SessionStatus } from "./types";

export interface SessionState {
  status: SessionStatus;
  session: SessionInfo | null;
}

export function sameSession(a: SessionInfo | null, b: SessionInfo | null): boolean {
  if (!a || !b) return a === b;
  return a.uid === b.uid && a.db === b.db && a.login === b.login && a.name === b.name;
}

/**
 * Pure transition for `deployguard://session-changed`. Kept separate from the
 * provider so it can be tested without Tauri.
 */
export function nextSessionState(prev: SessionState, event: SessionEvent): SessionState {
  switch (event.status) {
    case "signed_in":
      // Rust re-announces "signed in" after every Odoo page load. Keep the
      // existing state object when nothing changed. A fresh object each time
      // made every effect keyed on `session` re-run as if someone had just
      // signed in (onboarding reappearing, the module probe flickering the
      // menu, the app view re-opening). See commit 40d5849.
      return prev.status === "signed_in" && sameSession(prev.session, event.session)
        ? prev
        : { status: "signed_in", session: event.session };
    case "expired":
      return { status: "expired", session: null };
    case "signed_out":
      // A sign-out that follows an expiry keeps the explanation on screen
      // until the employee signs in again.
      return prev.status === "expired" ? prev : { status: "signed_out", session: null };
  }
}
