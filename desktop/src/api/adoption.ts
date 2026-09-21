import { callKw } from "./odoo";

export type AdoptionConfidence = "insufficient" | "low" | "medium" | "high";

export type ScoreFactorKey =
  | "f1_coverage"
  | "f2_timeliness"
  | "f3_training"
  | "f4_responsiveness"
  | "f5_quality";

export interface ScoreFactor {
  id: number;
  factor_key: ScoreFactorKey;
  weight: number;
  raw_value: number;
  weighted_value: number;
}

export interface AdoptionSnapshot {
  id: number;
  employee_id: [number, string] | number;
  window_start: string;
  window_end: string;
  computed_at: string;
  expected_total: number;
  excused_total: number;
  score: number;
  confidence: AdoptionConfidence;
  factor_ids: number[];
  factors?: ScoreFactor[];
}

export type ExpectedWorkState = "fulfilled" | "missed" | "excused";

export type ExcusalReason =
  | "leave"
  | "absence"
  | "no_shift"
  | "reassigned"
  | "site_inactive"
  | "system_fault"
  | "suppressed_by_admin";

export type WorkflowKey =
  | "attendance.post"
  | "site.visit"
  | "incident.review"
  | "training.mandatory"
  | "shift.handover";

export interface ExpectedWorkItem {
  id: number;
  workflow_key: WorkflowKey;
  employee_id: [number, string] | number;
  site_id: [number, string] | false;
  period_date: string;
  due_at: string | false;
  fulfilled_at: string | false;
  state: ExpectedWorkState;
  excusal_reason: ExcusalReason | false;
  on_time: boolean;
}

export type CheckinAnswerCode =
  | "didnt_know"
  | "couldnt_find"
  | "not_working"
  | "no_permission"
  | "someone_else"
  | "was_away"
  | "too_busy"
  | "other";

export interface AbandonmentCheckin {
  id: number;
  signal_id: [number, string];
  sent_at: string;
  answer: CheckinAnswerCode | false;
  answered_at: string | false;
  routed_action: string | false;
  workflow_key?: WorkflowKey;
  employee_name?: string;
}

export const WORKFLOW_LABELS: Record<WorkflowKey, string> = {
  "attendance.post": "Attendance Posting",
  "site.visit": "Site Visit & Checklist",
  "incident.review": "Incident Review",
  "training.mandatory": "Mandatory Training",
  "shift.handover": "Shift Handover",
};

export const FACTOR_CONFIG: Record<
  ScoreFactorKey,
  { label: string; weight: number; description: string }
> = {
  f1_coverage: {
    label: "Workflow Coverage",
    weight: 0.4,
    description: "Expected operational tasks actually executed in the system.",
  },
  f2_timeliness: {
    label: "Timeliness",
    weight: 0.2,
    description: "Tasks fulfilled at or before deadline.",
  },
  f3_training: {
    label: "Training & Currency",
    weight: 0.15,
    description: "Mandatory course currency and certification standing.",
  },
  f4_responsiveness: {
    label: "Responsiveness",
    weight: 0.15,
    description: "Actioning verifications and assigned task submissions.",
  },
  f5_quality: {
    label: "Reporting Quality",
    weight: 0.1,
    description: "Submissions completed first time without return for rework.",
  },
};

export const CHECKIN_OPTION_LABELS: Record<CheckinAnswerCode, string> = {
  didnt_know: "I didn't know I had to",
  couldnt_find: "I couldn't find where",
  not_working: "Something isn't working",
  no_permission: "I don't have permission",
  someone_else: "Someone else is doing it",
  was_away: "I was away",
  too_busy: "Too busy / short-staffed",
  other: "Other explanation",
};

/**
 * Fetches the latest adoption snapshot for an employee, including its 5 factors.
 */
