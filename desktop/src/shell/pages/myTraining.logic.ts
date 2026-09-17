/**
 * Pure logic for My Training — kept separate from MyTraining.tsx so it can
 * be unit-tested without mounting React or touching Tauri IPC. Mirrors
 * myWork.logic.ts's split.
 */

import type {
  CourseTree, TrainingAssessment, TrainingAssignment, TrainingAttempt, TrainingLesson, TrainingLessonProgress,
} from "../../api/training";

export const ASSIGNMENT_STATE_LABELS: Record<TrainingAssignment["state"], string> = {
  assigned: "Not started",
  in_progress: "In progress",
  completed: "Completed",
  failed: "Failed",
};

/** All lessons across every section, in display order. */
export function allLessons(tree: CourseTree): TrainingLesson[] {
  return tree.sections.flatMap((s) => s.lessons);
}

export function isLessonDone(lessonId: number, progress: TrainingLessonProgress[]): boolean {
  return progress.some((p) => p.lesson_id[0] === lessonId);
}

/** {done, total} lesson count for a progress bar / "3 of 7" label. */
export function lessonProgressSummary(
  tree: CourseTree,
  progress: TrainingLessonProgress[],
): { done: number; total: number } {
  const lessons = allLessons(tree);
  const done = lessons.filter((l) => isLessonDone(l.id, progress)).length;
  return { done, total: lessons.length };
}

/** The best (passed, or else most recent) attempt for an assessment, if any. */
export function latestAttemptFor(assessmentId: number, attempts: TrainingAttempt[]): TrainingAttempt | null {
  const forAssessment = attempts.filter((a) => a.assessment_id[0] === assessmentId);
  if (forAssessment.length === 0) return null;
  const passed = forAssessment.find((a) => a.state === "passed");
  if (passed) return passed;
  return forAssessment.reduce((latest, a) => (a.attempt_number > latest.attempt_number ? a : latest));
}

export function attemptsUsed(assessmentId: number, attempts: TrainingAttempt[]): number {
  return attempts.filter((a) => a.assessment_id[0] === assessmentId).length;
}

export function attemptsRemaining(assessment: TrainingAssessment, attempts: TrainingAttempt[]): number {
  return Math.max(0, assessment.max_attempts - attemptsUsed(assessment.id, attempts));
}

/** Whether every lesson is done and every assessment has a passed attempt —
 * the same rule the Odoo model uses to flip an assignment to "completed",
 * computed client-side so the UI can show "you're done!" the instant the
 * last action happens, without waiting on a refetch. */
export function isEverythingDone(tree: CourseTree, progress: TrainingLessonProgress[], attempts: TrainingAttempt[]): boolean {
  const { done, total } = lessonProgressSummary(tree, progress);
  if (done < total) return false;
  return tree.assessments.every((a) => attemptsUsed(a.id, attempts) > 0 && latestAttemptFor(a.id, attempts)?.state === "passed");
}

/** Score a set of selected options against a question client-side, for
 * instant per-question feedback in the assessment runner before the real
 * (server-authoritative) grading happens on submit. Never used to decide
 * pass/fail — that's always the server's action_submit. */
export function isAnswerCorrect(question: { options: { id: number }[] }, correctOptionIds: Set<number>, selected: Set<number>): boolean {
  const questionOptionIds = new Set(question.options.map((o) => o.id));
  const correctForThisQuestion = new Set([...correctOptionIds].filter((id) => questionOptionIds.has(id)));
  return selected.size === correctForThisQuestion.size && [...selected].every((id) => correctForThisQuestion.has(id));
}
