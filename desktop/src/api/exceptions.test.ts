import { describe, expect, it, vi, beforeEach } from "vitest";
import * as odooApi from "./odoo";
import {
  fetchExceptions,
  getExceptionCounts,
  acknowledgeException,
  resolveException,
  dismissException,
  reopenException,
  syncExceptions,
  ExceptionInstance,
} from "./exceptions";

describe("exceptions API", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockExceptions: ExceptionInstance[] = [
    {
      id: 1,
      notification_id: [10, "Roster gap at Site North"],
      rule_id: [1, "Roster Gap Rule"],
      tier: "critical",
      title: "Roster gap at Site North",
      body: "Uncovered guard slot for 2026-09-21 night shift",
      site_id: [101, "Site North"],
      notification_type: "roster_gap",
      severity: "critical",
      related_model: "security.shift.slot",
      related_id: 55,
      state: "open",
      first_seen_at: "2026-09-20 18:00:00",
      last_confirmed_at: "2026-09-20 18:30:00",
      escalation_level: 0,
      escalated_at: false,
      acknowledged_by_id: false,
      acknowledged_at: false,
      resolved_by_id: false,
      resolved_at: false,
      resolution_code: false,
      resolution_note: false,
    },
    {
      id: 2,
      notification_id: [11, "Invoice #102 overdue"],
      rule_id: [2, "Invoice Overdue Rule"],
      tier: "attention",
      title: "Invoice #102 overdue",
      body: "Payment 15 days past due",
      site_id: false,
      notification_type: "invoice_overdue",
      severity: "warning",
      related_model: "account.move",
      related_id: 102,
      state: "acknowledged",
      first_seen_at: "2026-09-19 10:00:00",
      last_confirmed_at: "2026-09-20 10:00:00",
      escalation_level: 0,
      escalated_at: false,
      acknowledged_by_id: [2, "Mitchell Admin"],
      acknowledged_at: "2026-09-19 11:00:00",
      resolved_by_id: false,
      resolved_at: false,
      resolution_code: false,
      resolution_note: false,
    },
    {
      id: 3,
      notification_id: [12, "Guard cert expiring soon"],
      rule_id: [3, "Cert Expiry Rule"],
      tier: "watch",
      title: "Guard cert expiring soon",
      body: "Firearm license expires in 25 days",
      site_id: false,
      notification_type: "cert_expiry",
      severity: "info",
      related_model: "security.employee.document",
      related_id: 77,
      state: "stale_paused",
      first_seen_at: "2026-09-15 09:00:00",
      last_confirmed_at: "2026-09-19 09:00:00",
      escalation_level: 0,
      escalated_at: false,
      acknowledged_by_id: false,
      acknowledged_at: false,
      resolved_by_id: false,
      resolved_at: false,
      resolution_code: false,
      resolution_note: false,
    },
  ];

  it("fetchExceptions calls search_read with constructed domain", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(mockExceptions);

    const res = await fetchExceptions({ tier: "critical", state: ["open", "stale_paused"] });
    expect(res).toHaveLength(3);
    expect(spy).toHaveBeenCalledWith(
      "security.exception.instance",
      "search_read",
      [
        [
          ["tier", "=", "critical"],
          ["state", "in", ["open", "stale_paused"]],
        ],
      ],
      expect.objectContaining({
        order: "tier asc, first_seen_at desc",
      })
    );
  });

  it("getExceptionCounts aggregates open exceptions by tier", async () => {
    vi.spyOn(odooApi, "callKw").mockResolvedValue([
      { tier: "critical", state: "open" },
      { tier: "critical", state: "open" },
      { tier: "attention", state: "acknowledged" },
      { tier: "watch", state: "stale_paused" },
    ]);

    const counts = await getExceptionCounts();
    expect(counts.critical).toBe(2);
    expect(counts.attention).toBe(1);
    expect(counts.watch).toBe(1);
    expect(counts.totalOpen).toBe(4);
  });

  it("acknowledgeException executes action_acknowledge", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(true);
    const success = await acknowledgeException(42);
    expect(success).toBe(true);
    expect(spy).toHaveBeenCalledWith(
      "security.exception.instance",
      "action_acknowledge",
      [[42]]
    );
  });

  it("resolveException executes action_resolve with resolution code and note", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(true);
    const success = await resolveException(42, "covered", "Covered by reserve guard Wilbert");
    expect(success).toBe(true);
    expect(spy).toHaveBeenCalledWith(
      "security.exception.instance",
      "action_resolve",
      [[42], "covered", "Covered by reserve guard Wilbert"]
    );
  });

  it("dismissException executes action_dismiss with reason", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(true);
    const success = await dismissException(42, "False alarm");
    expect(success).toBe(true);
    expect(spy).toHaveBeenCalledWith(
      "security.exception.instance",
      "action_dismiss",
      [[42], "False alarm"]
    );
  });

  it("reopenException executes action_reopen", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(true);
    const success = await reopenException(42);
    expect(success).toBe(true);
    expect(spy).toHaveBeenCalledWith(
      "security.exception.instance",
      "action_reopen",
      [[42]]
    );
  });

  it("syncExceptions executes action_sync_from_notifications", async () => {
    const spy = vi.spyOn(odooApi, "callKw").mockResolvedValue(undefined);
    await syncExceptions();
    expect(spy).toHaveBeenCalledWith(
      "security.exception.instance",
      "action_sync_from_notifications",
      []
    );
  });
});
