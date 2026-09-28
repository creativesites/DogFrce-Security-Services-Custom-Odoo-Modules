/* eslint-disable @typescript-eslint/no-explicit-any */
// A fake DogForce ERP for the design preview. Realistic, internally consistent
// data for one morning: three sites rostered, the attendance pipeline partly
// done. Test names only.

const params = new URLSearchParams(window.location.search);
const who = params.get("as") || "ops";
const first = params.get("first") === "1";
const guideVariant = params.get("guide");

const pad = (n: number) => String(n).padStart(2, "0");
const today = new Date();
const d = (offsetDays = 0) => {
  const x = new Date(today);
  x.setDate(x.getDate() + offsetDays);
  return `${x.getFullYear()}-${pad(x.getMonth() + 1)}-${pad(x.getDate())}`;
};
/** Local hh:mm today as an Odoo UTC datetime string. */
const at = (h: number, m = 0, offsetDays = 0) => {
  const x = new Date(today);
  x.setDate(x.getDate() + offsetDays);
  x.setHours(h, m, 0, 0);
  return `${x.getUTCFullYear()}-${pad(x.getUTCMonth() + 1)}-${pad(x.getUTCDate())} ${pad(x.getUTCHours())}:${pad(x.getUTCMinutes())}:00`;
};

const WHY = {
  register: "Payroll, client billing and AWOL follow-up are worked out from this register. If it's missing, guards may be paid wrongly and clients billed wrongly.",
  confirm: "A second person checking the register catches mistakes before they reach payroll.",
  verify: "Locking is what payroll reads from. It's the last check before people are paid.",
};
const PATH = "/odoo/action-security_attendance.action_attendance_posting_console";
const course = { course_id: 2, course_name: "Daily Attendance: Register, Confirm, Verify", assignment_id: 21 };

const card = (o: any) => ({
  checklist: false, why_it_matters: false, readiness: "ready", waiting_on: false, odoo_path: PATH,
  guidance_flow_code: false, is_overdue: false, training: false, state: "open", ...o,
});

const TODAY: Record<string, any[]> = {
  ops: [
    card({ id: 11, name: "Register attendance · Manda Hill Mall", responsibility: "Register attendance", site: "Manda Hill Mall",
      due_at: at(10), is_overdue: true, why_it_matters: WHY.register, guidance_flow_code: "attendance_register",
      training: { ...course, done: true } }),
    card({ id: 12, name: "Register attendance · ABC Shopping Centre", responsibility: "Register attendance", site: "ABC Shopping Centre",
      due_at: at(10), state: "in_progress", why_it_matters: WHY.register, guidance_flow_code: "attendance_register",
      training: { ...course, done: true } }),
    card({ id: 13, name: "Register attendance · Kabulonga Depot", responsibility: "Register attendance", site: "Kabulonga Depot",
      due_at: at(10), state: "submitted", why_it_matters: WHY.register, guidance_flow_code: "attendance_register",
      training: { ...course, done: true } }),
    card({ id: 14, name: "Weekly site visit · ABC Shopping Centre", responsibility: false, site: "ABC Shopping Centre",
      due_at: at(16, 30), checklist: true, odoo_path: false }),
  ],
  admin: [
    card({ id: 21, name: "Confirm attendance · Kabulonga Depot", responsibility: "Confirm attendance", site: "Kabulonga Depot",
      due_at: at(12), why_it_matters: WHY.confirm, guidance_flow_code: "attendance_confirm",
      training: { ...course, assignment_id: 22, done: false } }),
    card({ id: 22, name: "Confirm attendance · ABC Shopping Centre", responsibility: "Confirm attendance", site: "ABC Shopping Centre",
      due_at: at(12), readiness: "waiting", waiting_on: "Register attendance (Grace Mwale)", why_it_matters: WHY.confirm,
      guidance_flow_code: "attendance_confirm", training: { ...course, assignment_id: 22, done: false } }),
    card({ id: 23, name: "Confirm attendance · Manda Hill Mall", responsibility: "Confirm attendance", site: "Manda Hill Mall",
      due_at: at(12), readiness: "waiting", waiting_on: "Register attendance (Grace Mwale)", why_it_matters: WHY.confirm,
      guidance_flow_code: "attendance_confirm", training: { ...course, assignment_id: 22, done: false } }),
  ],
  hr: [
    card({ id: 31, name: "Verify attendance · Kabulonga Depot", responsibility: "Verify attendance", site: "Kabulonga Depot",
      due_at: at(15), readiness: "waiting", waiting_on: "Confirm attendance (Joseph Phiri)", why_it_matters: WHY.verify,
      guidance_flow_code: "attendance_verify", training: { ...course, done: true } }),
  ],
  gm: [],
  owner: [],
};