export async function fetchEmployeeSnapshot(
  employeeId: number
): Promise<AdoptionSnapshot | null> {
  const snapshots = await callKw<AdoptionSnapshot[]>(
    "security.adoption.snapshot",
    "search_read",
    [[["employee_id", "=", employeeId]]],
    {
      fields: [
        "id",
        "employee_id",
        "window_start",
        "window_end",
        "computed_at",
        "expected_total",
        "excused_total",
        "score",
        "confidence",
        "factor_ids",
      ],
      limit: 1,
      order: "window_end desc, id desc",
    }
  );

  if (!snapshots || snapshots.length === 0) {
    return null;
  }

  const snapshot = snapshots[0];
  if (snapshot.factor_ids && snapshot.factor_ids.length > 0) {
    const factors = await callKw<ScoreFactor[]>(
      "security.adoption.score.factor",
      "search_read",
      [[["id", "in", snapshot.factor_ids]]],
      {
        fields: ["id", "factor_key", "weight", "raw_value", "weighted_value"],
      }
    );
    snapshot.factors = factors;
  } else {
    snapshot.factors = [];
  }

  return snapshot;
}

/**
 * Fetches expected work items for an employee within an optional date window.
 */
export async function fetchExpectedWorkItems(
  employeeId: number,
  windowStart?: string,
  windowEnd?: string
): Promise<ExpectedWorkItem[]> {
  const domain: unknown[] = [["employee_id", "=", employeeId]];
  if (windowStart) domain.push(["period_date", ">=", windowStart]);
  if (windowEnd) domain.push(["period_date", "<=", windowEnd]);

  return await callKw<ExpectedWorkItem[]>(
    "security.adoption.expected.work.item",
    "search_read",
    [domain],
    {
      fields: [
        "id",
        "workflow_key",
        "employee_id",
        "site_id",
        "period_date",
        "due_at",
        "fulfilled_at",
        "state",
        "excusal_reason",
        "on_time",
      ],
      order: "period_date desc, id desc",
      limit: 100,
    }
  );
}

/**
 * Fetches pending assistance check-ins for this employee that need an answer.
 */
export async function fetchPendingCheckin(
  employeeId: number
): Promise<AbandonmentCheckin | null> {
  const checkins = await callKw<AbandonmentCheckin[]>(
    "security.adoption.checkin",
    "search_read",
    [[
      ["signal_id.employee_id", "=", employeeId],
      ["answer", "=", false],
    ]],
    {
      fields: [
        "id",
        "signal_id",
        "sent_at",
        "answer",
        "answered_at",
        "routed_action",
      ],
      order: "id desc",
      limit: 1,
    }
  );

  if (!checkins || checkins.length === 0) return null;
  return checkins[0];
}

/**
 * Submits an answer to an assistance check-in.
 */
export async function submitCheckinAnswer(
  checkinId: number,
  answer: CheckinAnswerCode
): Promise<boolean> {
  await callKw<unknown>(
    "security.adoption.checkin",
    "action_record_answer",
    [[checkinId], answer]
  );
  return true;
}

/**
 * Fetches team snapshots for managers / supervisors to view overview.
 */
export async function fetchTeamSnapshots(): Promise<AdoptionSnapshot[]> {
  return await callKw<AdoptionSnapshot[]>(
    "security.adoption.snapshot",
    "search_read",
    [[]],
    {
      fields: [
        "id",
        "employee_id",
        "window_start",
        "window_end",
        "computed_at",
        "expected_total",
        "excused_total",
        "score",
        "confidence",
        "factor_ids",
      ],
      order: "score desc, expected_total desc",
      limit: 50,
    }
  );
}

/**
 * Triggers re-computation of adoption snapshots and materialization.
 */
export async function triggerAdoptionRefresh(): Promise<void> {
  await callKw<unknown>(
    "security.adoption.expected.work.item",
    "action_materialize_all",
    []
  );
  await callKw<unknown>(
    "security.adoption.snapshot",
    "action_compute_all",
    []
  );
}
