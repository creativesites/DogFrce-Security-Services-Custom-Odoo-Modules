import { callKw } from "./odoo";
import type { ClientDiagnostics } from "../lib/errorCollector";

export type ClientCategory =
  | "dont_understand"
  | "not_working"
  | "no_permission"
  | "cant_find"
  | "my_info_wrong"
  | "slow"
  | "other";

export interface CreateSupportRequestPayload {
  subject: string;
  client_category: ClientCategory;
  priority?: "0" | "1" | "2" | "3";
  route?: string;
  work_task_id?: number;
  description?: string;
  diagnostics?: ClientDiagnostics;
}

export interface SupportRequestResult {
  id: number;
  name: string;
  state: string;
  priority: string;
}

export interface HelpArticle {
  id: number;
  title: string;
  summary: string;
  body: string;
  category_id: [number, string];
  route?: string;
  workflow_key?: string;
}

export type TaskFeedbackRating = "easy" | "okay" | "difficult" | "could_not_complete";

export type DifficultyReason =
  | "unclear_instructions"
  | "system_slow_or_buggy"
  | "site_conditions"
  | "time_pressure"
  | "missing_equipment"
  | "other";

export interface TaskFeedbackPayload {
  task_id: number;
  rating: TaskFeedbackRating;
  difficulty_reason?: DifficultyReason;
  notes?: string;
}

export interface OwnerMetricTile {
  value: number;
  numerator?: number;
  denominator?: number;
  is_sufficient?: boolean;
  drill_down_model: string;
  drill_down_domain: unknown[];
}

export interface OwnerOverviewData {
  period_start: string;
  period_end: string;
  workflow_coverage: OwnerMetricTile;
  on_time_rate: OwnerMetricTile;
  overdue_open: OwnerMetricTile;
  support_load: OwnerMetricTile;
  friction_rate: OwnerMetricTile;
  coverage_gap: OwnerMetricTile;
}

export async function createSupportRequest(
  payload: CreateSupportRequestPayload,
): Promise<SupportRequestResult> {
  return callKw<SupportRequestResult>("security.support.request", "create_from_client", [payload]);
}

export async function fetchContextualArticles(
  route?: string,
  workflowKey?: string,
  limit: number = 5,
): Promise<HelpArticle[]> {
  return callKw<HelpArticle[]>("security.help.article", "get_contextual_articles", [], {
    route,
    workflow_key: workflowKey,
    limit,
  });
}

export async function searchHelpArticles(query: string): Promise<HelpArticle[]> {
  return callKw<HelpArticle[]>("security.help.article", "search_articles", [query]);
}

export async function submitTaskFeedback(
  payload: TaskFeedbackPayload,
): Promise<{ id: number; rating: string }> {
  return callKw<{ id: number; rating: string }>("security.task.feedback", "submit_feedback", [payload]);
}

export async function fetchOwnerOverview(): Promise<OwnerOverviewData> {
  return callKw<OwnerOverviewData>("security.owner.digest", "get_owner_overview", []);
}

export async function fetchDrillDownRecords<T = Record<string, unknown>>(
  model: string,
  domain: unknown[],
  fields: string[],
  limit: number = 50,
): Promise<T[]> {
  return callKw<T[]>(model, "search_read", [domain, fields], { limit });
}
