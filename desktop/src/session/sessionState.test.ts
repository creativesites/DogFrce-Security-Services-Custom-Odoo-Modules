import { describe, expect, it } from "vitest";
import { sameSession } from "./SessionContext";

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
