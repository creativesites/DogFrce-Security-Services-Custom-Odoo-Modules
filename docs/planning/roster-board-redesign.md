# Roster board redesign: from batches to filters

Status: DRAFT for review (Guard roster session + DogForce Odoo session). Nothing here is built or deployed yet.

## Why
- The old board only works per batch. A batch is one site for one period, so a manager must pick a batch before seeing anything.
- Rostering is now automatic. People verify, correct and fill gaps. The screen must start from "what needs fixing", not from an empty batch picker.
- Winston's words: "not just superficial work". The data access has to change, not only the layout.

## What exists today (checked in code and on production)
- Roster slots (`security.roster.slot`) belong to a batch and carry a site, client, post, shift template, date, guard and status.
- Batches are still the entry point for the hub (`rostering_hub.js` loads batches, then the slots of one batch).
- Two new server endpoints exist on production:
  - `get_attention_board`: cycle totals plus sites needing action, worst first (paged).
  - `get_roster_cycle_grid`: sites as rows, days of the 21st to 20th cycle as columns, with filters for site, shift, day type, status and search.
- The new Roster Board (new) screen uses the grid. It has not been checked in a browser.
- Public holidays (Namibia) are in `security.public.holiday`. 2026 is loaded. 2027 is not.

## Target behaviour
1. Open on the current 21st–20th cycle, all sites, unfilled first. No batch needed.
2. Filters work together: site(s), client, cycle or date range, shift template, day type (Mon–Fri / Sat / Sun / public holiday, detected automatically), status (unfilled / clash / relief / confirmed), guard, supervisor.
3. Summary strip: unfilled shifts, sites needing action, clashes, guards over the day cap, Sunday and public-holiday gaps.
4. Click a cell or site: open the day or the site's shifts, assign, swap, clear, see the guard's other shifts that day.
5. Batches stay as the audit record, but are no longer how people navigate.

## Work items
1. Grid data (done, untested in browser): `get_roster_cycle_grid`.
2. Day detail: `get_slots_for_day(site_id, date)` returning slots, guards available and reasons.
3. Assign / clear / swap through the existing guard-eligibility checks (`action_manual_assign`), not new code paths.
4. Relief and exclusion warnings shown in the same panel.
5. Saved views (e.g. "Gaps this week", "Windhoek Eye nights").
6. Retire the batch dropdown from the hub once the new board is approved.

## Decisions needed (Winston)
- Who sees what: the six office staff, plus supervisors on their own sites?
- Default scope: all sites, or sites the user supervises?
- Keep the old hub and legacy board until the new one is approved (agreed earlier).

## Verification before any production use
- Run the grid and day-detail methods read-only in an Odoo shell, rolled back, against production data.
- Check the screen in a browser as an office user (Winston must do this or give access).
- Winston approves each production deploy.
