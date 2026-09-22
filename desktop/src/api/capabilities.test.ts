import { beforeEach, describe, expect, it, vi } from "vitest";

const callKw = vi.fn();
vi.mock("./odoo", () => ({ callKw: (...args: unknown[]) => callKw(...args) }));

const { FEATURE_MODELS, isAvailable, isModuleNotInstalled, probeCapabilities } = await import("./capabilities");

describe("isModuleNotInstalled", () => {
  it("recognises the Rust-classified missing module", () => {
    expect(isModuleNotInstalled({ kind: "module_not_installed", message: "x" })).toBe(true);
  });

  it("recognises an older server's KeyError only for the model asked about", () => {
    const err = { kind: "request_failed", message: "'security.owner.digest'" };
    expect(isModuleNotInstalled(err, "security.owner.digest")).toBe(true);
    expect(isModuleNotInstalled(err, "security.work.task")).toBe(false);
  });

  it("does not treat network, session or business errors as missing", () => {
    expect(isModuleNotInstalled({ kind: "network_unreachable", message: "x" })).toBe(false);
    expect(isModuleNotInstalled({ kind: "session_expired", message: "x" })).toBe(false);
    expect(isModuleNotInstalled({ kind: "request_failed", message: "Access denied" }, "security.work.task")).toBe(false);
    expect(isModuleNotInstalled(undefined)).toBe(false);
  });
});

describe("probeCapabilities", () => {
  beforeEach(() => callKw.mockReset());

  it("marks a feature unavailable only when its module is positively missing", async () => {
    callKw.mockImplementation(async (model: string) => {
      if (model === FEATURE_MODELS.adoption) throw { kind: "module_not_installed", message: "x" };
      if (model === FEATURE_MODELS.inbox) throw { kind: "network_unreachable", message: "offline" };
      return {};
    });
    const caps = await probeCapabilities();
    expect(isAvailable(caps, "adoption")).toBe(false);
    expect(isAvailable(caps, "inbox")).toBe(true);
    expect(isAvailable(caps, "work")).toBe(true);
  });

  it("treats a feature it hasn't probed yet as available", () => {
    expect(isAvailable({}, "owner")).toBe(true);
  });
});
