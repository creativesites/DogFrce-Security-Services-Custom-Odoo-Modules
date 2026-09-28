export interface SessionInfo {
  uid: number;
  login: string;
  name: string;
  db: string;
}

/** Mirrors src-tauri/src/windowing.rs's `SessionEvent`. */
export type SessionEvent =
  | { status: "signed_in"; session: SessionInfo; auto_reveal: boolean }
  | { status: "signed_out" }
  | { status: "expired" };

/**
 * `expired` is distinct from `signed_out`: Odoo rejected the session while the
 * employee was working, and they need to be told so rather than silently
 * landing on a sign-in screen.
 */
export type SessionStatus = "checking" | "signed_in" | "signed_out" | "expired";