const STEPS = [
  { id: 1, name: "Register attendance", owner: "Grace Mwale" },
  { id: 2, name: "Confirm attendance", owner: "Joseph Phiri" },
  { id: 3, name: "Verify attendance", owner: "Ruth Banda" },
];
const cell = (task_id: number, state: string, employee: string, extra: any = {}) =>
  ({ task_id, state, employee, is_overdue: false, readiness: "ready", ...extra });

const TEAM = {
  date: d(),
  steps: STEPS,
  pipeline: [
    { site: "ABC Shopping Centre", site_id: 1, cells: {
      1: cell(12, "in_progress", "Grace Mwale"), 2: cell(22, "open", "Joseph Phiri", { readiness: "waiting" }),
      3: cell(32, "open", "Ruth Banda", { readiness: "waiting" }) } },
    { site: "Kabulonga Depot", site_id: 2, cells: {
      1: cell(13, "verified", "Grace Mwale"), 2: cell(21, "open", "Joseph Phiri"),
      3: cell(31, "open", "Ruth Banda", { readiness: "waiting" }) } },
    { site: "Manda Hill Mall", site_id: 3, cells: {
      1: cell(11, "open", "Grace Mwale", { is_overdue: true }), 2: cell(23, "open", "Joseph Phiri", { readiness: "waiting" }),
      3: cell(33, "open", "Ruth Banda", { readiness: "waiting" }) } },
  ],
  people: [
    { employee: "Grace Mwale", employee_id: 1, expected: [11, 12, 13, 14], done: [13], overdue: [11], could_not_complete: [], waiting: [] },
    { employee: "Joseph Phiri", employee_id: 2, expected: [21, 22, 23], done: [], overdue: [], could_not_complete: [], waiting: [22, 23] },
    { employee: "Ruth Banda", employee_id: 3, expected: [31, 32, 33], done: [], overdue: [], could_not_complete: [], waiting: [31, 32, 33] },
  ],
};

const OWNER = {
  period_start: d(), period_end: d(), generated_at: at(9, 40),
  tiles: [
    { key: "tasks_today", label: "Work done today", value: 4, total: 10, detail: "4 of 10 tasks due today are done.", tone: "neutral",
      trend: { direction: "up", current_pct: 86, previous_pct: 71, explanation: "Last 7 days: 60 of 70 tasks done (86%). The 7 days before: 50 of 70 (71%)." },
      drill: { model: "security.work.task", domain: [], fields: ["name", "employee_id", "site_id", "due_at", "state"], title: "Work due today" } },
    { key: "overdue", label: "Overdue work", value: 1, total: null, detail: "Tasks past their due time and not done.", tone: "danger", trend: null,
      drill: { model: "security.work.task", domain: [], fields: ["name", "employee_id", "site_id", "due_at", "state"], title: "Overdue work" } },
    { key: "could_not_complete", label: "Couldn't be done (7 days)", value: 2, total: null, detail: "Each one has the employee's reason attached.", tone: "warning", trend: null,
      drill: { model: "security.work.task", domain: [], fields: ["name", "employee_id", "cnc_reason", "cnc_note"], title: "Couldn't be done" } },
    { key: "exceptions", label: "Open exceptions", value: 3, total: null, detail: "1 critical.", tone: "danger", trend: null,
      drill: { model: "security.exception.instance", domain: [], fields: ["title", "tier", "state", "site_id", "first_seen_at"], title: "Open exceptions" } },
    { key: "training_overdue", label: "Training overdue", value: 1, total: null, detail: "Assigned courses past their due date.", tone: "warning", trend: null,
      drill: { model: "security.training.assignment", domain: [], fields: ["employee_id", "course_id", "due_date", "state"], title: "Training overdue" } },
    { key: "support", label: "Problems reported", value: 0, total: null, detail: "No open problem reports.", tone: "success", trend: null,
      drill: { model: "security.support.request", domain: [], fields: ["name", "subject", "user_id", "priority", "state"], title: "Problems reported" } },
  ],
};

