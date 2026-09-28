// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { backend } from "../test/fakeTauri";
import { SessionProviderRoot } from "../session/SessionContext";
import { ViewModeProvider } from "./viewMode";
import { Home } from "./Home";
import { GuideDock } from "./GuideDock";
import { TeamToday } from "../shell/pages/TeamToday";
import type { TodayTask } from "../api/today";
import type { GuidanceSession } from "../api/guidance";

const employee = { uid: 7, login: "ops@dogforce.example", name: "Grace Mwale", db: "dogforce_prod" };

const register: TodayTask = {
  id: 11, name: "Register attendance · ABC Mall", state: "open", due_at: "2026-09-28 08:00:00", is_overdue: false,
  site: "ABC Mall", responsibility: "Register attendance",
  why_it_matters: "Payroll, client billing and AWOL follow-up are worked out from this register.",
  readiness: "ready", waiting_on: false, odoo_path: "/odoo/action-security_attendance.action_attendance_posting_console",
  guidance_flow_code: "attendance_register", checklist: false,
  training: { course_id: 1, course_name: "Daily Attendance", assignment_id: 5, done: true },
};

function session(overrides: Partial<GuidanceSession> = {}): GuidanceSession {
  return {
    id: 1, state: "active", practice: false,
    flow: { code: "attendance_register", name: "Register today's attendance", objective: "Everyone marked.", why: false },
    task: { id: 11, name: "Register attendance · ABC Mall", state: "in_progress" }, site: "ABC Mall", date: "2026-09-28",
    step: {
      id: 3, index: 3, title: "Mark every guard, then save", instruction: "Press Present, Absent or AWOL, then Save Changes.",
      why: "Each mark decides what a guard is paid.", has_help: true, success_message: false,
      deviation_hint: "Go back to the Posting Console for ABC Mall.", confirmable: false,
    },
    total: 3,
    steps: [{ title: "Open the Posting Console", done: true }, { title: "Open the sheet", done: true }, { title: "Mark every guard, then save", done: false }],
    off_track: false, highlight_nonce: 0,
    ...overrides,
  };
}

let calls: Array<{ model: string; method: string; args: unknown[]; kwargs: Record<string, unknown> }> = [];

function serve(handlers: Record<string, (args: unknown[], kwargs: Record<string, unknown>) => unknown>) {
  calls = [];
  backend.callKw = async (model, method, args, kwargs) => {
    calls.push({ model, method, args, kwargs });
    const h = handlers[method];
    if (!h) throw { kind: "request_failed", message: `unexpected ${method}` };
    return h(args, kwargs);
  };
}

function wrap(ui: React.ReactNode) {
  return render(<SessionProviderRoot><ViewModeProvider>{ui}</ViewModeProvider></SessionProviderRoot>);
}

beforeEach(() => {
  backend.reset();
  backend.session = employee;
});
afterEach(cleanup);

describe("Today", () => {
  const homeProps = {
    reloadSignal: 0, pageAvailable: () => true, canGuide: true, viewer: null,
    onGoTo: () => {}, onOpenTask: () => {}, onOpenCourse: () => {}, onReportProblem: () => {},
  };

  it("shows what to do, why, and offers the guide", async () => {
    serve({ get_my_today: () => ({ employee: { id: 1, name: "Grace" }, tasks: [register] }) });
    wrap(<Home {...homeProps} />);
    const card = (await screen.findByText("Register attendance")).closest("li")!;
    expect(within(card).getByText(/Payroll, client billing/)).toBeTruthy();
    expect(within(card).getByRole("button", { name: /Guide me/ })).toBeTruthy();
    expect(within(card).getByRole("button", { name: /I know how/ })).toBeTruthy();
  });

  it("'Guide me' starts a session for the real task, then docks the guide beside the ERP", async () => {
    serve({ get_my_today: () => ({ employee: { id: 1, name: "Grace" }, tasks: [register] }), start: () => session() });
    wrap(<Home {...homeProps} />);
    fireEvent.click(await screen.findByRole("button", { name: /Guide me/ }));
    await waitFor(() => expect(backend.viewMode).toBe("guide_dock"));
    const start = calls.find((c) => c.method === "start")!;
    expect(start.args).toEqual(["attendance_register"]);
    expect(start.kwargs).toEqual({ task_id: 11 });
    expect(backend.invoked.find((i) => i.cmd === "navigate_odoo")?.args).toEqual({ path: register.odoo_path });
  });

  it("puts learning first when the course isn't done", async () => {
    const learner = { ...register, training: { course_id: 1, course_name: "Daily Attendance", assignment_id: 5, done: false } };
    serve({ get_my_today: () => ({ employee: { id: 1, name: "Grace" }, tasks: [learner] }) });
    wrap(<Home {...homeProps} />);
    expect(await screen.findByRole("button", { name: /Learn this first/ })).toBeTruthy();
  });

  it("tells a downstream owner who they're waiting for, and offers no action yet", async () => {
    const waiting = { ...register, id: 12, responsibility: "Confirm attendance", readiness: "waiting" as const, waiting_on: "Register attendance (Grace)" };
    serve({ get_my_today: () => ({ employee: { id: 2, name: "Admin" }, tasks: [waiting] }) });
    wrap(<Home {...homeProps} />);
    expect(await screen.findByText("Waiting for Register attendance (Grace)")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Guide me/ })).toBeNull();
  });

  it("says plainly when there's nothing to do", async () => {
    serve({ get_my_today: () => ({ employee: { id: 1, name: "Grace" }, tasks: [] }) });
    wrap(<Home {...homeProps} />);
    expect(await screen.findByText("Nothing to do right now")).toBeTruthy();
  });
});

