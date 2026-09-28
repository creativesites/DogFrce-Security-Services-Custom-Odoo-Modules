import { callKw } from "./odoo";

/** Mirrors security.guidance.session._payload(). */
export interface GuidanceStep {
  id: number;
  index: number;
  title: string;
  instruction: string;
  why: string | false;
  has_help: boolean;
  success_message: string | false;
  deviation_hint: string | false;
  confirmable: boolean;
}

export interface GuidanceSession {
  id: number;
  state: "active" | "completed" | "abandoned";
  practice: boolean;
  flow: { code: string; name: string; objective: string | false; why: string | false };
  task: { id: number; name: string; state: string } | false;
  site: string | false;
  date: string | false;
  step: GuidanceStep | false;
  total: number;
  steps: Array<{ title: string; done: boolean }>;
  off_track: boolean;
  highlight_nonce: number;
}

export interface GuidanceHelp {
  help_html: string | false;
  deviation_hint: string | false;
}

export interface GuidanceAnswer {
  /** true only when the text came from the AI provider. */
  ai: boolean;
  answer: string;
  sources: string[];
}

const MODEL = "security.guidance.session";

export function startGuidance(flowCode: string, taskId?: number): Promise<GuidanceSession> {
  return callKw<GuidanceSession>(MODEL, "start", [flowCode], taskId ? { task_id: taskId } : {});
}

export function fetchActiveGuidance(): Promise<GuidanceSession | false> {
  return callKw<GuidanceSession | false>(MODEL, "get_active");
}

export function showMe(): Promise<GuidanceSession | false> {
  return callKw<GuidanceSession | false>(MODEL, "show_me");
}

export function requestHelp(): Promise<GuidanceHelp | false> {
  return callKw<GuidanceHelp | false>(MODEL, "request_help");
}

export function confirmStep(): Promise<GuidanceSession> {
  return callKw<GuidanceSession>(MODEL, "confirm_step");
}

export function abandonGuidance(): Promise<boolean> {
  return callKw<boolean>(MODEL, "abandon");
}

export function askGuidanceAi(question: string): Promise<GuidanceAnswer> {
  return callKw<GuidanceAnswer>(MODEL, "ask_ai", [question]);
}
