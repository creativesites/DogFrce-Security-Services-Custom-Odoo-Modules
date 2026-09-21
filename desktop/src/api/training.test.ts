import { describe, expect, it, vi, beforeEach } from "vitest";
import * as odooApi from "./odoo";
import { fetchCourseTree, fetchMyAssignments, markLessonComplete } from "./training";

describe("training API", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchMyAssignments calls search_read with employee_id filter", async () => {
    const mockAssignments = [
      {
        id: 1,
        employee_id: [10, "Guard John"] as [number, string],
        course_id: [1, "Getting Live"] as [number, string],
        course_version_id: [1, "Getting Live v1"] as [number, string],
        due_date: "2026-10-01",
        state: "assigned" as const,
        completed_at: false,
      },
    ];
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(mockAssignments);

    const rows = await fetchMyAssignments(10);
    expect(spy).toHaveBeenCalledWith(
      "security.training.assignment",
      "search_read",
      [[["employee_id", "=", 10]], ["employee_id", "course_id", "course_version_id", "due_date", "state", "completed_at"]],
      { order: "due_date asc" },
    );
    expect(rows).toEqual(mockAssignments);
  });

  it("fetchCourseTree correctly matches lessons when section_id is an Odoo Many2one tuple", async () => {
    vi.spyOn(odooApi, "callKw").mockImplementation(async (model: string) => {
      if (model === "security.training.section") {
        return [
          { id: 1, sequence: 10, name: "Section 1" },
          { id: 2, sequence: 20, name: "Section 2" },
        ];
      }
      if (model === "security.training.lesson") {
        return [
          {
            id: 101,
            section_id: [1, "Section 1"],
            sequence: 10,
            name: "Lesson 1.1",
            content_type: "text",
            body: "<p>Hello</p>",
            video_url: false,
            deep_link_path: false,
          },
          {
            id: 102,
            section_id: [2, "Section 2"],
            sequence: 10,
            name: "Lesson 2.1",
            content_type: "video_url",
            body: false,
            video_url: "https://example.com/video",
            deep_link_path: "/odoo/action-test",
          },
        ];
      }
      if (model === "security.training.assessment") {
        return [
          { id: 50, name: "Assessment 1", pass_mark_pct: 80, max_attempts: 3 },
        ];
      }
      if (model === "security.training.question") {
        return [
          { id: 501, assessment_id: [50, "Assessment 1"], sequence: 1, text: "Q1", question_type: "single" },
        ];
      }
      if (model === "security.training.question.option") {
        return [
          { id: 5001, question_id: [501, "Q1"], sequence: 1, text: "Option A" },
        ];
      }
      return [];
    });

    const tree = await fetchCourseTree(1);
    expect(tree.sections.length).toBe(2);
    expect(tree.sections[0].lessons.length).toBe(1);
    expect(tree.sections[0].lessons[0].name).toBe("Lesson 1.1");
    expect(tree.sections[1].lessons.length).toBe(1);
    expect(tree.sections[1].lessons[0].name).toBe("Lesson 2.1");

    expect(tree.assessments.length).toBe(1);
    expect(tree.assessments[0].questions.length).toBe(1);
    expect(tree.assessments[0].questions[0].options.length).toBe(1);
  });

  it("markLessonComplete calls create on security.training.lesson.progress", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(1);

    await markLessonComplete(5, 101);
    expect(spy).toHaveBeenCalledWith(
      "security.training.lesson.progress",
      "create",
      [{ assignment_id: 5, lesson_id: 101 }],
    );
  });
});
