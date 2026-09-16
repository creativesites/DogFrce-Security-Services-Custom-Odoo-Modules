export interface SessionInfo {
  uid: number;
  login: string;
  name: string;
  db: string;
}

/** Mirrors src-tauri/src/windowing.rs's `SessionEvent`. */
export type SessionEvent =
  | { status: "signed_in"; session: SessionInfo; auto_reveal: boolean }
  | { status: "signed_out" };
