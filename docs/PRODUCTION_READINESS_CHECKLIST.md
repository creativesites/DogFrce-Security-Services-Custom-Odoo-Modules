# DeployGuard — Production Readiness Checklist

Companion to [`PRODUCTION_READINESS_AUDIT.md`](PRODUCTION_READINESS_AUDIT.md). Work top to bottom. Nothing in **Section A** may be waived — each item is a confirmed defect, not a precaution.

Legend: `[ ]` open · `[~]` in progress · `[x]` done and verified by someone other than the implementer.

---

## A. Blockers — production use is unsafe until every box is ticked

### A1. Payroll and loan access control
- [ ] `security.payslip` ACL no longer grants `hr.group_hr_user` write/create/**unlink**
- [ ] Same for `security.payslip.earning.line`, `security.payslip.deduction.line`, `security.employee.loan`, `security.loan.deduction`
- [ ] A dedicated payroll group exists (preparer/approver split — see audit §7.1)
- [ ] `ir.rule` restricts non-payroll users to their own payslip (`employee_id.user_id == user`)
- [ ] `security.payslip` inherits `mail.thread`; state and monetary fields carry `tracking=True`
- [ ] **Verified by test:** a supervisor cannot read another employee's payslip
- [ ] **Verified by test:** a supervisor cannot delete any payslip

### A2. WhatsApp webhook authentication
- [ ] `/api/whatsapp/webhook` validates a shared secret or HMAC signature
- [ ] Endpoint is bound to the internal Docker network / not publicly routable
- [ ] `OWNER STATS` (and any financial aggregate) is unreachable without an authenticated, authorised sender
- [ ] Sender identity is not trusted from the request body alone
- [ ] **Verified:** an unauthenticated POST from outside the network is rejected

### A3. Credential exposure
- [ ] Database password rotated
- [ ] Odoo `admin_passwd` rotated
- [ ] Any API keys/tokens found in `CLAUDE.md`, `AGENTS.md`, `INSTALL.md`, `MOBILE_DEPLOYMENT_GUIDE.md`, `deploy/*.yml`, `.github/workflows/` rotated
- [ ] `odoo.conf` removed from git tracking; `odoo.conf.example` committed in its place
- [ ] `.gitignore` covers `odoo.conf`, `*.conf` with secrets, and any `.env` variants
- [ ] Config moved to environment variables or Docker secrets
- [ ] Decision recorded on git history: purge, or treat all historical values as permanently compromised

### A4. Mobile authentication
- [ ] PIN verification no longer accepts a client-computed hash as the credential
- [ ] Rate limiting and lockout on `/api/security/mobile/auth/pin`, keyed on employee **and** source IP
- [ ] Error responses are uniform (no employee-existence oracle)
- [ ] `su=True` is not used before authentication succeeds
- [ ] `cors="*"` narrowed on authentication routes
- [ ] TLS terminated in front of Odoo; `usesCleartextTraffic` removed from the mobile build
- [ ] Mobile app rebuilt and redistributed after the above

### A5. Demo module containment
- [ ] Confirmed whether `security_demo_site` is installed on production (`SELECT state FROM ir_module_module WHERE name='security_demo_site'`)
- [ ] If installed on production: uninstalled, and seeded demo `res.users` audited/removed
- [ ] `security.demo.panel_enabled` default flipped to opt-**in**
- [ ] `/web/login` override cannot ship to a production database
- [ ] Same check for `security_demo_data`, `security_demo_data_zm`, `security_demo_zambia_site`

---

## B. Financial integrity — required before payroll or invoices are trusted

- [ ] Payroll state transitions guarded (`action_mark_paid`, `action_reset_to_draft`, `action_close`, period `action_reset_to_draft`)
- [ ] `action_compute_from_sources` refuses to recompute `confirmed`/`paid` payslips
- [ ] Loan carry-forward is idempotent — keyed ledger entry, not `next_line.amount += carry`
- [ ] **Verified by test:** confirm → reset → confirm does not double the loan deduction
- [ ] UNIQUE constraint on `(period_id, employee_id)` for payslips
- [ ] Payroll and billing consume only **approved** attendance (`billing_approved` / `overtime_approved`)
- [ ] The 4 financially significant crons reviewed for idempotency:
  - [ ] Security: Auto-generate Monthly Invoices
  - [ ] Security: Monthly Leave Accrual
  - [ ] Security: Year-End Leave Carryover
  - [ ] Security: Auto-generate Next Month Roster Batches
- [ ] Duplicate-invoice protection verified across all three billing generation paths
- [ ] The 14 `except: pass` sites reviewed; none sits in a payroll or billing path

---

## C. Correctness

- [ ] Currency and statutory labels are company-driven, not hardcoded
- [ ] `whatsapp_bridge.py:666-673` no longer emits `ZMW` / `NAPSA/NHIMA` for a Namibian company
- [ ] `security_billing.py:1088` fallback currency reviewed
- [ ] Decision recorded: is this one product for two markets, or a Namibian deployment carrying Zambian residue?
- [ ] `security_notifications.py:72` no longer hardcodes `http://localhost:8069`
- [ ] `security_licensing` ships an `ir.model.access.csv` (its Owner nav leaf currently raises `AccessError`)

---

## D. Multi-company — required only if a second entity/branch will exist

- [ ] Decision recorded on whether DogForce will operate multiple companies
- [ ] If yes: `company_id` added across business models (currently 12 of 117)
- [ ] If yes: `ir.rule` company isolation on payroll, attendance, discipline, equipment, fleet, documents, billing
- [ ] Cross-company leakage tested with two companies and a user restricted to one

---

## E. Testing gates

- [ ] Permission test suite exists and runs in CI
- [ ] Payroll: generation, recompute, state transitions, loan interaction
- [ ] Billing: duplicate protection across all generation paths
- [ ] Roster: overlap, coverage, overnight and month-boundary shifts
- [ ] Attendance → payroll → billing chain covered end-to-end
- [ ] Integration tests for `/api/whatsapp/webhook` and the mobile auth endpoints
- [ ] `security_operations` (the operations core) has tests — currently none

---

## F. Deployment

- [ ] Production `odoo.conf` verified to carry `list_db = False` and a correct `dbfilter`
- [ ] `proxy_mode` correct behind the reverse proxy; HTTPS enforced
- [ ] Workers and cron threads sized for real load
- [ ] Resource limits applied to **all** stacks on the host, not only DogForce
- [ ] Community vs Enterprise cutover question resolved (see `KNOWN_ISSUES.md`)
- [ ] Monitoring and alerting on: container health, DB availability, cron failures, integration failures
- [ ] Log retention configured; logs verified free of credentials and payroll data

---

## G. Backup and recovery

- [ ] Nightly backup verified running and completing
- [ ] Filestore included and consistent with the DB snapshot
- [ ] Offsite (R2) sync verified
- [ ] Weekly throwaway-DB integrity test verified passing
- [ ] **Restore performed end-to-end into a scratch environment and documented** — a restore procedure that has never been executed is not a restore procedure
- [ ] Restore runbook written (currently only `backup-db.sh` exists; restore is manual)
- [ ] RPO/RTO agreed with DogForce and achievable by the above

---

## H. Upgrade safety

- [ ] `security_dogforce_data` post-init hook verified safe to re-run against a populated database
- [ ] No demo module can seed users or data into production
- [ ] `noupdate` flags audited across all data files (the password-overwrite class of defect)
- [ ] Module upgrade rehearsed against a **restored copy of production**, not a clean database
- [ ] Rollback plan written and tested

---

## I. Documentation

- [ ] `CLAUDE.md` corrected — it says Odoo 17; the codebase is Odoo 19
- [ ] `CLAUDE.md` server/database details corrected to reflect the actual production system
- [ ] All credentials removed from documentation
- [ ] Restore procedure documented
- [ ] `KNOWN_ISSUES.md` refreshed against this audit

---

## J. Sign-off

Production go-live requires named sign-off on each:

| Area | Owner | Date | Signature |
|---|---|---|---|
| Section A — blockers all closed | | | |
| Section B — financial integrity | | | |
| Section E — test gates green | | | |
| Section G — restore demonstrated | | | |
| Business acceptance (DogForce) | | | |

**Do not sign Section A on the basis that the system appears to work.** Every Section A item is a confirmed defect that a working system will not reveal on its own.
