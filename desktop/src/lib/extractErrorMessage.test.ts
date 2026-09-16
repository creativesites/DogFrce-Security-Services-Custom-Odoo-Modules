import { describe, expect, it } from "vitest";
import { extractErrorMessage } from "./extractErrorMessage";

describe("extractErrorMessage", () => {
  it("returns a real Error instance's message", () => {
    expect(extractErrorMessage(new Error("boom"))).toBe("boom");
  });

  it("falls back to the default when an Error has an empty message", () => {
    // Regression test: the original implementation checked
    // `err instanceof Error && err.message` (empty string is falsy) and
    // fell through to the generic object-shape branch below, which still
    // matched (Error has a `message` string property) and returned the
    // same empty string instead of the fallback — so a blank Error message
    // rendered as blank UI text instead of a helpful message. Fixed in
    // extractErrorMessage.ts to check message content directly within the
    // Error branch.
    expect(extractErrorMessage(new Error(""))).toBe("Something went wrong. Try again.");
  });

  it("falls back to the default for an Error with a whitespace-only message", () => {
    expect(extractErrorMessage(new Error("   "))).toBe("Something went wrong. Try again.");
  });

  it("extracts .message from the serialized Tauri AppError shape (kind/message tag)", () => {
    // Mirrors src-tauri/src/errors.rs's #[serde(tag = "kind", content = "message")]
    // shape, e.g. { kind: "network_unreachable", message: "Can't reach..." }.
    // Tauri command rejections deserialize to a plain object, not a JS Error,
    // so `err instanceof Error` is false for these — this is the primary
    // real-world case this function exists for.
    const rejection = { kind: "network_unreachable", message: "Can't reach DeployGuard ERP. Check your connection." };
    expect(extractErrorMessage(rejection)).toBe("Can't reach DeployGuard ERP. Check your connection.");
  });

  it("returns a plain non-empty string as-is", () => {
    expect(extractErrorMessage("Incorrect username or password")).toBe("Incorrect username or password");
  });

  it("falls back to default for a whitespace-only string", () => {
    expect(extractErrorMessage("   ")).toBe("Something went wrong. Try again.");
  });

  it("falls back to default for an empty string", () => {
    expect(extractErrorMessage("")).toBe("Something went wrong. Try again.");
  });

  it("falls back to default for null", () => {
    expect(extractErrorMessage(null)).toBe("Something went wrong. Try again.");
  });

  it("falls back to default for undefined", () => {
    expect(extractErrorMessage(undefined)).toBe("Something went wrong. Try again.");
  });

  it("falls back to default for a serialized error object with a whitespace-only message", () => {
    expect(extractErrorMessage({ kind: "unknown", message: "   " })).toBe("Something went wrong. Try again.");
  });

  it("falls back to default for an object with no message field", () => {
    expect(extractErrorMessage({ kind: "unknown" })).toBe("Something went wrong. Try again.");
  });

  it("falls back to default for an object whose message field is not a string", () => {
    expect(extractErrorMessage({ message: 42 })).toBe("Something went wrong. Try again.");
  });

  it("falls back to default for a bare number", () => {
    expect(extractErrorMessage(12345)).toBe("Something went wrong. Try again.");
  });

  it("respects a custom fallback argument", () => {
    expect(extractErrorMessage(null, "Custom fallback")).toBe("Custom fallback");
  });

  it("prefers the real Error branch even for an Error with extra fields", () => {
    const err = Object.assign(new Error("real error"), { kind: "server_error" });
    expect(extractErrorMessage(err)).toBe("real error");
  });
});