describe("Guide dock", () => {
  it("shows the server's current step, why, and progress", async () => {
    serve({ get_active: () => session() });
    wrap(<GuideDock onFinished={() => {}} />);
    expect(await screen.findByRole("heading", { name: "Mark every guard, then save" })).toBeTruthy();
    expect(screen.getByText(/Each mark decides/)).toBeTruthy();
    expect(screen.getByText("Step 3 of 3")).toBeTruthy();
  });

  it("explains how to get back when the employee is off track", async () => {
    serve({ get_active: () => session({ off_track: true }) });
    wrap(<GuideDock onFinished={() => {}} />);
    expect(await screen.findByText("You're on a different screen")).toBeTruthy();
    expect(screen.getByText("Go back to the Posting Console for ABC Mall.")).toBeTruthy();
  });

  it("labels AI answers as AI and grounded in the step", async () => {
    serve({
      get_active: () => session(),
      request_help: () => ({ help_html: "<p>Only use Mark All Present after checking.</p>", deviation_hint: false }),
      ask_ai: () => ({ ai: true, answer: "Mark them Present and add the time they left.", sources: ["Step: Mark"] }),
    });
    wrap(<GuideDock onFinished={() => {}} />);
    fireEvent.click(await screen.findByRole("button", { name: /I'm stuck/ }));
    expect(await screen.findByText("Only use Mark All Present after checking.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/Still stuck/), { target: { value: "A guard left early?" } });
    fireEvent.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(/AI explanation, based on this step's approved instructions/)).toBeTruthy();
  });

  it("confirms completion when the server says the task is done", async () => {
    let active: GuidanceSession | false = session();
    serve({ get_active: () => active });
    wrap(<GuideDock onFinished={() => {}} />);
    await screen.findByRole("heading", { name: "Mark every guard, then save" });
    active = false;
    await act(async () => { await new Promise((r) => setTimeout(r, 1600)); });
    expect(await screen.findByRole("heading", { name: "Done" })).toBeTruthy();
  });
});

describe("Team Today", () => {
  it("shows where each site is stuck, with the real task behind each cell", async () => {
    serve({
      get_team_today: () => ({
        date: "2026-09-28",
        steps: [{ id: 1, name: "Register attendance", owner: "Grace" }, { id: 2, name: "Confirm attendance", owner: "Admin" }],
        pipeline: [{ site: "ABC Mall", site_id: 3, cells: {
          1: { task_id: 11, state: "submitted", is_overdue: false, readiness: "ready", employee: "Grace" },
          2: { task_id: 12, state: "open", is_overdue: true, readiness: "ready", employee: "Admin" },
        } }],
        people: [{ employee: "Admin", employee_id: 2, expected: [12], done: [], overdue: [12], could_not_complete: [], waiting: [] }],
      }),
    });
    wrap(<TeamToday />);
    expect(await screen.findByRole("button", { name: /ABC Mall, Confirm attendance: Overdue/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /ABC Mall, Register attendance: Done/ })).toBeTruthy();
  });
});
