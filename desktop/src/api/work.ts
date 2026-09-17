import { callKw } from "./odoo";
import type { WorkAction, WorkTaskState } from "../shell/pages/myWork.logic";

/**
 * Talks to the `security_work` Odoo module (built concurrently by a
 * separate agent — see the My Work build brief). Standard `call_kw`
 * against its models, no bespoke controller: any internal user with normal
 * read/write access to these models can use My Work as-is.
 *
 * Every function here can fail simply because the module isn't installed
 * yet in whatever environment this runs against (unknown model/method) —
 * callers must treat that as an ordinary error state, not a crash.
 */

export interface WorkTask {
  id: number;
  name: string;
  description: string | false;
  due_at: string | false;
  state: WorkTaskState;
  site_id: [number, string] | false;
  checklist_template_id: [number, string] | false;
  note: string | false;
  cnc_reason: string | false;
}

export interface ChecklistItemDef {
  id: number;
  sequence: number;
  label: string;
  item_type: "boolean" | "text" | "number" | "photo";
  required: boolean;
}

export interface ChecklistResponse {
  id: number;
  task_id: [number, string];
  item_def_id: [number, string];
  value_bool: boolean;
  value_text: string | false;
  value_number: number | false;
  note: string | false;
}

const TASK_FIELDS = [
  "name",
  "description",
  "due_at",
  "state",
  "site_id",
  "checklist_template_id",
  "note",
  "cnc_reason",
];

/** Resolves the `hr.employee` record for the given Odoo user id, or `null`
 * if this user has no linked employee (e.g. a pure back-office login). */
export async function resolveEmployeeId(uid: number): Promise<number | null> {
  const rows = await callKw<Array<{ id: number }>>(
    "hr.employee",
    "search_read",
    [[["user_id", "=", uid]], ["id"]],
    { limit: 1 },
  );
  return rows[0]?.id ?? null;
}

/** All tasks assigned to `employeeId`, soonest due date first. */
export async function fetchMyTasks(employeeId: number): Promise<WorkTask[]> {
  return callKw<WorkTask[]>(
    "security.work.task",
    "search_read",
    [[["employee_id", "=", employeeId]], TASK_FIELDS],
    { order: "due_at asc" },
  );
}

export async function fetchTask(taskId: number): Promise<WorkTask> {
  const rows = await callKw<WorkTask[]>("security.work.task", "read", [[taskId], TASK_FIELDS]);
  if (!rows[0]) throw new Error("Task not found.");
  return rows[0];
}

/** The template's checklist item definitions, in display order. */
export async function fetchChecklistItems(templateId: number): Promise<ChecklistItemDef[]> {
  return callKw<ChecklistItemDef[]>(
    "security.work.checklist.item.def",
    "search_read",
    [[["template_id", "=", templateId]], ["sequence", "label", "item_type", "required"]],
    { order: "sequence asc" },
  );
}

/** Any responses already recorded for this task (e.g. re-opening a
 * previously started task). */
export async function fetchChecklistResponses(taskId: number): Promise<ChecklistResponse[]> {
  return callKw<ChecklistResponse[]>(
    "security.work.checklist.response",
    "search_read",
    [[["task_id", "=", taskId]], ["task_id", "item_def_id", "value_bool", "value_text", "value_number", "note"]],
  );
}

/** Odoo's `<selection>` values for a field aren't guaranteed stable/known
 * ahead of time (`cnc_reason` here) — read them from the model itself via
 * `fields_get` rather than hardcoding a list that could drift from the
 * backend module. Falls back to an empty list (a free-text-less reason
 * picker) if the field or model isn't there yet. */
export async function fetchCncReasonOptions(): Promise<Array<{ value: string; label: string }>> {
  try {
    const fields = await callKw<Record<string, { selection?: [string, string][] }>>(
      "security.work.task",
      "fields_get",
      [["cnc_reason"]],
      { attributes: ["selection"] },
    );
    const selection = fields.cnc_reason?.selection ?? [];
    return selection.map(([value, label]) => ({ value, label }));
  } catch {
    return [];
  }
}

const ACTION_METHOD: Record<WorkAction, string> = {
  start: "action_start",
  submit: "action_submit",
  could_not_complete: "action_could_not_complete",
  cancel: "action_cancel",
};

/** Runs a workflow method on a task. `reason` is required (and only used)
 * for `could_not_complete`. */
export async function runWorkAction(taskId: number, action: WorkAction, reason?: string): Promise<void> {
  const method = ACTION_METHOD[action];
  const args = action === "could_not_complete" ? [[taskId], reason ?? ""] : [[taskId]];
  await callKw<unknown>("security.work.task", method, args);
}

/** Upserts one checklist response row for `itemDefId` on `taskId`. */
export async function saveChecklistResponse(
  taskId: number,
  itemDefId: number,
  existingResponseId: number | null,
  value: { value_bool?: boolean; value_text?: string; value_number?: number; note?: string },
): Promise<void> {
  if (existingResponseId) {
    await callKw<boolean>("security.work.checklist.response", "write", [[existingResponseId], value]);
  } else {
    await callKw<number>("security.work.checklist.response", "create", [
      { task_id: taskId, item_def_id: itemDefId, ...value },
    ]);
  }
}

export interface RosterSignoff {
  id: number;
  batch_id: [number, string];
  role: "front_desk" | "general_manager" | "hr" | "finance" | "director";
  sequence: number;
  state: "pending" | "signed" | "flagged";
  user_id: [number, string] | false;
  signed_at: string | false;
  note: string | false;
  can_sign: boolean;
}

const ROSTER_SIGNOFF_FIELDS = [
  "id",
  "batch_id",
  "role",
  "sequence",
  "state",
  "user_id",
  "signed_at",
  "note",
  "can_sign",
];

/** All pending roster signoffs waiting on the current user's role. */
export async function fetchPendingRosterSignoffs(): Promise<RosterSignoff[]> {
  return callKw<RosterSignoff[]>(
    "security.roster.signoff",
    "search_read",
    [[["state", "=", "pending"], ["can_sign", "=", true]], ROSTER_SIGNOFF_FIELDS],
    { order: "batch_id desc, sequence asc" },
  );
}

/** Signs off a roster batch for the active user's role. */
export async function signRosterBatch(signoffId: number): Promise<boolean> {
  return callKw<boolean>(
    "security.roster.signoff",
    "action_sign",
    [[signoffId]],
  );
}

/** Flags an issue on a roster batch with an explanatory note. */
export async function flagRosterBatch(signoffId: number, note: string): Promise<boolean> {
  return callKw<boolean>(
    "security.roster.signoff",
    "action_flag",
    [[signoffId], note],
  );
}

