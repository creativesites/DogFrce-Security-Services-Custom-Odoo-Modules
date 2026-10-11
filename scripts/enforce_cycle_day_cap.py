# Run in `odoo shell`: APPLY=0|1 CAP=21 LOG_PATH=... < enforce_cycle_day_cap.py
# 1) sets security.max_working_days_per_cycle  2) unassigns slots beyond each guard's CAP-th working day in the
# 21 Sep cycle (generated batches only; confirmed batches untouched)  3) refills affected batches from site pools.
import json, os
CAP = int(os.environ.get("CAP", "21"))
DATE_FROM = "2026-09-21"
MANUAL_TEST_SITES = (4200, 4250, 4246)  # Hochland, Petrofund, Windhoek Eye Clinic: left untouched
env["ir.config_parameter"].sudo().set_param("security.max_working_days_per_cycle", str(CAP))
Batch, Slot = env["security.roster.batch"], env["security.roster.slot"]
all_slots = Slot.search([("batch_id.date_from", "=", DATE_FROM), ("batch_id.state", "!=", "cancelled"),
                         ("employee_id", "!=", False), ("state", "!=", "cancelled")])
by_emp = {}
for s in all_slots:
    by_emp.setdefault(s.employee_id.id, {}).setdefault(s.shift_date, []).append(s)
log = {"cap": CAP, "unassigned": [], "affected_batches": []}
affected = set()
for emp_id, days in by_emp.items():
    ordered = sorted(days)
    for d in ordered[CAP:]:
        for s in days[d]:
            if s.batch_id.state != "generated" or s.site_id.id in MANUAL_TEST_SITES:
                continue
            log["unassigned"].append({"slot": s.id, "employee": emp_id, "date": str(d), "batch": s.batch_id.id, "site": s.site_id.name})
            s.write({"employee_id": False, "state": "draft"})
            affected.add(s.batch_id.id)
print("guards over cap:", sum(1 for d in by_emp.values() if len(d) > CAP), "slots unassigned:", len(log["unassigned"]))
for b in Batch.browse(sorted(affected)):
    b.action_auto_fill_slots()
    sl = b.slot_ids.filtered(lambda x: x.state != "cancelled")
    log["affected_batches"].append(b.id)
    print("%-45s assigned %3d / %3d gaps %3d" % (b.site_id.name[:45], len(sl.filtered("employee_id")), len(sl), len(sl.filtered("critical_gap"))))
# verify
chk = {}
for s in Slot.search([("batch_id.date_from", "=", DATE_FROM), ("batch_id.state", "!=", "cancelled"), ("employee_id", "!=", False), ("state", "!=", "cancelled")]):
    chk.setdefault(s.employee_id.id, set()).add(s.shift_date)
print("MAX days any guard now:", max(len(v) for v in chk.values()), "guards over cap:", sum(1 for v in chk.values() if len(v) > CAP))
json.dump(log, open(os.environ.get("LOG_PATH", "/tmp/daycap_changelog.json"), "w"))
if os.environ.get("APPLY") == "1":
    env.cr.commit(); print("COMMITTED")
else:
    env.cr.rollback(); print("DRY RUN - rolled back")
