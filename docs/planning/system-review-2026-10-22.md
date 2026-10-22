# DogForce system review: rostering first (22 Oct 2026)

Status: review only. Nothing here is changed yet. Each item says what to fix, remove or improve, and the evidence checked.

## P0: fix now

1. **Gap-scan floods notifications.** `security_notifications/models/security_notifications.py` (`action_scan_roster_gaps`) creates one notification per unfilled slot, every 10 minutes. Evidence: 302 notifications in two days against about 460 open gaps. Fix: one notification per site per day, with a count.
2. **Smart recommendations never see gaps.** `security_ai_engine/models/security_smart_recommendation.py:115` searches `state = "unassigned"`, which does not exist (valid states: draft, assigned, cancelled). The search silently returns nothing. Fix: `employee_id = False` and `state = "draft"`.
3. **19 active sites have no regular guard pool.** They are skipped by the automatic rosters on purpose. Evidence: `generate` dry run, 19 skipped. This is a data gap, not a code bug. Owner: Winston and HR.

## P1: rostering correctness

4. **Rest-hour rule is not enforced within one run.** `action_auto_fill_slots` says so in its docstring. The 10-hour rest check looks only at slots already saved. Two shifts filled in the same run can break the rest rule, and the meeting was told the system respects 12-hour rest. Fix: check against slots assigned earlier in the same run.
5. **Two auto-assign paths.** `action_auto_assign_all` and `action_auto_fill_slots` in `security_shift_planner.py` implement rules separately. Not yet verified whether they agree on pools, caps and rest. Fix: one engine, the other removed.
6. **Batch still drives the old hub.** Rostering Hub loads batches; the new board uses the cycle grid. Fix: retire the batch dropdown once the board is approved (Winston's decision, 14 Oct).
7. **Access.** The Operations Supervisor login has no HR role, so it cannot see the roster menus. Decide the role for each person, and whether the account is shared.
8. **Merged duplicates still point to archived records.** 86 adoption rows still reference the 37 archived Shiwana records (`/root/backups/shiwana_merge_changelog.json`). Fix: repoint in a reviewed step, or leave as history.
9. **Manual-test sites are excluded by a setting.** `security.roster.manual_site_ids` (System Parameters). It is not documented on the screen. Fix: document it, and remove it once manual testing ends.

## P2: remove or tidy

10. **Legacy roster board** (`roster_board.js`, about 1,460 lines) duplicates the new board. Remove after approval.
11. **Two overlapping endpoints**: `get_attention_board` and `get_roster_cycle_grid`. Keep both, but state in each docstring which screen uses it.
12. **Namibia public holidays**: 2026 only (36 entries). 2027 must be loaded before January, or Sunday and holiday detection will be wrong.
13. **Stale claims.** My earlier updates to Wilbert overstated the roster board and the client sites page. They need a correction (already noted in chat).
14. **Tests not run in this review.** `security_operations/tests/test_site_guard_pool.py` exists; run it before the next release.

## Working well (checked)

- Slot states are consistent: 4,604 filled slots, all `assigned`. No shift is assigned to an inactive guard. No active duplicate guard names.
- The 21 Nov – 20 Dec cycle is generated automatically: 27 batches with slots, from the monthly job (`action_cron_auto_generate_next_month_batches`).
- Daily and monthly generators now roster only sites with a pool, and skip the manual-test sites.

## Not reviewed yet

- Attendance and posting console end-to-end on production (earlier review found and fixed several issues; not re-tested).
- Mobile guard check-in on a phone.
- Two-way site and contract sync (not started).
