import { callKw } from "./odoo";
import { resolveEmployeeId } from "./work";

/**
 * Talks to the `security_training` Odoo module via plain `call_kw` — same
 * pattern as `work.ts`. No bespoke backend endpoint; the signed-in user's
 * own Odoo ACLs and record rules (own assignment vs. `group_training_
 * supervisor`) are what actually govern what comes back.
 *
 * The lesson/assessment tree isn't returned as one nested read (Odoo's
 * `call_kw` doesn't support arbitrary nested prefetch), so `fetchCourseTree`
 * composes it from several flat reads — the same shape the web client's own
 * views would issue.
 */
export { resolveEmployeeId };

export interface TrainingAssignment {
  id: number;
  employee_id: [number, string];
  course_id: [number, string];
  course_version_id: [number, string];
  due_date: string | false;
  state: "assigned" | "in_progress" | "completed" | "failed";
  completed_at: string | false;
}

export interface TrainingLesson {
  id: number;
  section_id: number;
  sequence: number;
  name: string;
  content_type: "text" | "video_url";
  body: string | false;
  video_url: string | false;
  deep_link_path: string | false;
}

export interface TrainingSection {
  id: number;
  sequence: number;
  name: string;
  lessons: TrainingLesson[];
}

export interface TrainingOption {
  id: number;
  sequence: number;
  text: string;
}

export interface TrainingQuestion {
  id: number;
  sequence: number;
  text: string;
  question_type: "single" | "multi";
  options: TrainingOption[];
}

export interface TrainingAssessment {
  id: number;
  name: string;
  pass_mark_pct: number;
  max_attempts: number;
  questions: TrainingQuestion[];
}

export interface TrainingAttempt {
  id: number;
  assessment_id: [number, string];
  attempt_number: number;
  state: "in_progress" | "passed" | "failed";
  score_pct: number;
  submitted_at: string | false;
}

export interface TrainingLessonProgress {
  id: number;
  lesson_id: [number, string];
  completed_at: string;
}

export interface CourseTree {
  sections: TrainingSection[];
  assessments: TrainingAssessment[];
}

const ASSIGNMENT_FIELDS = [
  "employee_id", "course_id", "course_version_id", "due_date", "state", "completed_at",
];

/** All training assigned to `employeeId`, soonest due date first. */
export async function fetchMyAssignments(employeeId: number): Promise<TrainingAssignment[]> {
  return callKw<TrainingAssignment[]>(
    "security.training.assignment",
    "search_read",
    [[["employee_id", "=", employeeId]], ASSIGNMENT_FIELDS],
    { order: "due_date asc" },
  );
}

export async function fetchAssignment(assignmentId: number): Promise<TrainingAssignment> {
  const rows = await callKw<TrainingAssignment[]>(
    "security.training.assignment", "read", [[assignmentId], ASSIGNMENT_FIELDS],
  );
  if (!rows[0]) throw new Error("Training assignment not found.");
  return rows[0];
}

export async function fetchLessonProgress(assignmentId: number): Promise<TrainingLessonProgress[]> {
  return callKw<TrainingLessonProgress[]>(
    "security.training.lesson.progress",
    "search_read",
    [[["assignment_id", "=", assignmentId]], ["lesson_id", "completed_at"]],
  );
}

export async function fetchAttempts(assignmentId: number): Promise<TrainingAttempt[]> {
  return callKw<TrainingAttempt[]>(
    "security.training.attempt",
    "search_read",
    [[["assignment_id", "=", assignmentId]], ["assessment_id", "attempt_number", "state", "score_pct", "submitted_at"]],
    { order: "attempt_number asc" },
  );
}

/** The full content tree for a course version: sections with their
 * lessons, and assessments with their questions and options — composed
 * from flat reads since call_kw has no nested-prefetch equivalent. */
