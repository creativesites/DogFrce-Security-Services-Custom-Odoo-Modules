import { invoke } from "../lib/tauri";

/**
 * Thin wrapper over the `odoo_call_kw` Tauri command (src-tauri/src/commands.rs).
 * The "shell" webview never holds the Odoo session cookie itself (see
 * DEVIATIONS.md D-1/D-2) — Rust makes the actual HTTP request using the
 * cookie it read from the "odoo" webview, and this just shapes the call the
 * way Odoo's own JS client would: `model.method(*args, **kwargs)`.
 *
 * Any model/method the signed-in user's own Odoo ACLs allow can be called
 * this way — there is no bespoke per-feature backend endpoint required.
 */
export async function callKw<T>(
  model: string,
  method: string,
  args: unknown[] = [],
  kwargs: Record<string, unknown> = {},
): Promise<T> {
  return invoke<T>("odoo_call_kw", { model, method, args, kwargs });
}
