# Run inside `odoo shell`: PAYLOAD_PATH=/tmp/payload.json APPLY=0|1 ... < apply_roster_pools.py
# Merges matched guards into contract-site and operational-site pools. Never removes members.
import json, os
from odoo import fields
payload = json.load(open(os.environ["PAYLOAD_PATH"]))
SRC = "DogForce Guard Roaster 21 Aug - 20 Sep 2026"
Emp = env["hr.employee"]
for cs_id, d in payload["sites"].items():
    cs = env["security.contract.site"].browse(int(cs_id))
    site = cs.site_id
    emps = Emp.browse(d["emp"]).exists().filtered(lambda e: e.active and e.security_guard)
    before = len(site.site_guard_pool_ids)
    cs.write({"contract_guard_pool_ids": [(4, e.id) for e in emps], "guard_pool_mode": "site_only"})
    site.write({"site_guard_pool_ids": [(4, e.id) for e in emps], "guard_pool_mode": "site_only",
                "guard_pool_source": SRC, "guard_pool_source_date": fields.Date.today()})
    body = "Regular guard pool imported from %s: %d guards (%d before). Unmatched, needs HR review: %s" % (
        SRC, len(emps), before, ", ".join(d["unmatched"]) or "none")
    if hasattr(site, "message_post"):
        site.message_post(body=body)
    print(cs_id, site.name, "pool", len(site.site_guard_pool_ids), "peak", site.peak_staffing_required,
          "warn", site.guard_pool_capacity_warning)
if os.environ.get("APPLY") == "1":
    env.cr.commit(); print("COMMITTED")
else:
    env.cr.rollback(); print("DRY RUN - rolled back")