export async function fetchCourseTree(courseVersionId: number): Promise<CourseTree> {
  const sections = await callKw<Array<{ id: number; sequence: number; name: string }>>(
    "security.training.section",
    "search_read",
    [[["course_version_id", "=", courseVersionId]], ["sequence", "name"]],
    { order: "sequence asc" },
  );
  const sectionIds = sections.map((s) => s.id);

  const lessons = sectionIds.length
    ? await callKw<TrainingLesson[]>(
        "security.training.lesson",
        "search_read",
        [[["section_id", "in", sectionIds]], ["section_id", "sequence", "name", "content_type", "body", "video_url", "deep_link_path"]],
        { order: "sequence asc" },
      )
    : [];

  const resolvedSections: TrainingSection[] = sections.map((section) => ({
    ...section,
    lessons: lessons.filter((l) => l.section_id === section.id),
  }));

  const assessmentRows = await callKw<Array<{ id: number; name: string; pass_mark_pct: number; max_attempts: number }>>(
    "security.training.assessment",
    "search_read",
    [[["course_version_id", "=", courseVersionId]], ["name", "pass_mark_pct", "max_attempts"]],
  );
  const assessmentIds = assessmentRows.map((a) => a.id);

  const questionRows = assessmentIds.length
    ? await callKw<Array<{ id: number; assessment_id: [number, string]; sequence: number; text: string; question_type: "single" | "multi" }>>(
        "security.training.question",
        "search_read",
        [[["assessment_id", "in", assessmentIds]], ["assessment_id", "sequence", "text", "question_type"]],
        { order: "sequence asc" },
      )
    : [];
  const questionIds = questionRows.map((q) => q.id);

  const optionRows = questionIds.length
    ? await callKw<Array<{ id: number; question_id: [number, string]; sequence: number; text: string }>>(
        "security.training.question.option",
        "search_read",
        [[["question_id", "in", questionIds]], ["question_id", "sequence", "text"]],
        { order: "sequence asc" },
      )
    : [];

  const assessments: TrainingAssessment[] = assessmentRows.map((assessment) => ({
    ...assessment,
    questions: questionRows
      .filter((q) => q.assessment_id[0] === assessment.id)
      .map((q) => ({
        id: q.id,
        sequence: q.sequence,
        text: q.text,
        question_type: q.question_type,
        options: optionRows
          .filter((o) => o.question_id[0] === q.id)
          .map((o) => ({ id: o.id, sequence: o.sequence, text: o.text })),
      })),
  }));

  return { sections: resolvedSections, assessments };
}

/** Optional AI assist, scoped to one lesson's own content -- never used
 * for grading (assessments are always scored deterministically). Throws
 * with a clean message the caller can show directly when AI assist isn't
 * configured (security_ai_engine not installed, or no Gemini key set) --
 * see security_training_course.py's ask_ai docstring for why this exists
 * as a deliberate, narrow exception to the MVP's no-AI scope guard. */
export async function askLessonAi(lessonId: number, question: string): Promise<string> {
  return callKw<string>("security.training.lesson", "ask_ai", [[lessonId], question]);
}

/** Marks a lesson complete for this assignment. Idempotent from the
 * caller's point of view: the model's own unique constraint means a
 * second call for an already-completed lesson raises, so callers should
 * check existing progress before calling this (the UI never shows the
 * control once a lesson is already marked done). */
export async function markLessonComplete(assignmentId: number, lessonId: number): Promise<void> {
  await callKw<number>("security.training.lesson.progress", "create", [
    { assignment_id: assignmentId, lesson_id: lessonId },
  ]);
}

export async function startAttempt(assignmentId: number, assessmentId: number): Promise<number> {
  const result = await callKw<number | [number]>(
    "security.training.attempt", "action_start_attempt", [assignmentId, assessmentId],
  );
  return Array.isArray(result) ? result[0] : result;
}

/** Submits answers for an in-progress attempt. `answers` maps question id
 * to the array of selected option ids (a single-choice question still
 * sends a one-element array). */
export async function submitAttempt(
  attemptId: number,
  answers: Record<number, number[]>,
): Promise<TrainingAttempt> {
  // action_submit returns `self` (the attempt recordset); over JSON-RPC
  // call_kw serialises that as a list of ids, not field data, so the
  // scored result is always fetched with a separate read.
  await callKw<unknown>("security.training.attempt", "action_submit", [[attemptId], answers]);
  const [attempt] = await callKw<TrainingAttempt[]>(
    "security.training.attempt", "read",
    [[attemptId], ["assessment_id", "attempt_number", "state", "score_pct", "submitted_at"]],
  );
  return attempt;
}
