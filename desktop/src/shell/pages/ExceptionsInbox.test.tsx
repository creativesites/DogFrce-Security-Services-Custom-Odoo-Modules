// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { backend } from "../../test/fakeTauri";
import { ExceptionsInbox } from "./ExceptionsInbox";
import { ViewModeProvider } from "../../app/viewMode";

const item = {
  id: 1, notification_id: [10, "Roster gap"], rule_id: [1, "Roster gap"], tier: "critical",
  title: "Roster gap at Main Gate", body: "Uncovered night shift", site_id: [101, "ABC Mall"],
  notification_type: "roster_gap", severity: "critical", related_model: false, related_id: 0,
  state: "open", first_seen_at: "2026-09-28 06:00:00", last_seen_at: "2026-09-28 06:00:00",
  acknowledged_at: false, acknowledged_by: false, resolved_at: false, resolved_by: false,
  resolution_code: false, resolution_note: false, escalation_level: 0, next_escalation_at: false,
};

let acknowledged = 0;
beforeEach(() => {
  backend.reset();
  acknowledged = 0;
  backend.callKw = async (_model, method) => {
    if (method === "search_count") return 1;
    if (method === "search_read") return [item];
    if (method === "action_acknowledge") { acknowledged += 1; return true; }
    return true;
  };
});
afterEach(cleanup);

function renderInbox() {
  render(<ViewModeProvider><ExceptionsInbox /></ViewModeProvider>);
  return screen.findAllByText("Roster gap at Main Gate");
}

describe("ExceptionsInbox keyboard shortcuts", () => {
  it("acknowledges the selected exception with a plain 'a'", async () => {
    await renderInbox();
    fireEvent.keyDown(window, { key: "a" });
    await screen.findAllByText("Roster gap at Main Gate");
    expect(acknowledged).toBe(1);
  });

  it("ignores Ctrl+A / ⌘A (select all) instead of acknowledging", async () => {
    await renderInbox();
    fireEvent.keyDown(window, { key: "a", ctrlKey: true });
    fireEvent.keyDown(window, { key: "a", metaKey: true });
    expect(acknowledged).toBe(0);
  });
});
