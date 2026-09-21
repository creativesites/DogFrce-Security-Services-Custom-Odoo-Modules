import { describe, expect, it } from "vitest";
import {
  adjacentLessons, allLessons, attemptsRemaining, attemptsUsed, findLessonSection, isAnswerCorrect, isEverythingDone, isLessonDone,
  latestAttemptFor, lessonProgressSummary,
} from "./myTraining.logic";
import type { CourseTree, TrainingAssessment, TrainingAttempt, TrainingLessonProgress } from "../../api/training";

function lessonProgress(lessonId: number): TrainingLessonProgress {
  return { id: lessonId * 100, lesson_id: [lessonId, "Lesson"], completed_at: "2026-01-01 00:00:00" };
}

function attempt(overrides: Partial<Omit<TrainingAttempt, "assessment_id">> & { assessment_id: number }): TrainingAttempt {
  const { assessment_id, ...rest } = overrides;
  return {
    id: 1,
    attempt_number: 1,
    state: "in_progress",
    score_pct: 0,
    submitted_at: false,
    ...rest,
    assessment_id: [assessment_id, "Assessment"],
  };
}

const tree: CourseTree = {
  sections: [
    {
      id: 1, sequence: 10, name: "Section 1",
      lessons: [
        { id: 11, section_id: 1, sequence: 10, name: "L1", content_type: "text", body: "a", video_url: false, deep_link_path: false },
        { id: 12, section_id: 1, sequence: 20, name: "L2", content_type: "text", body: "b", video_url: false, deep_link_path: false },
      ],
    },
    {
      id: 2, sequence: 20, name: "Section 2",
      lessons: [
        { id: 21, section_id: 2, sequence: 10, name: "L3", content_type: "text", body: "c", video_url: false, deep_link_path: false },
      ],
    },
  ],
  assessments: [
    { id: 100, name: "Quiz", pass_mark_pct: 80, max_attempts: 3, questions: [] },
  ],
};

describe("allLessons", () => {
  it("flattens every section's lessons in order", () => {
    const ids = allLessons(tree).map((l) => l.id);
    expect(ids).toEqual([11, 12, 21]);
  });
});

describe("isLessonDone", () => {
  it("is true once a progress row exists for the lesson", () => {
    expect(isLessonDone(11, [lessonProgress(11)])).toBe(true);
  });
  it("is false when no progress row matches", () => {
    expect(isLessonDone(11, [lessonProgress(12)])).toBe(false);
  });
  it("is false with empty progress", () => {
    expect(isLessonDone(11, [])).toBe(false);
  });
});

describe("lessonProgressSummary", () => {
  it("counts done vs total across all sections", () => {
    expect(lessonProgressSummary(tree, [lessonProgress(11), lessonProgress(21)])).toEqual({ done: 2, total: 3 });
  });
  it("is {0, total} with no progress", () => {
    expect(lessonProgressSummary(tree, [])).toEqual({ done: 0, total: 3 });
  });
});

describe("latestAttemptFor", () => {
  it("returns null when there are no attempts", () => {
    expect(latestAttemptFor(100, [])).toBeNull();
  });
  it("prefers a passed attempt over a later failed one", () => {
    const passed = attempt({ assessment_id: 100, attempt_number: 1, state: "passed" });
    const failed = attempt({ assessment_id: 100, attempt_number: 2, state: "failed" });
    expect(latestAttemptFor(100, [passed, failed])).toBe(passed);
  });
  it("returns the highest attempt_number when none passed", () => {
    const first = attempt({ assessment_id: 100, attempt_number: 1, state: "failed" });
    const second = attempt({ assessment_id: 100, attempt_number: 2, state: "failed" });
    expect(latestAttemptFor(100, [first, second])).toBe(second);
  });
  it("ignores attempts for a different assessment", () => {
    const other = attempt({ assessment_id: 999, attempt_number: 1, state: "passed" });
    expect(latestAttemptFor(100, [other])).toBeNull();
  });
});

