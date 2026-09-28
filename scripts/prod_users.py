# Odoo shell script: create or update DogForce staff logins.
# Run it through scripts/prod_users.sh, which passes the rows in DG_USERS.
# Every output line meant for the operator starts with "DG|".
#
# DG_USERS: one row per line, "role|Full Name|login[|replaces=old_login]"
#   role: ops, admin, hr, finance, manager, owner
#   replaces=old_login: move old_login's employee record to this user and
#   archive old_login (for someone moving to a new login).
# DG_ADD_OWNER: optional login that also gets the Owner group.
#
# All rows are validated first, and nothing is saved unless every row works.
# Temporary passwords are printed once and never stored.
import os
import secrets
import string

ROLE_GROUPS = {
    "ops": ["security_base.group_security_supervisor"],
    "admin": ["security_operations.group_security_front_desk"],
    "hr": ["security_base.group_security_hr_payroll_officer"],
    "finance": ["security_operations.group_security_finance"],
    "manager": ["security_base.group_security_manager"],
    "owner": ["security_base.group_security_owner"],
}
ROLE_LABEL = {
    "ops": "Operations Supervisor", "admin": "Admin", "hr": "HR",
    "finance": "Finance", "manager": "General Manager", "owner": "Managing Director",
}


def dg(msg=""):
    print("DG|" + msg)


rows, errors = [], []
for n, line in enumerate(os.environ.get("DG_USERS", "").splitlines(), 1):
    line = line.strip()
    if not line:
        continue
    parts = [p.strip() for p in line.split("|")]
    role, name, login = (parts + ["", "", ""])[:3]
    login = login.lower()
    replaces = ""
    for extra in parts[3:]:
        if extra.startswith("replaces="):
            replaces = extra.split("=", 1)[1].strip().lower()
    if role not in ROLE_GROUPS:
        errors.append("row %d: role '%s' must be one of %s" % (n, role, ", ".join(ROLE_GROUPS)))
    if len(name) < 2:
        errors.append("row %d: missing full name" % n)
    if "@" not in login:
        errors.append("row %d: '%s' is not an email login" % (n, login))
    if replaces == login:
        errors.append("row %d: replaces= must be a different login" % n)
    rows.append((role, name, login, replaces))

logins = [r[2] for r in rows]
if len(set(logins)) != len(logins):
    errors.append("the same login appears twice")
if not rows:
    errors.append("no users given")
Users = env["res.users"].with_context(no_reset_password=True, active_test=False)
for role, name, login, replaces in rows:
    if replaces and not Users.search([("login", "=", replaces)], limit=1):
        errors.append("replaces=%s: no such user" % replaces)

if errors:
    for e in errors:
        dg("ERROR " + e)
    dg("STOPPED. Nothing was changed.")
else:
    Employees = env["hr.employee"].with_context(active_test=False)
    alphabet = string.ascii_letters + string.digits
    results = []
    try:
        for role, name, login, replaces in rows:
            password = "".join(secrets.choice(alphabet) for _ in range(12))
            group_ids = [env.ref("base.group_user").id] + [env.ref(x).id for x in ROLE_GROUPS[role]]
            user = Users.search([("login", "=", login)], limit=1)
            vals = {"name": name, "login": login, "email": login, "password": password, "active": True}
            if user:
                user.write(vals)
                action = "updated"
            else:
                user = Users.create(vals)
                action = "created"
            user.write({"group_ids": [(4, g) for g in group_ids]})

            # Work tasks find their owner through the employee record.
            emp = Employees.search([("user_id", "=", user.id)], limit=1)
            note = ""
            if replaces:
                old = Users.search([("login", "=", replaces)], limit=1)
                old_emp = Employees.search([("user_id", "=", old.id)], limit=1)
                if not emp and old_emp:
                    emp = old_emp
                old.write({"active": False})
                note = ", archived %s" % replaces
            if not emp:
                emp = Employees.search([("work_email", "=ilike", login), ("user_id", "=", False)], limit=1) \
                    or Employees.search([("name", "=ilike", name), ("user_id", "=", False)], limit=1)
            if emp:
                emp.write({"user_id": user.id, "work_email": login, "active": True})
            else:
                emp = Employees.create({"name": name, "user_id": user.id, "work_email": login,
                                        "job_title": ROLE_LABEL[role]})
            results.append((ROLE_LABEL[role], name, login, password, "%s, employee #%s%s" % (action, emp.id, note)))

        owner_msg = ""
        add_owner = os.environ.get("DG_ADD_OWNER", "").strip().lower()
        if add_owner:
            extra = Users.search([("login", "=", add_owner)], limit=1)
            if extra:
                extra.write({"group_ids": [(4, env.ref("security_base.group_security_owner").id)]})
                owner_msg = "Owner access added for %s" % add_owner
            else:
                owner_msg = "Owner access NOT added: no user %s" % add_owner
        env.cr.commit()
    except Exception as exc:
        env.cr.rollback()
        dg("ERROR %s: %s" % (type(exc).__name__, exc))
        dg("STOPPED. Nothing was changed.")
    else:
        dg("=" * 100)
        dg("%-20s %-24s %-38s %s" % ("ROLE", "NAME", "LOGIN", "TEMPORARY PASSWORD"))
        dg("-" * 100)
        for role, name, login, password, note in results:
            dg("%-20s %-24s %-38s %s   (%s)" % (role, name, login, password, note))
        if owner_msg:
            dg("-" * 100)
            dg(owner_msg)
        dg("=" * 100)
        dg("Saved. Send each password privately; ask them to change it on first login.")
