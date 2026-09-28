import type { TodayTask } from "../../api/today";
import { parseOdooDatetime } from "../../shell/pages/myWork.logic";

/**
 * Presentation of a Today card. Every *fact* (overdue, waiting, done) comes
 * from the server; this file only turns those facts into the words and tone
 * the employee sees.
 */

export type CardTone = "danger" | "warning" | "info" | "success" | "neutral";

export interface CardStatus {
  label: string;
  tone: CardTone;
}

const DONE_STATES: TodayTask["state"][] = ["submitted", "verified"];

export function isDone(task: TodayTask): boolean {
  return DONE_STATES.includes(task.state);
}

export function dueTime(task: TodayTask): string | null {
  const d = task.due_at ? parseOdooDatetime(task.due_at) : null;
  return d ? d.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }) : null;
}

export function cardStatus(task: TodayTask): CardStatus {
  if (task.state === "verified") return { label: "Done and checked", tone: "success" };
  if (task.state === "submitted") return { label: "Done", tone: "success" };
  if (task.state === "could_not_complete") return { label: "Couldn't be done: reported", tone: "warning" };
  if (task.is_overdue) return { label: `Overdue${dueTime(task) ? `, was due ${dueTime(task)}` : ""}`, tone: "danger" };
  if (task.readiness === "waiting") return { label: `Waiting for ${task.waiting_on || "an earlier step"}`, tone: "neutral" };
  if (task.state === "in_progress") return { label: dueTime(task) ? `In progress · due ${dueTime(task)}` : "In progress", tone: "info" };
  return { label: dueTime(task) ? `Due ${dueTime(task)}` : "To do", tone: "info" };
}

/** The one thing to do next on this card. */
export type NextAction = "learn" | "guide" | "open" | "wait" | "none";

export function nextAction(task: TodayTask, canGuide: boolean): NextAction {
  if (isDone(task) || task.state === "could_not_complete" || task.state === "cancelled") return "none";
  if (task.readiness === "waiting") return "wait";
  if (task.training && !task.training.done) return "learn";
  if (canGuide && task.guidance_flow_code) return "guide";
  return "open";
}

/** "3 of 5 done" for the header. Counts only what is on the list. */
export function progress(tasks: TodayTask[]): { done: number; total: number } {
  const live = tasks.filter((t) => t.state !== "cancelled");
  return { done: live.filter(isDone).length, total: live.length };
}