const TASK_ROWS = [
  { id: 11, name: "Register attendance · Manda Hill Mall", employee_id: [1, "Grace Mwale"], site_id: [3, "Manda Hill Mall"], due_at: at(10), state: "open", cnc_reason: false, cnc_note: false },
  { id: 12, name: "Register attendance · ABC Shopping Centre", employee_id: [1, "Grace Mwale"], site_id: [1, "ABC Shopping Centre"], due_at: at(10), state: "in_progress", cnc_reason: false, cnc_note: false },
  { id: 13, name: "Register attendance · Kabulonga Depot", employee_id: [1, "Grace Mwale"], site_id: [2, "Kabulonga Depot"], due_at: at(10), state: "verified", cnc_reason: false, cnc_note: false },
  { id: 14, name: "Weekly site visit · ABC Shopping Centre", employee_id: [1, "Grace Mwale"], site_id: [1, "ABC Shopping Centre"], due_at: at(16, 30), state: "open", cnc_reason: false, cnc_note: false, checklist_template_id: [4, "Site visit"], description: false, note: false },
];

function guidance() {
  if (guideVariant === "done") return false;
  return {
    id: 5, state: "active", practice: false,
    flow: { code: "attendance_register", name: "Register today's attendance", objective: "Every guard rostered at the site today is marked and saved.", why: WHY.register },
    task: { id: 12, name: "Register attendance · ABC Shopping Centre", state: "in_progress" },
    site: "ABC Shopping Centre", date: d(),
    step: {
      id: 3, index: 3, title: "Mark every guard, then save",
      instruction: "For each guard press Present, Absent or AWOL. When nobody shows “Not Marked”, press Save Changes.",
      why: "Each mark decides what a guard is paid for today, and an AWOL mark starts the follow-up. Mark what actually happened.",
      has_help: true, success_message: "Attendance registered. Admin can now confirm it.",
      deviation_hint: "Go back to the Posting Console for ABC Shopping Centre.", confirmable: false,
    },
    total: 3,
    steps: [
      { title: "Open the Posting Console", done: true },
      { title: "Open ABC Shopping Centre's sheet", done: true },
      { title: "Mark every guard, then save", done: false },
    ],
    off_track: guideVariant === "off_track", highlight_nonce: 0,
  };
}

const ASSIGNMENTS = [
  { id: 21, employee_id: [1, "Grace Mwale"], course_id: [2, course.course_name], course_version_id: [5, "v1"], due_date: d(4), state: "in_progress", completed_at: false },
  { id: 23, employee_id: [1, "Grace Mwale"], course_id: [1, "Getting Live: Client Setup & Rostering"], course_version_id: [1, "v1"], due_date: d(-2), state: "completed", completed_at: at(9, 0, -2) },
];

