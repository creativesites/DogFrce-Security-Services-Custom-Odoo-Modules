import { describe, expect, it, vi, beforeEach } from "vitest";
import * as odooApi from "./odoo";
import {
  fetchEmployeeSnapshot,
  fetchExpectedWorkItems,
  fetchPendingCheckin,
  submitCheckinAnswer,
  FACTOR_CONFIG,
  CHECKIN_OPTION_LABELS,
} from "./adoption";

describe("adoption API", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetchEmployeeSnapshot returns snapshot with factors joined", async () => {
    const mockSnapshot = {
      id: 5,
      employee_id: [1, "Mitchell Admin"] as [number, string],
      window_start: "2026-09-13",
      window_end: "2026-09-19",
      computed_at: "2026-09-20 00:00:00",
      expected_total: 20,
      excused_total: 2,
      score: 92,
      confidence: "medium" as const,
      factor_ids: [11, 12, 13, 14, 15],
    };

    const mockFactors = [
      { id: 11, factor_key: "f1_coverage" as const, weight: 0.4, raw_value: 85.0, weighted_value: 34.0 },
      { id: 12, factor_key: "f2_timeliness" as const, weight: 0.2, raw_value: 90.0, weighted_value: 18.0 },
      { id: 13, factor_key: "f3_training" as const, weight: 0.15, raw_value: 100.0, weighted_value: 15.0 },
      { id: 14, factor_key: "f4_responsiveness" as const, weight: 0.15, raw_value: 100.0, weighted_value: 15.0 },
      { id: 15, factor_key: "f5_quality" as const, weight: 0.1, raw_value: 100.0, weighted_value: 10.0 },
    ];

    vi.spyOn(odooApi, "callKw").mockImplementation(async (model: string) => {
      if (model === "security.adoption.snapshot") {
        return [mockSnapshot];
      }
      if (model === "security.adoption.score.factor") {
        return mockFactors;
      }
      return [];
    });

    const res = await fetchEmployeeSnapshot(1);
    expect(res).not.toBeNull();
    expect(res?.score).toBe(92);
    expect(res?.confidence).toBe("medium");
    expect(res?.factors).toHaveLength(5);
    expect(res?.factors?.[0].factor_key).toBe("f1_coverage");
  });

  it("fetchEmployeeSnapshot returns null when no snapshot exists", async () => {
    vi.spyOn(odooApi, "callKw").mockResolvedValue([]);
    const res = await fetchEmployeeSnapshot(999);
    expect(res).toBeNull();
  });

  it("fetchExpectedWorkItems passes employee_id and date window", async () => {
    const mockItems = [
      {
        id: 101,
        workflow_key: "attendance.post" as const,
        employee_id: [1, "Mitchell Admin"] as [number, string],
        site_id: [10, "Headquarters"] as [number, string],
        period_date: "2026-09-18",
        due_at: "2026-09-18 08:00:00",
        fulfilled_at: "2026-09-18 07:55:00",
        state: "fulfilled" as const,
        excusal_reason: false as const,
        on_time: true,
      },
    ];

    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(mockItems);

    const items = await fetchExpectedWorkItems(1, "2026-09-13", "2026-09-19");
    expect(spy).toHaveBeenCalledWith(
      "security.adoption.expected.work.item",
      "search_read",
      [[
        ["employee_id", "=", 1],
        ["period_date", ">=", "2026-09-13"],
        ["period_date", "<=", "2026-09-19"],
      ]],
      expect.objectContaining({ limit: 100 })
    );
    expect(items).toEqual(mockItems);
  });

  it("submitCheckinAnswer records answer code on checkin model", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(true);
    const success = await submitCheckinAnswer(42, "not_working");
    expect(spy).toHaveBeenCalledWith(
      "security.adoption.checkin",
      "action_record_answer",
      [[42], "not_working"]
    );
    expect(success).toBe(true);
  });

  it("fetchPendingCheckin queries unanswered checkins for employee", async () => {
    const mockCheckins = [
      {
        id: 7,
        signal_id: [12, "Signal #12"] as [number, string],
        sent_at: "2026-09-19 10:00:00",
        answer: false as const,
        answered_at: false as const,
        routed_action: false as const,
      },
    ];
    vi.spyOn(odooApi, "callKw").mockResolvedValue(mockCheckins);
    const checkin = await fetchPendingCheckin(1);
    expect(checkin).toEqual(mockCheckins[0]);
  });

  it("FACTOR_CONFIG weights sum to 1.0 (100%)", () => {
    const totalWeight = Object.values(FACTOR_CONFIG).reduce(
      (acc, curr) => acc + curr.weight,
      0
    );
    expect(Math.round(totalWeight * 100) / 100).toBe(1.0);
  });

  it("CHECKIN_OPTION_LABELS contains all 8 spec answers", () => {
    expect(Object.keys(CHECKIN_OPTION_LABELS)).toHaveLength(8);
    expect(CHECKIN_OPTION_LABELS.not_working).toBe("Something isn't working");
  });
});
