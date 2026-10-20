# DogForce follow-up plan — after 14 Oct 2026 meeting

Status: DRAFT. Based on the highlights only. To be revised when the full transcript arrives.

## What was asked (highlights)

1. **Guard profile based on the Namibian setup.** Certifications are not important. What matters: can the guard read, speak English, speak Afrikaans, write, write neatly, and general smartness/suitability.
2. **Client sites and client contracts must stay in sync.** A change to a site must reflect in its contract, and ad-hoc changes (e.g. client asks for one extra guard) must be captured on the contract.
3. **Clean up the Client Sites page** so it looks and works like the Client Contract form.
4. **Roster board must not start empty** and must filter by more than a single batch: site, date range, client, status, guard, shift type, gaps only, relief only, etc. Needs a new way of showing the information.


## Meeting transcript (14 Oct) — decisions and actions

**Decisions**
- Rosters are generated automatically from next month. Managers review and approve, rather than building rosters by hand.
- The roster view filters by **site**, not by batch. It has to detect Sundays and public holidays (Namibian calendar).
- The roster view runs on 21st–20th monthly cycles: 21 Sep–20 Oct, 21 Oct–20 Nov, 21 Nov–20 Dec.
- Filters required: date, time, shift, month, year and site.

**Schedule error raised in the meeting (Windhoek Eye Institution)**
- Required: Monday–Friday **night only**; Saturday, Sunday and public holidays **24 hours**.
- Found: the day shift (06:00–18:00) was set on all seven days, for both Windhoek Eye Institution and Hochland Service Station.

**Done 14 Oct (production, reversible)**
- Corrected the day-shift setup at both sites to Saturday, Sunday and public holidays only. The night shift stays on all days. Previous values saved to `/root/backups/sched_before.csv` on the server.
- Existing rosters were **not** changed.

**Still open, needs approval**
- 5 guards are assigned to Monday–Friday day shifts at Windhoek Eye Institution from 14 Oct onward. Clearing those assignments would take guards off live shifts, so this has not been done.
- Decide whether to cancel and regenerate those slots, or leave them for the manager to fix by hand.

**Action items from the meeting**
- Wilbert: update the roster section to filter by site (full search and filter, with Namibian Sunday and public-holiday detection).
- Winston: fix the schedule setup (partly done above; the rosters still need correcting).
- Winston: the four "Monday day shift" items are covered by the correction above.

## Current state (from code)

| Area | What exists today | Gap |
|---|---|---|
| Guard skills | `hr.employee` has `security_language_ids`, `security_attribute_ids`, `security_certification_ids` (`security_base/models/hr_employee.py:15-29`). Master data in `security_base/models/security_master_data.py` (`security.language` line 42, `security.attribute` line 53). | No read/write/neatness rating; certifications are the main skill focus. Need a clear skills screen and a few structured fields. |
| Site ↔ contract | Contract activation **pushes** contract → operational site (`security_client_contract.py:371+`). Editing a site does **not** update its contract. | One-way only. Ad-hoc changes do not flow back. |
| Roster board | Loads slots by `batch_id` (`security_shift_planner/static/src/js/roster_board.js:241, 379`). | Needs cross-batch filtering, default "today/this week" view, and an empty-state that is useful, not blank. |
| Client Sites page | Operational workbench (`security_operations/static/src/xml/client_sites_workbench.xml`). Scrolling just fixed. | Visual redesign to match the contract form. |

## Proposed approach

### Phase 1 — Guard profile (small, low risk)
- Add to `hr.employee` (security_base): `can_read` (bool), `can_write` (bool), `writes_neatly` (selection: neat / average / poor), `english_level` and `afrikaans_level` (selection: none / basic / good / fluent), `smartness_rating` (1–5, supervisor-set), plus a free-text `skills_note`.
- Hide or de-emphasise certifications on the employee form; keep the data.
- Expose these fields on the roster board guard card (so a supervisor sees who can read/write when assigning).
- Optional filter: "minimum English / Afrikaans level" for a post that needs it.
- **Confirm first:** exact list of fields and scale wording from the transcript.

