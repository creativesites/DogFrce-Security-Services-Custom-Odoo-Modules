import { callKw } from "./odoo";

export type ExceptionTier = "critical" | "attention" | "watch";

export type ExceptionState =
  | "open"
  | "acknowledged"
  | "resolved"
  | "auto_resolved"
  | "stale_paused";

export type ResolutionCode =
  | "fixed"
  | "covered"
  | "explained"
  | "not_an_issue"
  | "duplicate"
  | "deferred";

export const RESOLUTION_CODE_LABELS: Record<ResolutionCode, string> = {
  fixed: "Fixed",
  covered: "Covered",
  explained: "Explained",
  not_an_issue: "Not an Issue",
  duplicate: "Duplicate",
  deferred: "Deferred",
};

export interface ExceptionInstance {
  id: number;
  notification_id: [number, string] | number;
  rule_id: [number, string] | number;
  tier: ExceptionTier;
  title: string;
  body?: string | false;
  site_id: [number, string] | false;
  notification_type: string;
  severity: string;
  related_model?: string | false;
  related_id?: number | false;
  state: ExceptionState;
  first_seen_at: string;
  last_confirmed_at: string;
  escalation_level: number;
  escalated_at: string | false;
  acknowledged_by_id: [number, string] | false;
  acknowledged_at: string | false;
  resolved_by_id: [number, string] | false;
  resolved_at: string | false;
  resolution_code: ResolutionCode | false;
  resolution_note: string | false;
}

export interface ExceptionCounts {
  critical: number;
  attention: number;
  watch: number;
  totalOpen: number;
}

export interface ExceptionFilters {
  tier?: ExceptionTier;
  state?: ExceptionState | ExceptionState[];
  siteId?: number;
}

const EXCEPTION_FIELDS = [
  "id",
  "notification_id",
  "rule_id",
  "tier",
  "title",
  "body",
  "site_id",
  "notification_type",
  "severity",
  "related_model",
  "related_id",
  "state",
  "first_seen_at",
  "last_confirmed_at",
  "escalation_level",
  "escalated_at",
  "acknowledged_by_id",
  "acknowledged_at",
  "resolved_by_id",
  "resolved_at",
  "resolution_code",
  "resolution_note",
];

export async function fetchExceptions(filters: ExceptionFilters = {}): Promise<ExceptionInstance[]> {
  const domain: unknown[] = [];

  if (filters.tier) {
    domain.push(["tier", "=", filters.tier]);
  }

  if (filters.state) {
    if (Array.isArray(filters.state)) {
      domain.push(["state", "in", filters.state]);
    } else {
      domain.push(["state", "=", filters.state]);
    }
  }

  if (filters.siteId) {
    domain.push(["site_id", "=", filters.siteId]);
  }

  return callKw<ExceptionInstance[]>(
    "security.exception.instance",
    "search_read",
    [domain],
    {
      fields: EXCEPTION_FIELDS,
      order: "tier asc, first_seen_at desc",
    }
  );
}

/** Open-exception counts per tier, counted by the server (one `search_count`
 * each) rather than by downloading every open record. */
export async function getExceptionCounts(): Promise<ExceptionCounts> {
  const open: unknown[] = ["state", "in", OPEN_EXCEPTION_STATES];
  const count = (extra: unknown[][]) =>
    callKw<number>("security.exception.instance", "search_count", [[open, ...extra]]);
  const [critical, attention, watch, totalOpen] = await Promise.all([
    count([["tier", "=", "critical"]]),
    count([["tier", "=", "attention"]]),
    count([["tier", "=", "watch"]]),
    count([]),
  ]);
  return { critical, attention, watch, totalOpen };
}

/** The states the inbox treats as "still needs attention". */
export const OPEN_EXCEPTION_STATES: ExceptionState[] = ["open", "stale_paused", "acknowledged"];

export async function acknowledgeException(id: number): Promise<boolean> {
  await callKw<boolean>(
    "security.exception.instance",
    "action_acknowledge",
    [[id]]
  );
  return true;
}

export async function resolveException(
  id: number,
  resolutionCode: ResolutionCode = "fixed",
  resolutionNote: string = ""
): Promise<boolean> {
  await callKw<boolean>(
    "security.exception.instance",
    "action_resolve",
    [[id], resolutionCode, resolutionNote]
  );
  return true;
}

export async function dismissException(id: number, reason: string = ""): Promise<boolean> {
  await callKw<boolean>(
    "security.exception.instance",
    "action_dismiss",
    [[id], reason]
  );
  return true;
}

export async function reopenException(id: number): Promise<boolean> {
  await callKw<boolean>(
    "security.exception.instance",
    "action_reopen",
    [[id]]
  );
  return true;
}

export async function syncExceptions(): Promise<void> {
  await callKw<void>(
    "security.exception.instance",
    "action_sync_from_notifications",
    []
  );
}
