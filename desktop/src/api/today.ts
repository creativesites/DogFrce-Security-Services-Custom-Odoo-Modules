import { callKw } from "./odoo";

/**
 * Today and Team Today. The server (security_work + security_deployguard_ops)
 * decides what is due, overdue, waiting or done. This module only shapes the
 * calls, and nothing here re-derives a rule. When the Platform exists this is
 * the file that switches from Odoo to /v1.
 */

export interface TodayTraining {
  course_id: number;
  course_name: string;
  assignment_id: number | false;
  done: boolean;
}

export interface TodayTask {
  id: number;
  name: string;
  state: "open" | "in_progress" | "submitted" | "verified" | "could_not_complete" | "rejected" | "cancelled";
  due_at: string | false;
  is_overdue: boolean;
  site: string | false;
  responsibility: string | false;
  why_it_matters: string | false;
  readiness: "ready" | "waiting";
  waiting_on: string | false;
  odoo_path: string | false;
  guidance_flow_code: string | false;
  checklist: boolean;
  /** Present when security_deployguard_ops is installed. */
  training?: TodayTraining | false;
}

export interface MyToday {
  employee: { id: number; name: string } | false;
  tasks: TodayTask[];
}

export function fetchMyToday(): Promise<MyToday> {
  return callKw<MyToday>("security.work.task", "get_my_today");
}

export interface TeamCell {
  task_id: number;
  state: TodayTask["state"];
  is_overdue: boolean;
  readiness: TodayTask["readiness"];
  employee: string;
}

export interface TeamPerson {
  employee: string;
  employee_id: number;
  expected: number[];
  done: number[];
  overdue: number[];
  could_not_complete: number[];
  waiting: number[];
}

export interface TeamToday {
  date: string;
  steps: Array<{ id: number; name: string; owner: string }>;
  pipeline: Array<{ site: string; site_id: number | false; cells: Record<string, TeamCell> }>;
  people: TeamPerson[];
}

export function fetchTeamToday(): Promise<TeamToday> {
  return callKw<TeamToday>("security.work.task", "get_team_today");
}

export interface TaskEvidenceRow {
  id: number;
  name: string;
  employee_id: [number, string] | false;
  site_id: [number, string] | false;
  due_at: string | false;
  state: TodayTask["state"];
  cnc_reason: string | false;
  cnc_note: string | false;
}

/** The records behind a Team Today number, so every count can be checked. */
export function fetchTasksByIds(ids: number[]): Promise<TaskEvidenceRow[]> {
  if (ids.length === 0) return Promise.resolve([]);
  return callKw<TaskEvidenceRow[]>("security.work.task", "search_read", [
    [["id", "in", ids]],
    ["name", "employee_id", "site_id", "due_at", "state", "cnc_reason", "cnc_note"],
  ]);
}
