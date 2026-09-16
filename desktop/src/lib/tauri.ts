import { invoke as tauriInvoke } from "@tauri-apps/api/core";

/**
 * Thin, typed wrapper over the Tauri IPC surface. Every Rust command this
 * app calls is listed here — see docs/deployguard/17-desktop-architecture.md
 * §3 for the target allowlist shape (this MVP slice implements a subset).
 */
export async function invoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return tauriInvoke<T>(cmd, args);
}