### Phase 2 — Two-way site ↔ contract sync
- Single source of truth decision needed: **the contract** owns requirements (posts, shifts, guard counts); the **site** owns location/contact data.
- On site save: write relevant changes back to the linked contract site (name, location, supervisor, contact), and flag contract requirement changes for review rather than silently overwriting.
- Ad-hoc requests: add a contract-level "Additional Requirement" line (date range, shift, guard count, reason, requested by, approved by) that auto-creates a roster slot for those dates and appears in the contract's history.
- **Confirm first:** should an ad-hoc change require approval before it hits the roster?

### Phase 3 — Client Sites page redesign
- Match the Client Contract form layout: header with status and key figures, tabs (Overview, Sites, Posts & Shifts, Guards, History), consistent cards.
- Keep the filter chips and search that exist.
- Fix any empty or broken states.

### Phase 4 — Roster board: filters and default view
- Replace batch-only loading with a query builder: site(s), client, date range (default: this week or next 7 days), shift type, status (gap / assigned / relief / confirmed), guard, supervisor.
- Default on open: the current week for the user's sites, not an empty board.
- Saved views (e.g. "Gaps this week", "Relief used", "Hochland night shifts").
- Summary strip: total slots, filled %, gaps, relief count.

## Order and rough effort

1. Phase 1 (guard profile): smallest, unblocks supervisors. ~1–2 days.
2. Phase 4 (roster board default and filters): highest operational value. ~3–4 days.
3. Phase 2 (site ↔ contract sync + ad-hoc requests): needs the decision on ownership first. ~3–5 days.
4. Phase 3 (Client Sites redesign): depends on Phase 2 data model. ~2–3 days.

## Decisions needed before building

1. Exact guard profile fields and rating scales (from transcript).
2. Who owns requirement changes: contract or site?
3. Do ad-hoc guard requests need approval? By whom?
4. Default roster view: "this week" or "today"?
5. Keep certifications visible at all, or hide them from the employee form?

## Joint Architecture Plan — Automated Rostering & Filter Evolution (Oct 20)

### The Core Architectural Problem
The original system was batch-centric:
- Every slot belonged to a `security.roster.batch`.
- Fairness checks (22 working days cap, max 1 Sunday) queried `batch_id`.
- The interactive Roster Board (`roster_board.js`) required picking a single batch from a dropdown before displaying any slots.

The recent update created `Roster Board (new)` with a 21st–20th cycle picker and site-by-day table, but stripped all operational capabilities (it became a non-interactive count matrix rather than a working roster board).

### The End-to-End Architectural Target
1. **Decouple Constraints from `batch_id`**: Update fairness algorithms to evaluate over the operational cycle date range (`shift_date >= d0 AND shift_date <= d1`) rather than `batch_id`.
2. **Unified Filter Engine**: Replace batch-only loading with a multi-parameter query engine supporting Cycle (21st–20th), Site, Client, Shift Template (Day/Night), Day Type (Weekday, Saturday, Sunday, Namibian Public Holiday), and Status (Gaps, Clashes, Relief, Filled).
3. **Dual-Layer Interactive UI**:
   - **Layer 1 (Macro Grid)**: Site-by-day high-density overview with cycle KPIs.
   - **Layer 2 (Micro Assignment Drawer)**: Clicking any cell opens the day's post/shift slots for that site, with guard allocation drawer, eligibility checks, conflict alerts, and quick assignment.
   - **Site Navigation**: Clicking a site name opens the full-cycle site roster view.
4. **Emergency Cycle Provisioning**:
   - The current cycle ends today (20 Oct). The 21 Oct – 20 Nov cycle has 0 slots.
   - Fix operational requirement ID 54 (Windhoek Eye) and generate the upcoming cycle slots immediately.

