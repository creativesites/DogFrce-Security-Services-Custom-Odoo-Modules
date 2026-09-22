import { describe, expect, it } from "vitest";
import {
  MonitoringNotice,
  NOTICE_MODEL,
  adoptionAllowed,
  isNoticeModelMissing,
  noticeStatusFrom,
  noticeStatusFromError,
  shouldShowOnboarding,
} from "./onboarding";

const notice = (acknowledged: boolean): MonitoringNotice => ({
  version: "v1",
  title: "How DeployGuard uses your activity",
  body: ["para"],
  acknowledged,
  acknowledged_at: acknowledged ? "2026-09-22 08:00:00" : false,
});

describe("isNoticeModelMissing", () => {
  it("recognises a module that isn't installed (Odoo 19's NotFound, as classified in Rust)", () => {
    expect(isNoticeModelMissing({ kind: "module_not_installed", message: "This feature isn't installed on DogForce ERP yet." })).toBe(true);
  });

  it("still recognises an older server's KeyError naming the model", () => {
    expect(isNoticeModelMissing({ kind: "request_failed", message: `'${NOTICE_MODEL}'` })).toBe(true);
  });

  it("does not mistake a network failure or expired session for a missing module", () => {
    expect(isNoticeModelMissing({ kind: "network_unreachable", message: "Can't reach DogForce ERP." })).toBe(false);
    expect(isNoticeModelMissing({ kind: "session_expired", message: "Your session has expired." })).toBe(false);
    expect(isNoticeModelMissing({ kind: "request_failed", message: "Some other validation error" })).toBe(false);
    expect(isNoticeModelMissing(null)).toBe(false);
    expect(isNoticeModelMissing("boom")).toBe(false);
  });
});

describe("notice status", () => {
  it("maps acknowledgement state", () => {
    expect(noticeStatusFrom(notice(false)).kind).toBe("needs_ack");
    expect(noticeStatusFrom(notice(true)).kind).toBe("acknowledged");
  });

  it("treats a missing module as unavailable and anything else as a retryable error", () => {
    expect(noticeStatusFromError({ kind: "request_failed", message: `'${NOTICE_MODEL}'` }).kind).toBe("unavailable");
    const err = noticeStatusFromError({ kind: "network_unreachable", message: "Can't reach DogForce ERP." });
    expect(err).toEqual({ kind: "error", message: "Can't reach DogForce ERP." });
  });
});

describe("adoptionAllowed", () => {
  it("only once the person has acknowledged the notice", () => {
    expect(adoptionAllowed(noticeStatusFrom(notice(true)))).toBe(true);
    expect(adoptionAllowed(noticeStatusFrom(notice(false)))).toBe(false);
    expect(adoptionAllowed({ kind: "unavailable" })).toBe(false);
    expect(adoptionAllowed({ kind: "loading" })).toBe(false);
    expect(adoptionAllowed({ kind: "error", message: "x" })).toBe(false);
  });
});

describe("shouldShowOnboarding", () => {
  it("always shows it to someone who hasn't acknowledged, even if they've seen the welcome", () => {
    expect(shouldShowOnboarding(noticeStatusFrom(notice(false)), true)).toBe(true);
  });

  it("never shows it again once acknowledged", () => {
    expect(shouldShowOnboarding(noticeStatusFrom(notice(true)), false)).toBe(false);
  });

  it("shows the welcome once per device when the server has no notice to acknowledge", () => {
    expect(shouldShowOnboarding({ kind: "unavailable" }, false)).toBe(true);
    expect(shouldShowOnboarding({ kind: "unavailable" }, true)).toBe(false);
  });

  it("does not trap anyone behind a load error or while loading", () => {
    expect(shouldShowOnboarding({ kind: "error", message: "x" }, false)).toBe(false);
    expect(shouldShowOnboarding({ kind: "loading" }, false)).toBe(false);
  });
});
