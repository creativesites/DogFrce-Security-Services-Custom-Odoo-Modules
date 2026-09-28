import { describe, expect, it, vi, beforeEach } from "vitest";
import * as odooApi from "./odoo";
import {
  createSupportRequest,
  fetchContextualArticles,
  submitTaskFeedback,
  fetchOwnerOverview,
  fetchDrillDownRecords,
} from "./support";

describe("support API", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls security.support.request.create_from_client with formatted payload", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue({
      id: 101,
      name: "SUPP/2026/00001",
      state: "new",
      priority: "3",
    });

    const res = await createSupportRequest({
      subject: "Screen frozen",
      client_category: "not_working",
      priority: "3",
      route: "/work",
    });

    expect(spy).toHaveBeenCalledWith(
      "security.support.request",
      "create_from_client",
      [{
        subject: "Screen frozen",
        client_category: "not_working",
        priority: "3",
        route: "/work",
      }],
    );
    expect(res.name).toBe("SUPP/2026/00001");
  });

  it("calls security.help.article.get_contextual_articles with route and workflow_key", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue([
      { id: 1, title: "Work Sweeps Guide", summary: "Sweeps summary", body: "<p>body</p>", category_id: [1, "Work"] },
    ]);

    const articles = await fetchContextualArticles("/work", "site.visit", 3);
    expect(spy).toHaveBeenCalledWith(
      "security.help.article",
      "get_contextual_articles",
      [],
      { route: "/work", workflow_key: "site.visit", limit: 3 },
    );
    expect(articles.length).toBe(1);
    expect(articles[0].title).toBe("Work Sweeps Guide");
  });

  it("submits micro-feedback via security.task.feedback.submit_feedback", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue({ id: 55, rating: "difficult" });

    const res = await submitTaskFeedback({
      task_id: 12,
      rating: "difficult",
      difficulty_reason: "system_slow_or_buggy",
      notes: "Too slow",
    });

    expect(spy).toHaveBeenCalledWith(
      "security.task.feedback",
      "submit_feedback",
      [{
        task_id: 12,
        rating: "difficult",
        difficulty_reason: "system_slow_or_buggy",
        notes: "Too slow",
      }],
    );
    expect(res.id).toBe(55);
  });

  it("fetches the owner overview and exactly the records behind a tile", async () => {
    const tile = {
      key: "overdue", label: "Overdue work", value: 2, total: null, detail: "", tone: "danger" as const, trend: null,
      drill: { model: "security.work.task", domain: [["is_overdue", "=", true]], fields: ["name", "state"], title: "Overdue work" },
    };
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue({
      period_start: "2026-09-28", period_end: "2026-09-28", generated_at: "2026-09-28 08:00:00", tiles: [tile],
    });
    const overview = await fetchOwnerOverview();
    expect(spy).toHaveBeenCalledWith("security.owner.digest", "get_owner_overview", []);
    expect(overview.tiles[0].value).toBe(2);

    const drillSpy = vi.spyOn(odooApi, "callKw").mockResolvedValue([{ id: 1, name: "Task 1" }]);
    await fetchDrillDownRecords(tile.drill, 10);
    expect(drillSpy).toHaveBeenCalledWith("security.work.task", "search_read", [[["is_overdue", "=", true]], ["name", "state"]], { limit: 10 });
  });

});
