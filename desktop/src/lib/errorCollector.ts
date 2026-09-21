/**
 * In-memory ring buffer for the last 5 client errors and system diagnostics.
 * docs/deployguard/34-feedback-and-support.md §1.3
 */

export interface CapturedError {
  timestamp: string;
  message: string;
  code?: string;
  context?: string;
}

export interface ClientDiagnostics {
  appVersion: string;
  route: string;
  task?: { id: number; name: string };
  online: boolean;
  platform: string;
  userAgent: string;
  timestamp: string;
  recentErrors: CapturedError[];
}

const MAX_ERRORS = 5;
const errorBuffer: CapturedError[] = [];

/** Redacts common sensitive tokens, passwords, and session cookies from error messages */
export function sanitizeErrorMessage(raw: string): string {
  if (!raw) return "";
  return raw
    .replace(/(password|session_id|token|secret|auth)\s*[:=]\s*["']?[^"'\s,]+["']?/gi, "$1: [REDACTED]")
    .slice(0, 500);
}

export function recordClientError(err: unknown, context?: string): void {
  const message = err instanceof Error ? err.message : String(err);
  const code = (err as { code?: string })?.code || (err as { name?: string })?.name;

  const captured: CapturedError = {
    timestamp: new Date().toISOString(),
    message: sanitizeErrorMessage(message),
    code: code ? String(code) : undefined,
    context,
  };

  errorBuffer.push(captured);
  if (errorBuffer.length > MAX_ERRORS) {
    errorBuffer.shift();
  }
}

export function getRecentErrors(): CapturedError[] {
  return [...errorBuffer];
}

export function clearRecentErrors(): void {
  errorBuffer.length = 0;
}

export function getClientDiagnostics(
  route: string = "/home",
  taskContext?: { id: number; name: string },
): ClientDiagnostics {
  return {
    appVersion: "0.1.0",
    route,
    task: taskContext,
    online: typeof navigator !== "undefined" ? navigator.onLine : true,
    platform: typeof navigator !== "undefined" ? navigator.platform : "unknown",
    userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "desktop-shell",
    timestamp: new Date().toISOString(),
    recentErrors: getRecentErrors(),
  };
}

// Global listener for unhandled errors in window if running in browser/tauri
if (typeof window !== "undefined") {
  window.addEventListener("error", (event) => {
    recordClientError(event.error || event.message, "uncaught_error");
  });
  window.addEventListener("unhandledrejection", (event) => {
    recordClientError(event.reason, "unhandled_promise_rejection");
  });
}
