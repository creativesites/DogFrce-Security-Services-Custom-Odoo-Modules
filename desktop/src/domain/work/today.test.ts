import { describe, expect, it } from "vitest";
import type { TodayTask } from "../../api/today";
import { cardStatus, nextAction, progress } from "./today";

const base: TodayTask = {
  id: 1, name: "Register attendance · ABC Mall", state: "open", due_at: "2026-09-28 08:00:00", is_overdue: false,
  site: "ABC Mall", responsibility: "Register attendance", why_it_matters: "Payroll", readiness: "ready",
  waiting_on: false, odoo_path: "/odoo/x", guidance_flow_code: "attendance_register", checklist: false, training: false,
};

describe("Today card", () => {
  it("uses the server's overdue flag, not the clock", () => {
    expect(cardStatus({ ...base, is_overdue: true }).tone).toBe("danger");
    expect(cardStatus({ ...base, due_at: "2000-01-01 00:00:00", is_overdue: false }).tone).toBe("info");
  });

  it("says who it's waiting for", () => {
    const s = cardStatus({ ...base, readiness: "waiting", waiting_on: "Register attendance (Grace)" });
    expect(s.label).toBe("Waiting for Register attendance (Grace)");
  });

  it("offers learning first, then guidance, then the ERP", () => {
    const course = { course_id: 1, course_name: "Daily Attendance", assignment_id: 3, done: false };
    expect(nextAction({ ...base, training: course }, true)).toBe("learn");
    expect(nextAction({ ...base, training: { ...course, done: true } }, true)).toBe("guide");
    expect(nextAction(base, false)).toBe("open");
    expect(nextAction({ ...base, readiness: "waiting" }, true)).toBe("wait");
    expect(nextAction({ ...base, state: "submitted" }, true)).toBe("none");
  });

  it("counts progress over live tasks only", () => {
    expect(progress([base, { ...base, id: 2, state: "verified" }, { ...base, id: 3, state: "cancelled" }])).toEqual({ done: 1, total: 2 });
  });
});
