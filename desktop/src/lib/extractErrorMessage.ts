/**
 * Tauri command errors reject the JS promise with the *serialized value* of
 * the Rust `Err` variant (see src-tauri/src/errors.rs's
 * `#[serde(tag = "kind", content = "message")]`), not a JS `Error`
 * instance. `err instanceof Error` is therefore always false for these —
 * this normalizes both shapes to a user-facing string, and never leaks a
 * raw object into the UI.
 */
export function extractErrorMessage(err: unknown, fallback = "Something went wrong. Try again."): string {
  if (err instanceof Error && err.message) return err.message;
  if (
    err &&
    typeof err === "object" &&
    "message" in err &&
    typeof (err as { message: unknown }).message === "string"
  ) {
    return (err as { message: string }).message;
  }
  if (typeof err === "string" && err.trim().length > 0) return err;
  return fallback;
}