export async function fakeOdoo(model: string, method: string, args: any[], _kwargs: Record<string, unknown>): Promise<unknown> {
  await new Promise((r) => setTimeout(r, 120));
  if (method === "fields_get") return {};
  if (method === "get_viewer_context") {
    return { is_supervisor: ["gm", "owner"].includes(who), is_manager: ["gm", "owner"].includes(who), is_owner: who === "owner" };
  }
  if (model === "security.deployguard.policy.acknowledgement") {
    return {
      version: "2026-09-draft-2", title: "What DeployGuard records",
      body: [
        "DeployGuard records the work you're expected to do and whether it was done: tasks, checklists, training and attendance steps.",
        "It compares that with the work expected of your role. It does not record your screen, keystrokes or mouse, or how long you spend in the app.",
        "Your manager sees what was expected and what was done, with the records behind it.",
      ],
      acknowledged: !first || method === "acknowledge", acknowledged_at: false,
    };
  }
  switch (method) {
    case "get_my_today":
      return { employee: { id: 1, name: "x" }, tasks: TODAY[who] ?? [] };
    case "get_team_today":
      return TEAM;
    case "get_owner_overview":
      return OWNER;
    case "get_active":
    case "report_ui_state":
    case "show_me":
      return guidance();
    case "request_help":
      return { help_html: "<ul><li><strong>Present</strong>: the guard came to the post.</li><li><strong>Absent</strong>: they told you they couldn't come.</li><li><strong>AWOL</strong>: they didn't come and didn't tell anyone.</li></ul><p>Only use <em>Mark All Present</em> after you've checked that every guard really came.</p>", deviation_hint: false };
    case "ask_ai":
      return { ai: true, answer: "Mark them Present, and put the time they actually left in the check-out time. Payroll then pays only the hours they worked.", sources: ["Step: Mark every guard"] };
    case "get_contextual_articles":
    case "search_articles":
      return [
        { id: 1, title: "Registering daily attendance", summary: "How to use the Posting Console, step by step.", category_id: [1, "Attendance"] },
        { id: 2, title: "What to do when the roster is wrong", summary: "Guards missing from the sheet, or the wrong site.", category_id: [1, "Attendance"] },
      ];
    case "search_count":
      return 1;
  }
  if (method === "search_read" || method === "read") {
    switch (model) {
      case "hr.employee": return [{ id: 1 }];
      case "security.work.task": return TASK_ROWS;
      case "security.roster.signoff": return [];
      case "security.work.checklist.item.def":
        return [
          { id: 1, template_id: [4, "Site visit"], sequence: 10, label: "Guards at post and in uniform", item_type: "boolean", required: true, help_text: false },
          { id: 2, template_id: [4, "Site visit"], sequence: 20, label: "Occurrence book up to date", item_type: "boolean", required: true, help_text: false },
          { id: 3, template_id: [4, "Site visit"], sequence: 30, label: "Anything the client raised", item_type: "text", required: false, help_text: false },
        ];
      case "security.work.checklist.response": return [];
      case "security.training.assignment": return ASSIGNMENTS;
      case "security.training.lesson.progress": return [];
      case "security.training.attempt": return [];
      case "security.training.section": return [{ id: 1, sequence: 10, name: "Why daily attendance matters" }, { id: 2, sequence: 20, name: "Register (Operations Supervisor)" }];
      case "security.training.lesson":
        return [
          { id: 1, section_id: [1, "Why"], sequence: 10, name: "Why does today's attendance have to be done today?", content_type: "text", body: "<p>At the end of the month, payroll pays each guard for the shifts the register says they worked.</p>", video_url: false, deep_link_path: false, guidance_flow_code: false },
          { id: 2, section_id: [2, "Register"], sequence: 10, name: "How do I register a site's attendance?", content_type: "text", body: "<ol><li>Open Workforce → Posting Console.</li><li>Choose the site and date.</li><li>Mark each guard, then Save Changes.</li></ol>", video_url: false, deep_link_path: PATH, guidance_flow_code: false },
          { id: 3, section_id: [2, "Register"], sequence: 30, name: "Do it: register today's attendance with DeployGuard beside you", content_type: "text", body: "<p>Press <strong>Practice it now</strong>.</p>", video_url: false, deep_link_path: PATH, guidance_flow_code: "attendance_register" },
        ];
      case "security.training.assessment": return [{ id: 1, name: "Daily attendance check", pass_mark_pct: 80, max_attempts: 3 }];
      case "security.training.question": return [];
      case "security.training.question.option": return [];
      case "security.exception.instance":
        return [
          { id: 1, notification_id: [1, "x"], rule_id: [1, "Work overdue"], tier: "attention", title: "Overdue: Register attendance · Manda Hill Mall",
            body: "Register attendance · Manda Hill Mall was due 10:00 and isn't done. Owner: Grace Mwale.\nWhy it matters: payroll and billing are worked out from this register.\nNext: ask Grace Mwale whether something is blocking them.",
            site_id: [3, "Manda Hill Mall"], notification_type: "task_overdue", severity: "warning", related_model: "security.work.task", related_id: 11,
            state: "open", first_seen_at: at(10, 5), last_confirmed_at: at(10, 5), escalation_level: 0, escalated_at: false,
            acknowledged_by_id: false, acknowledged_at: false, resolved_by_id: false, resolved_at: false, resolution_code: false, resolution_note: false },
          { id: 2, notification_id: [2, "x"], rule_id: [2, "Roster gap"], tier: "critical", title: "Unassigned slot: Kabulonga Depot night shift",
            body: "Post: North Gate. No guard assigned for tonight's 18:00–06:00 shift.", site_id: [2, "Kabulonga Depot"], notification_type: "roster_gap",
            severity: "critical", related_model: false, related_id: 0, state: "open", first_seen_at: at(8, 15), last_confirmed_at: at(9, 30),
            escalation_level: 1, escalated_at: at(9, 15), acknowledged_by_id: false, acknowledged_at: false, resolved_by_id: false, resolved_at: false,
            resolution_code: false, resolution_note: false },
        ];
      case "security.adoption.snapshot": return [];
      case "security.adoption.expected.work.item": return [];
      case "security.adoption.checkin": return [];
      case "security.help.article": return [{ body: "<p>Open Workforce → Posting Console…</p>" }];
    }
    return [];
  }
  return true;
}
