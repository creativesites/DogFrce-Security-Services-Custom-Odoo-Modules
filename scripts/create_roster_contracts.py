# Run in `odoo shell`: PAYLOAD_PATH=payload3.json APPLY=0|1 LOG_PATH=... < create_roster_contracts.py
# Creates contracts/sites/posts/shift requirements for roster sections that had no contract in Odoo.
# COMMERCIAL TERMS (rates, monthly value, end date, billing contact) are NOT invented: left blank/0 for the
# manager to complete. Everything created is listed in the change log so it can be reversed.
import json, os
from odoo import fields
P = json.load(open(os.environ["PAYLOAD_PATH"]))
NIGHT, DAY, POST_TYPE = 5, 4, 12
ALL = dict(monday=True, tuesday=True, wednesday=True, thursday=True, friday=True, saturday=True, sunday=True, public_holiday=True)
SUN_PH = dict(monday=False, tuesday=False, wednesday=False, thursday=False, friday=False, saturday=False, sunday=True, public_holiday=True)
# (tag, contract name, partner (id or name to create), [(site name, location, service)])  service: 24h | night_sun_ph
SPECS = [
    ("emerincia", "Emerincia Plot", "Emerincia Plot", [("Emerincia Plot", "Windhoek", "24h")]),
    ("unigas", "Unigas", 4637, [("Unigas", "Windhoek", "night_sun_ph")]),
    ("newera_ho", "New Era", "New Era", [("New Era Head Office, Warehouse & Shop", "Windhoek", "24h")]),
    ("newera_hosp", "New Era", "New Era", [("New Era Central Hospital & State House", "Windhoek", "night_sun_ph")]),
    ("scrap_south", "Scrap Southern", "SCRAP_PARTNER", [("Scrap Salvage - Southern", "Windhoek", "night_sun_ph")]),
]
Partner, Contract, Emp = env["res.partner"], env["security.client.contract"], env["hr.employee"]
log = {"run": str(fields.Datetime.now()), "created": [], "notes": []}
contracts = {}
scrap_partner = env["security.client.contract"].browse(24).partner_id.id
for tag, cname, pspec, sites in SPECS:
    if pspec == "SCRAP_PARTNER":
        pspec = scrap_partner
    if isinstance(pspec, str):
        partner = Partner.search([("name", "=", pspec), ("is_company", "=", True)], limit=1)
        if not partner:
            partner = Partner.create({"name": pspec, "is_company": True})
            log["created"].append(["res.partner", partner.id, pspec])
    else:
        partner = Partner.browse(pspec)
    key = (cname, partner.id)
    c = contracts.get(key)
    if not c:
        c = Contract.create({"name": cname, "partner_id": partner.id, "date_start": "2026-09-21", "state": "draft",
            "note": "Created %s from the DogForce guard roster (21 Sep-20 Oct 2026). Rates, monthly value, end date "
                    "and billing terms were NOT supplied - manager to complete." % fields.Date.today()})
        contracts[key] = c
        log["created"].append(["security.client.contract", c.id, cname])
    for sname, loc, svc in sites:
        cs = env["security.contract.site"].create({"contract_id": c.id, "name": sname, "location": loc, "site_type": "other"
            if False else env["security.contract.site"]._fields["site_type"].selection[0][0]})
        post = env["security.contract.post"].create({"contract_id": c.id, "contract_site_id": cs.id, "name": "Main Guarding Post",
            "post_type_id": POST_TYPE, "required_guard_count": 1})
        reqs = [(NIGHT, ALL), (DAY, ALL if svc == "24h" else SUN_PH)]
        for tmpl, days in reqs:
            r = env["security.contract.shift.requirement"].create(dict(contract_id=c.id, contract_site_id=cs.id,
                contract_post_id=post.id, shift_template_id=tmpl, guard_count=1, **days))
            log["created"].append(["security.contract.shift.requirement", r.id, "%s tmpl %s" % (sname, tmpl)])
        emps = Emp.browse(P[tag]["emp"]).exists().filtered(lambda e: e.active and e.security_guard)
        cs.write({"contract_guard_pool_ids": [(6, 0, emps.ids)], "guard_pool_mode": "site_only"})
        log["created"] += [["security.contract.site", cs.id, sname], ["security.contract.post", post.id, sname]]
        log["notes"].append({"site": sname, "service": svc, "pool": emps.mapped("name"), "unmatched_names": P[tag]["unmatched"],
                             "sheet_needed": P[tag]["needed"], "sheet_allocated": P[tag]["allocated"]})
for c in contracts.values():
    c.action_activate()
    log["created"].append(["activated", c.id, c.name])
    for cs in c.contract_site_ids:
        if cs.site_id:
            cs.site_id.write({"guard_pool_source": "DogForce Guard Roaster 21 Aug - 20 Sep 2026", "guard_pool_source_date": fields.Date.today()})
            log["created"].append(["security.client.site", cs.site_id.id, cs.site_id.name])
json.dump(log, open(os.environ.get("LOG_PATH", "/tmp/contracts_changelog.json"), "w"), indent=1)
print(json.dumps(log["notes"], indent=1)[:1500])
for c in contracts.values():
    for b in env["security.roster.batch"].search([("site_id.contract_id", "=", c.id)]):
        print("BATCH", b.site_id.name, len(b.slot_ids), "assigned", len(b.slot_ids.filtered("employee_id")))
if os.environ.get("APPLY") == "1":
    env.cr.commit(); print("COMMITTED")
else:
    env.cr.rollback(); print("DRY RUN - rolled back")
