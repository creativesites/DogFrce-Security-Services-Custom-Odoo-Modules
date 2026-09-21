import { describe, expect, it, beforeEach } from "vitest";
import {
  recordClientError,
  getRecentErrors,
  clearRecentErrors,
  sanitizeErrorMessage,
  getClientDiagnostics,
} from "./errorCollector";

describe("errorCollector", () => {
  beforeEach(() => {
    clearRecentErrors();
  });

  it("redacts sensitive fields in error messages", () => {
    const raw = "Authentication failed: password=SuperSecret123, session_id='abc123xyz'";
    const sanitized = sanitizeErrorMessage(raw);
    expect(sanitized).not.toContain("SuperSecret123");
    expect(sanitized).not.toContain("abc123xyz");
    expect(sanitized).toContain("[REDACTED]");
  });

  it("maintains a maximum of 5 recent errors in ring buffer", () => {
    for (let i = 1; i <= 7; i++) {
      recordClientError(new Error(`Error #${i}`), `test_step_${i}`);
    }
    const errors = getRecentErrors();
    expect(errors.length).toBe(5);
    expect(errors[0].message).toBe("Error #3");
    expect(errors[4].message).toBe("Error #7");
  });

  it("builds clean client diagnostics without personal credentials", () => {
    recordClientError("Network glitch", "api_call");
    const diag = getClientDiagnostics("/work", { id: 42, name: "Perimeter Sweep" });

    expect(diag.route).toBe("/work");
    expect(diag.task?.id).toBe(42);
    expect(diag.appVersion).toBe("0.1.0");
    expect(diag.recentErrors.length).toBe(1);
    expect(diag.recentErrors[0].message).toBe("Network glitch");
    expect(diag.timestamp).toBeDefined();
  });
});
