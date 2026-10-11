# Run inside `odoo shell` AFTER apply_roster_pools.py: APPLY=0|1 PAYLOAD_PATH=... < generate_cycle_rosters.py
# For each contract site that received an imported regular pool: reset the batch's pool snapshot to the
# site defaults (snapshots made before the import were empty), then auto-fill that batch only.
# Left for manual testing on purpose: contract sites 8 Hochland S S, 30 Petrofund, 24 Windhoek Eye Clinic.
# Skipped: 40 Atta Rentals (batch already confirmed).
import json, os
payload = json.load(open(os.environ["PAYLOAD_PATH"]))
MANUAL, SKIP = {8, 30, 24}, {40}
Batch = env["security.roster.batch"]
tot = ass = 0
for cs_id in map(int, payload["sites"]):
    if cs_id in MANUAL | SKIP:
        continue
    site = env["security.contract.site"].browse(cs_id).site_id
    b = Batch.search([("site_id", "=", site.id), ("date_from", "=", "2026-09-21"), ("state", "!=", "cancelled")], limit=1)
    if not b:
        print("NO BATCH", site.name); continue
    b._get_effective_site_pool(site)
    b.roster_site_pool_ids.filtered(lambda p: p.site_id == site).action_reset_to_site_defaults()
    if not b.slot_ids:
        b.action_generate_slots()
    b.action_auto_fill_slots()
    sl = b.slot_ids.filtered(lambda s: s.state != "cancelled")
    pool = set(site.site_guard_pool_ids.ids)
    out = len(sl.filtered(lambda s: s.employee_id and s.employee_id.id not in pool))
    n_ass = len(sl.filtered("employee_id")); tot += len(sl); ass += n_ass
    print("%-45s pool %2d slots %3d assigned %3d gaps %3d outside_pool %d relief %d" % (
        site.name[:45], len(pool), len(sl), n_ass, len(sl.filtered("critical_gap")), out, len(sl.filtered("is_relief"))))
print("TOTAL", ass, "/", tot)
if os.environ.get("APPLY") == "1":
    env.cr.commit(); print("COMMITTED")
else:
    env.cr.rollback(); print("DRY RUN - rolled back")