describe("attemptsUsed / attemptsRemaining", () => {
  const assessment: TrainingAssessment = { id: 100, name: "Quiz", pass_mark_pct: 80, max_attempts: 3, questions: [] };

  it("counts attempts for the given assessment only", () => {
    const attempts = [
      attempt({ assessment_id: 100, attempt_number: 1 }),
      attempt({ assessment_id: 100, attempt_number: 2 }),
      attempt({ assessment_id: 999, attempt_number: 1 }),
    ];
    expect(attemptsUsed(100, attempts)).toBe(2);
    expect(attemptsRemaining(assessment, attempts)).toBe(1);
  });

  it("never goes negative when attempts exceed the limit", () => {
    const attempts = [1, 2, 3, 4].map((n) => attempt({ assessment_id: 100, attempt_number: n }));
    expect(attemptsRemaining(assessment, attempts)).toBe(0);
  });

  it("is the full max when nothing attempted yet", () => {
    expect(attemptsRemaining(assessment, [])).toBe(3);
  });
});

describe("isEverythingDone", () => {
  it("is false when lessons remain", () => {
    expect(isEverythingDone(tree, [], [])).toBe(false);
  });

  it("is false when lessons are done but the assessment isn't passed", () => {
    const progress = [lessonProgress(11), lessonProgress(12), lessonProgress(21)];
    expect(isEverythingDone(tree, progress, [])).toBe(false);
  });

  it("is true once every lesson is done and every assessment passed", () => {
    const progress = [lessonProgress(11), lessonProgress(12), lessonProgress(21)];
    const attempts = [attempt({ assessment_id: 100, state: "passed" })];
    expect(isEverythingDone(tree, progress, attempts)).toBe(true);
  });

  it("is true with no assessments at all once lessons are done", () => {
    const noAssessmentTree: CourseTree = { ...tree, assessments: [] };
    const progress = [lessonProgress(11), lessonProgress(12), lessonProgress(21)];
    expect(isEverythingDone(noAssessmentTree, progress, [])).toBe(true);
  });
});

describe("isAnswerCorrect", () => {
  const question = { options: [{ id: 1 }, { id: 2 }, { id: 3 }] };

  it("is true for an exact match", () => {
    expect(isAnswerCorrect(question, new Set([1, 3]), new Set([1, 3]))).toBe(true);
  });

  it("is false when missing a correct option", () => {
    expect(isAnswerCorrect(question, new Set([1, 3]), new Set([1]))).toBe(false);
  });

  it("is false when an extra wrong option is selected", () => {
    expect(isAnswerCorrect(question, new Set([1]), new Set([1, 2]))).toBe(false);
  });

  it("is false for an empty selection against a non-empty answer key", () => {
    expect(isAnswerCorrect(question, new Set([1]), new Set())).toBe(false);
  });
});

describe("adjacentLessons", () => {
  it("returns null prev for the first lesson and correct next", () => {
    const adj = adjacentLessons(tree, 11);
    expect(adj.prev).toBeNull();
    expect(adj.next?.id).toBe(12);
    expect(adj.index).toBe(0);
    expect(adj.total).toBe(3);
  });

  it("returns correct prev and next for a middle lesson", () => {
    const adj = adjacentLessons(tree, 12);
    expect(adj.prev?.id).toBe(11);
    expect(adj.next?.id).toBe(21);
    expect(adj.index).toBe(1);
  });

  it("returns correct prev and null next for the last lesson", () => {
    const adj = adjacentLessons(tree, 21);
    expect(adj.prev?.id).toBe(12);
    expect(adj.next).toBeNull();
    expect(adj.index).toBe(2);
  });
});

describe("findLessonSection", () => {
  it("finds section containing lesson", () => {
    const s = findLessonSection(tree, 12);
    expect(s?.id).toBe(1);
    expect(s?.name).toBe("Section 1");
  });

  it("returns null when lesson is not found", () => {
    expect(findLessonSection(tree, 999)).toBeNull();
  });
});
