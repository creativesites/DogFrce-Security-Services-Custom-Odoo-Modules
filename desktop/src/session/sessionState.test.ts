import { describe, expect, it } from "vitest";
import { nextSessionState, sameSession } from "./sessionState";

const owner = { uid: 2, login: "owner@dogforce", name: "Owner", db: "dogforce_prod" };

describe("sameSession", () => {
  it("treats Rust's repeated sign-in announcement for the same person as no change", () => {
    expect(sameSession(owner, { ...owner })).toBe(true);
  });

  it("notices a different person, database or display name", () => {
    expect(sameSession(owner, { ...owner, uid: 3 })).toBe(false);
    expect(sameSession(owner, { ...owner, db: "odoo-security" })).toBe(false);
    expect(sameSession(owner, { ...owner, name: "Renamed" })).toBe(false);
  });

  it("handles signed-out states", () => {
    expect(sameSession(null, null)).toBe(true);
    expect(sameSession(owner, null)).toBe(false);
  });
});

describe("nextSessionState", () => {
  const signedIn = { status: "signed_in" as const, session: owner };

  it("keeps the same state object when Rust re-announces the same person", () => {
    expect(nextSessionState(signedIn, { status: "signed_in", session: { ...owner }, auto_reveal: false })).toBe(signedIn);
  });

  it("moves to expired when Odoo rejects the session mid-use", () => {
    expect(nextSessionState(signedIn, { status: "expired" })).toEqual({ status: "expired", session: null });
  });

  it("does not replace the expiry explanation with a plain sign-out", () => {
    const expired = { status: "expired" as const, session: null };
    expect(nextSessionState(expired, { status: "signed_out" })).toBe(expired);
  });

  it("clears expiry once the employee signs in again", () => {
    const expired = { status: "expired" as const, session: null };
    expect(nextSessionState(expired, { status: "signed_in", session: owner, auto_reveal: true })).toEqual(signedIn);
  });

  it("signs out from checking or signed-in", () => {
    expect(nextSessionState(signedIn, { status: "signed_out" })).toEqual({ status: "signed_out", session: null });
    expect(nextSessionState({ status: "checking", session: null }, { status: "signed_out" }).status).toBe("signed_out");
  });
});
