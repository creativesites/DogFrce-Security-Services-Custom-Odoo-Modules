import { describe, expect, it } from "vitest";
import {
  availableActions,
  byDueDateAscending,
  dueBadgeTone,
  isActiveState,
  isOverdue,
  parseOdooDatetime,
} from "./myWork.logic";

describe("availableActions", () => {
  it("offers start/could-not-complete/cancel for an open task", () => {
    expect(availableActions("open")).toEqual(["start", "could_not_complete", "cancel"]);
  });

  it("offers submit/could-not-complete for an in-progress task", () => {
    expect(availableActions("in_progress")).toEqual(["submit", "could_not_complete"]);
  });

  it("treats a rejected task the same as open (assignee can pick it back up)", () => {
    expect(availableActions("rejected")).toEqual(["start", "could_not_complete", "cancel"]);
  });

  it("offers nothing for a submitted task (awaiting supervisor review)", () => {
    expect(availableActions("submitted")).toEqual([]);
  });

  it("offers nothing for a verified task (finished)", () => {
    expect(availableActions("verified")).toEqual([]);
  });

  it("offers nothing for a could-not-complete task", () => {
    expect(availableActions("could_not_complete")).toEqual([]);
  });

  it("offers nothing for a cancelled task", () => {
    expect(availableActions("cancelled")).toEqual([]);
  });

  it("never includes verify/reject — those are supervisor-side actions on the same model", () => {
    for (const state of ["open", "in_progress", "submitted", "verified", "could_not_complete", "rejected", "cancelled"] as const) {
      const actions = availableActions(state);
      expect(actions).not.toContain("verify");
      expect(actions).not.toContain("reject");
    }
  });
});

describe("parseOdooDatetime", () => {
  it("parses a naive Odoo datetime string as UTC, not local time", () => {
    const parsed = parseOdooDatetime("2026-09-16 10:00:00");
    expect(parsed?.toISOString()).toBe("2026-09-16T10:00:00.000Z");
  });

  it("parses a T-separated ISO-ish variant", () => {
    const parsed = parseOdooDatetime("2026-09-16T10:00:00");
    expect(parsed?.toISOString()).toBe("2026-09-16T10:00:00.000Z");
  });

  it("returns null for an unparseable string", () => {
    expect(parseOdooDatetime("not-a-date")).toBeNull();
  });
});

describe("isOverdue", () => {
  const now = new Date("2026-09-16T12:00:00.000Z");

  it("is false when there is no due date", () => {
    expect(isOverdue(false, "open", now)).toBe(false);
  });

  it("is true when due_at is in the past and the task is still open", () => {
    expect(isOverdue("2026-09-16 10:00:00", "open", now)).toBe(true);
  });

  it("is false when due_at is in the future", () => {
    expect(isOverdue("2026-09-16 14:00:00", "open", now)).toBe(false);
  });

  it("is false for a verified task even if due_at is in the past", () => {
    expect(isOverdue("2026-09-16 10:00:00", "verified", now)).toBe(false);
  });

  it("is false for a cancelled task even if due_at is in the past", () => {
    expect(isOverdue("2026-09-16 10:00:00", "cancelled", now)).toBe(false);
  });

  it("is true for a submitted task past due (still pending review)", () => {
    expect(isOverdue("2026-09-16 10:00:00", "submitted", now)).toBe(true);
  });
});

describe("dueBadgeTone", () => {
  const now = new Date("2026-09-16T12:00:00.000Z");

  it("is neutral with no due date", () => {
    expect(dueBadgeTone(false, "open", now)).toBe("neutral");
  });

  it("is danger when overdue", () => {
    expect(dueBadgeTone("2026-09-16 10:00:00", "open", now)).toBe("danger");
  });

  it("is warning when due within 24 hours", () => {
    expect(dueBadgeTone("2026-09-17 08:00:00", "open", now)).toBe("warning");
  });

  it("is neutral when due more than 24 hours out", () => {
    expect(dueBadgeTone("2026-09-20 08:00:00", "open", now)).toBe("neutral");
  });

  it("is neutral for a verified task due soon (already finished)", () => {
    expect(dueBadgeTone("2026-09-17 08:00:00", "verified", now)).toBe("neutral");
  });
});

describe("byDueDateAscending", () => {
  it("sorts soonest due date first", () => {
    const tasks = [
      { due_at: "2026-09-20 00:00:00" as string | false },
      { due_at: "2026-09-16 00:00:00" as string | false },
      { due_at: "2026-09-18 00:00:00" as string | false },
    ];
    const sorted = [...tasks].sort(byDueDateAscending);
    expect(sorted.map((t) => t.due_at)).toEqual([
      "2026-09-16 00:00:00",
      "2026-09-18 00:00:00",
      "2026-09-20 00:00:00",
    ]);
  });

  it("puts tasks with no due date last", () => {
    const tasks = [
      { due_at: false as string | false },
      { due_at: "2026-09-16 00:00:00" as string | false },
    ];
    const sorted = [...tasks].sort(byDueDateAscending);
    expect(sorted.map((t) => t.due_at)).toEqual(["2026-09-16 00:00:00", false]);
  });

  it("treats two undated tasks as equal", () => {
    const tasks = [{ due_at: false as string | false }, { due_at: false as string | false }];
    expect(byDueDateAscending(tasks[0], tasks[1])).toBe(0);
  });
});

describe("isActiveState", () => {
  it("open, in_progress, rejected, and submitted are active", () => {
    expect(isActiveState("open")).toBe(true);
    expect(isActiveState("in_progress")).toBe(true);
    expect(isActiveState("rejected")).toBe(true);
    expect(isActiveState("submitted")).toBe(true);
  });

  it("verified, could_not_complete, and cancelled are not active", () => {
    expect(isActiveState("verified")).toBe(false);
    expect(isActiveState("could_not_complete")).toBe(false);
    expect(isActiveState("cancelled")).toBe(false);
  });
});
