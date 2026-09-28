# DogForce roles and the attendance → payment pipeline

Source: DogForce's *User Roles & Responsibilities Matrix* (supplied by the
founder, 2026-09-28; revised the same day to add roster approval, and to give
the GM and MD full access). This is the operational model DeployGuard's first V2
slice is built on. **No credentials belong in this file or anywhere in the
repository.**

## The six users

| # | Role | Responsibilities | Odoo group (existing) |
|---|---|---|---|
| 1 | Operations Supervisor | Draft the roster; **register attendance**; exchange/swap guards | `security_base.group_security_supervisor` |
| 2 | Admin | **Confirm attendance** | `security_operations.group_security_front_desk` |
| 3 | HR | **Verify attendance**; payroll audit & inspection; **roster approval** | `security_base.group_security_hr_payroll_officer` |
| 4 | General Manager | Approve payroll; final inspection & analysis; **roster approval**; **full access** | `security_base.group_security_manager` |
| 5 | Finance | Financial audit for payment; approve payment; present to MD | `security_operations.group_security_finance` |
| 6 | Managing Director (owner) | Overall oversight and final authority | `security_base.group_security_owner` |

Users 1–3 and 5 are the four daily DeployGuard desktop users. The GM (4) and MD (6)
are the manager and owner audiences.

## Access decisions (2026-09-28)

- **Roster approval is HR's and the GM's** (and the owner's, whose group
  implies manager). `security.roster.batch.action_approve` / `action_reject`
  enforce this. Before, anyone who could open a roster could approve it.
- **The GM and the MD both have full access.** Every DeployGuard screen treats
  the manager group like the owner: Owner Overview, Team Today, Adoption's team
  view, Exceptions triage, problem reports, and guidance insights. In the ERP
  itself the owner group implies manager, but not the other way round. **On
  production, give Wilbert's user the "Security Owner" group as well** (Settings
  → Users → Wilbert → Access Rights) so he has the same ERP-wide access as
  Kuume. That is a configuration change on the server, not code.

## The sequential flow

```
Roster (1) ─► Register attendance (1) ─► Confirm (2) ─► Verify (3)
          ─► Payroll audit (3) ─► Payroll approval (4) ─► Financial audit
          & payment approval (5) ─► MD oversight (6)
```

Each step depends on the previous person having done theirs. If one person
doesn't use the system, everyone after them is blocked, and today the only way
to find out is to ask around. **That is the problem DeployGuard solves first.**

## How the first slice maps onto Odoo

The attendance part of the pipeline already exists as the
`security.attendance.batch` state machine (one batch per site per day,
generated from the roster):

| Pipeline step | Who | Batch state reached | DeployGuard task completes when |
|---|---|---|---|
| Register attendance | Operations Supervisor | `draft → captured` | batch is `captured` |
| Confirm attendance | Admin | `captured → reviewed` | batch is `reviewed` |
| Verify attendance | HR | `reviewed → locked` | batch is `locked` |

DeployGuard generates one task per **rostered site-day** for each step owner
(`security.work.responsibility`). A downstream task shows *"waiting for
<previous step>"* until its input is ready. The GM sees on **Team Today**
exactly where each site's attendance is stuck and with whom.

Roster approval (3/4), payroll approval (4) and payment (5) are the next slices. They follow the same
pattern once the attendance steps are proven.
