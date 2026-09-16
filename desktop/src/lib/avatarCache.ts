/**
 * Per-viewer localStorage cache for the signed-in user's Odoo avatar
 * (fetched once via the `odoo_fetch_avatar` Rust command, which returns a
 * `data:` URL — see src-tauri/src/odoo.rs). Never touches the network
 * itself; that's the caller's job. Wrapped in try/catch throughout since
 * localStorage can throw (private browsing, cleared/blocked site data) and
 * the avatar is a cosmetic nice-to-have, never something to crash over.
 */

const KEY_PREFIX = "dg-avatar:";

export function getCachedAvatar(uid: number): string | null {
  try {
    return window.localStorage.getItem(KEY_PREFIX + uid);
  } catch {
    return null;
  }
}

export function setCachedAvatar(uid: number, dataUrl: string): void {
  try {
    window.localStorage.setItem(KEY_PREFIX + uid, dataUrl);
  } catch {
    // Best-effort only — a full quota or blocked storage just means we
    // re-fetch next launch instead of reading from cache.
  }
}

export function clearCachedAvatar(uid: number): void {
  try {
    window.localStorage.removeItem(KEY_PREFIX + uid);
  } catch {
    // Nothing to do — see setCachedAvatar.
  }
}
