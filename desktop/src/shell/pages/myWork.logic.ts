/**
 * Pure logic for the My Work page — kept separate from MyWork.tsx so it can
 * be unit-tested without mounting React or touching Tauri IPC. Nothing here
 * makes a network call.
 */

export type WorkTaskState =
  | "open"
  | "in_progress"
  | "submitted"
  | "verified"
  | "could_not_complete"
  | "rejected"
  | "cancelled";

export type WorkAction = "start" | "submit" | "could_not_complete" | "cancel";

/** Human labels for each state, used in list/detail badges. */
export const STATE_LABELS: Record<WorkTaskState, string> = {
  open: "Open",
  in_progress: "In progress",
  submitted: "Submitted",
  verified: "Verified",
  could_not_complete: "Could not complete",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

/**
 * Which of the four employee-facing actions (Start / Submit / Could Not
 * Complete / Cancel) are valid from a given state. Verify/Reject are
 * supervisor actions on the *same* model — deliberately not surfaced here,
 * since My Work is the assignee's own view of their task, not a review
 * queue. `rejected` is treated like `open`: the assignee can pick the task
 * back up rather than it being a dead end.
 */
export function availableActions(state: WorkTaskState): WorkAction[] {
  switch (state) {
    case "open":
    case "rejected":
      return ["start", "could_not_complete", "cancel"];
    case "in_progress":
      return ["submit", "could_not_complete"];
    case "submitted":
    case "verified":
    case "could_not_complete":
    case "cancelled":
      return [];
    default:
      return [];
  }
}

/** True once a task's due date has passed and it isn't in a finished state. */
export function isOverdue(dueAt: string | false | null | undefined, state: WorkTaskState, now: Date = new Date()): boolean {
  if (!dueAt) return false;
  if (state === "verified" || state === "cancelled") return false;
  const due = parseOdooDatetime(dueAt);
  if (!due) return false;
  return due.getTime() < now.getTime();
}

/** Badge tone for the due-date pill: an existing --ds-danger/--ds-warning
 * pairing (design tokens), never a raw color. */
export function dueBadgeTone(
  dueAt: string | false | null | undefined,
  state: WorkTaskState,
  now: Date = new Date(),
): "danger" | "warning" | "neutral" {
  if (!dueAt) return "neutral";
  if (isOverdue(dueAt, state, now)) return "danger";
  const due = parseOdooDatetime(dueAt);
  if (!due) return "neutral";
  const hoursUntilDue = (due.getTime() - now.getTime()) / (1000 * 60 * 60);
  if (state !== "verified" && state !== "cancelled" && hoursUntilDue <= 24) return "warning";
  return "neutral";
}

/**
 * Odoo returns naive UTC datetimes as "YYYY-MM-DD HH:MM:SS" (no timezone
 * suffix) over JSON-RPC. `new Date("2026-09-16 10:00:00")` is parsed as
 * *local* time by JS engines, silently shifting it by the viewer's UTC
 * offset — wrong for anything that compares against "now". This parses it
 * explicitly as UTC instead.
 */
export function parseOdooDatetime(value: string): Date | null {
  const match = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})/.exec(value);
  if (!match) return null;
  const [, y, mo, d, h, mi, s] = match;
  const time = Date.UTC(Number(y), Number(mo) - 1, Number(d), Number(h), Number(mi), Number(s));
  return Number.isNaN(time) ? null : new Date(time);
}

/** Sort key: soonest due date first, tasks with no due date last. */
export function byDueDateAscending<T extends { due_at: string | false }>(a: T, b: T): number {
  const da = a.due_at ? parseOdooDatetime(a.due_at)?.getTime() ?? null : null;
  const db = b.due_at ? parseOdooDatetime(b.due_at)?.getTime() ?? null : null;
  if (da === null && db === null) return 0;
  if (da === null) return 1;
  if (db === null) return -1;
  return da - db;
}

/** True while the task is still "live" work for the assignee — used to
 * decide the default list filter (hide fully-finished tasks unless asked). */
export function isActiveState(state: WorkTaskState): boolean {
  return state === "open" || state === "in_progress" || state === "rejected" || state === "submitted";
}

export type RosterRole = "front_desk" | "general_manager" | "hr" | "finance" | "director";

export const ROSTER_ROLE_LABELS: Record<RosterRole, string> = {
  front_desk: "Front Desk (Posting & Attendance)",
  general_manager: "General Manager (Validation)",
  hr: "HR (Hours & Equity Audit)",
  finance: "Finance (Payment Release)",
  director: "Director (Executive Oversight)",
};

export function formatRosterRole(role: string): string {
  return ROSTER_ROLE_LABELS[role as RosterRole] ?? role;
}

