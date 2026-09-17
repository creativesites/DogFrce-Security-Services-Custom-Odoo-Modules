# Rostering, Clients & Sites — Simplification and Workflow Plan

> Status: Active · Created 2026-09-17 · Owner: Winston
> Source: manager feedback (Wilbert, GM) — WhatsApp messages + voice note, 17 Sep 2026
> Related: [BUILD-STATUS-AND-PHASE-PLAN](deployguard/BUILD-STATUS-AND-PHASE-PLAN.md) · [ROSTER_WORLDCLASS_PLAN](ROSTER_WORLDCLASS_PLAN.md)

---

## 0. Credential handling — read first

The account list shared this morning contained **live production passwords for
four accounts on `dogforce_prod`**, including the Odoo superadmin. Those
passwords have now travelled through a chat client and at least one AI session.

**They must be treated as compromised and rotated today.** No password from that
list appears in this document, in the repository, or in any commit — and none
should. The *roles* from that list are used below; the secrets are not.

This is the same finding as S-1 in
[00-current-state.md](deployguard/00-current-state.md) §7, now with a second
exposure path. See §6.1.

---

## 1. What the manager actually said

Four separate inputs, which resolve into **seven distinct asks**:

| # | Ask | Source |
|---|---|---|
| **A1** | Operations Manager account needs admin rights — "based on how they operate" | message |
| **A2** | Client Site screen is cluttered — "let's clear it, all that stuff coming up… let it be **completely clear**" so front desk or ops can just set up a site | voice note |
| **A3** | Client → tender → sites hierarchy must be visible — "this site belongs to this tender, and that client's tender has all these related sites… when I click on Clients I should see all the sites, with all their requirements and all their shifts" | voice note |
| **A4** | Site list should be a **vertical layout**, not whatever it renders now — "I just want to see a layout of our sites arranged vertically. Because right now… I don't even know" | voice note |
| **A5** | **Delete permission** — "if I'm given the action buttons… right now when I try to delete requests, I can't. Maybe it's restricted only to the main admin" | voice note |
| **A6** | The **six-role roster approval chain** (see §3) | message |
| **A7** | Front desk validates daily posting **after** ops has posted and marked attendance; HR needs an **hours audit** (sharing/balancing of hours, equity) | messages |

Underneath all of it, one sentence from the founder's own framing:

> "They want to start rostering, but there is a cumbersome process before they
> can do that."

That is the real brief. Everything below serves it.

---

## 2. Why it feels cumbersome — the actual diagnosis

This was audited against the code, not guessed. Two structural problems.

### 2.1 The prerequisite chain is seven models deep

To generate one roster slot, this must exist first:

```
res.partner (Client)
  └─ security.client.site
       └─ security.post.type          ← separate config menu
            └─ security.post
                 └─ security.shift.template     ← separate config menu
                      └─ security.shift.requirement  (+ bill_rate, pay_rate)
                           └─ security.billing.plan  ← different module entirely
                                └─ security.roster.batch → generate
```

Seven models, spread across **three top-level menus** (Operations, Rostering,
Clients & Sites) plus Billing. The health-check wizard
(`security.roster.setup.wizard`) confirms this by what it tests for: sites with
no requirements, requirements with no template, zero bill rate, zero pay rate,
no billing plan, no shift templates at all. **Each of those is a wall a user can
hit before they are allowed to roster.** [verified in code]

### 2.2 There are five competing ways to do the same setup

| Entry point | Where | What it does |
|---|---|---|
| `security.client.onboarding.wizard` | Clients menu | **Full 5-step chain**: client → sites → requirements → billing → first roster |
| `security.site.setup.wizard` | "Quick Onboarding Wizard" button on the Site form | Overlapping subset: posts + site setup |
| Clients & Sites mega menu | Command Center overlay | 5 tabs of launcher cards into raw model lists |
| Site Hub | OWL single-page app | Another site management surface |
| Roster setup health check | Rostering menu | Tells you what's missing, doesn't fix it |

**The irony: a genuinely good end-to-end wizard already exists** — the 5-step
`security_client_onboarding` wizard does the whole chain including the first
roster. It is buried, and four other half-overlapping surfaces compete with it.

**So the fix is mostly subtraction and information architecture, not new
features.** That is good news for today.

### 2.3 What the "Call assist / Towing / Recovery" clutter actually is

Those strings are not on the site model. They are **launcher cards and tabs in
the Clients & Sites Command Center mega menu** (`clients_sites_mega_menu.xml` —
five tabs: Quick Launchpad, Clients & Contracts, Locations/Geofence/Posts,
Risk & Exclusions, Client SOP & Guidance), plus neighbouring menu entries from
`security_armed_response` (dispatch/callout) which was merged recently and is
not installed anywhere yet.

He clicks "Client Site" expecting a list of sites and gets a command center. A4
("arranged vertically") is him asking for **a list view, not a card grid**.

### 2.4 The approval chain doesn't exist in code

`security.roster.batch` has states `draft → generated → submitted → approved →
confirmed → cancelled` with exactly **one** approval step
(`submitted_by_id` / `approved_by_id`). The manager described **six roles in
sequence**. Today, roles 2–6 have nowhere to sign. [verified in code]

### 2.5 The delete problem is a group problem, not an ACL problem

`security_operations/security/ir.model.access.csv` already grants
`perm_unlink = 1` on every operations model — but to `hr.group_hr_user`. There
are **no ACL rows for the Security Manager / Owner groups at all**, and no
`unlink` override or `ondelete="restrict"` blocking deletes. [verified in code]

So Wilbert can't delete because **his account isn't in the group that holds the
right**, not because the right doesn't exist. A1 and A5 are the same fix.

---

## 3. The six-role roster workflow, as described

| Step | Role | Responsibility | Maps to |
|---|---|---|---|
| 1 | **Operations** | Drafts the roster | `draft` → `generated` |
| 2 | **Front Desk** | Cross-checks the roster; supervises supervisors on attendance | **new** `cross_checked` |
| 3 | **General Manager** (Wilbert) | Validates the roster | **new** `validated` |
| 4 | **HR** | Confirms the roster; payment processing, payroll | **new** `hr_confirmed` |
| 5 | **Finance** | Releases payments, audits | **new** `finance_released` |
| 6 | **Admin / Director** | Final oversight and approval | `approved` → `confirmed` |

Plus, separately from the monthly roster:

- **Daily posting validation (A7a):** ops posts attendance and marks it →
  **front desk validates it afterwards**. `security.attendance.batch` already
  has `draft → captured → reviewed → locked`; `reviewed` is the natural
  front-desk gate, but there is no front-desk role to own it and no enforcement
  that ops can't review their own posting.
- **HR hours audit (A7b):** hours per guard per period, with fairness/equity
  balancing. The scoring engine already has a `fairness_weight` on shift
  requirements and `security_shift_planner` has roster scoring — the data exists,
  the report does not.

> **Design note worth flagging:** six sequential approvals on a monthly roster is
> a lot of ceremony, and each added gate is a place the roster stops moving. I'd
> recommend steps 2–3 (front desk cross-check, GM validate) be **blocking**, and
> steps 4–6 (HR, Finance, Director) be **parallel sign-offs** on an already-live
> roster — guards get posted, while payroll and finance confirm in their own time.
> Sequential-everything means nobody gets rostered until the Director clicks a
> button. Raise this with Wilbert before building step 6 as a hard gate.

---

## 4. Today's plan

Ordered by impact-per-hour. Items 1–4 are the ones that make him feel the
difference immediately; 5–6 are structural; 7 is the desktop app track.

### Task 1 — Permissions: Operations Manager + delete rights · ~1h

- [ ] Add explicit ACL rows for `security_base.group_security_manager` and
      `group_security_owner` on all `security_operations` models, with
      `perm_unlink = 1` — stop relying on `hr.group_hr_user` as the de-facto
      admin group
- [ ] Grant the Operations Manager account Security Manager + HR/Payroll Officer
      groups (**not** `base.group_system` — admin-like capability through roles,
      not superuser; see §6.2)
- [ ] Verify the Delete action actually appears in the UI for that user on
      Client Sites, Posts, Shift Requirements and Roster Batches
- [ ] Add a record-rule check so deleting a site with live roster slots gives a
      clear message rather than a silent failure or a traceback

**Acceptance:** Wilbert's account can delete a test client site, a post and a
shift requirement, and gets a readable refusal when a record is genuinely in use.

### Task 2 — Client Site form: strip it to what a setup actually needs · ~2h

- [ ] Page 1 is only: site name, client, location, supervisor, sector, code.
      Nothing else above the fold
- [ ] Move coverage gauges, risk badges and contract status to the **list/kanban**
      where they belong — a setup form is not a dashboard
- [ ] Remove one of the two competing header buttons (keep Site Hub, retire the
      duplicate "Quick Onboarding Wizard" — the client onboarding wizard is the
      one true path, Task 3)
- [ ] Collapse five notebook pages to three: **Posts & Shifts**, **Location &
      Contacts**, **Notes & Exclusions**
- [ ] Geofence fields are optional and clearly marked as such — they must never
      block saving a site

**Acceptance:** a front-desk user creates a usable client site in under 60
seconds, entering six fields, with no scrolling past the fold.

### Task 3 — One way in: promote the onboarding wizard, demote the rest · ~2h

- [ ] Make "Set up a new client" (the 5-step wizard) the primary CTA on the
      Clients & Sites menu and the empty state of the sites list
- [ ] Cut the mega menu from five tabs of cards to **one clear panel**: Clients,
      Sites, Contracts, Requirements — four destinations, no launchpad
- [ ] Ensure the wizard can be exited and resumed — setup abandoned halfway must
      not lose the client and sites already created
- [ ] Seed **default shift templates** (Day 06:00–18:00, Night 18:00–06:00,
      12h, 8h) and **default post types** (Static Guard, Gate, Patrol, Control
      Room) so a brand-new site is rosterable without visiting a config menu
- [ ] Bill rate / pay rate of zero becomes a **warning**, not a wall — you can
      roster, you just get told billing is incomplete

**Acceptance:** from an empty database, a new client with one site and one shift
requirement reaches "generate roster" without opening a single configuration
menu.

### Task 4 — Client → tender → sites hierarchy, vertical · ~2h

- [ ] New default **list view for Client Sites**, grouped by Client — vertical,
      scannable, exactly as asked (A4). Kanban stays available, but is no longer
      what opens by default
- [ ] "Tender" made real: expose `security.client.contract` as the grouping
      level, so a contract covering several sites shows them all together, and
      each site shows which tender it belongs to
- [ ] Client (`res.partner`) form gains a **Sites** tab: every site for that
      client, with its posts, shift requirements and shifts inline — "when I
      click on Clients I should see all the sites, with all their requirements
      and all their shifts" (A3)
- [ ] Smart button on the client: site count → the filtered vertical site list

**Acceptance:** Wilbert opens a client and sees, on one screen, every site under
that client, which tender each belongs to, and the shifts each site requires.

### Task 5 — Roster approval chain (six roles) · ~3h · may spill to tomorrow

- [ ] New groups: `group_security_front_desk`, `group_security_finance`,
      `group_security_director` (HR officer and Manager already exist)
- [ ] Extend `security.roster.batch` states per §3, each with its own
      `*_by_id` / `*_at` stamp and a chatter entry
- [ ] Each transition button visible only to its group; no self-approval — the
      user who drafted cannot cross-check, the one who cross-checked cannot
      validate
- [ ] Rejection at any step returns the batch to the previous step with a
      mandatory reason, not to draft
- [ ] A status bar on the batch showing where it is in the chain and who it is
      waiting on
- [ ] Unit tests: full happy path, each rejection path, self-approval refusal

**Acceptance:** a roster drafted by Operations cannot reach Confirmed without
five distinct users acting, and the batch always shows who it is waiting on.

> Confirm the sequential-vs-parallel question in §3 with Wilbert before building
> steps 4–6 as hard gates.

### Task 6 — Front-desk daily validation + HR hours audit · ~2h · likely tomorrow

- [ ] Front-desk gate on `security.attendance.batch`: ops posts → `captured`;
      **front desk** moves `captured → reviewed`; ops cannot review its own
      posting
- [ ] HR hours audit view: hours per guard per period, with variance against the
      team average — the "sharing of hours / equity" ask (A7b)
- [ ] Flag outliers both ways: guards significantly over and significantly under
      the average

### Task 7 — Desktop app, Phase 2 (continues in parallel)

Per the phase plan, Phase 2 is the bridge addon. Today's slice:

- [ ] Confirm whether Aegis's `security_deployguard_bridge` work exists anywhere
      recoverable — it is marked Done on the cowork board but is in **no git ref**
      (see the phase plan §4.1). Decide: recover or rebuild
- [ ] If rebuilding: scaffold the addon (config singleton, integration group and
      user, encrypted secret storage) — no auth logic yet
- [ ] Surface today's roster workflow in the desktop app's My Work: a roster
      batch waiting on *your* signature is a task

---

## 5. Explicitly not today

| Deferred | Why |
|---|---|
| Rewriting the Site Hub OWL app | Task 2 + 3 may make it redundant; decide after |
| Automatic roster generation improvements | The complaint is setup friction, not generation quality |
| Billing/finance integration for step 5 | Needs the approval chain to exist first |
| Installing `security_armed_response` / `security_telephony` | Not installed anywhere; adding menus now makes A2 worse |
| Mobile app changes | Not in this feedback |

---

## 6. Non-negotiables carried into this work

### 6.1 Credential rotation — today

- [ ] Rotate all four production account passwords from the shared list, plus
      the Odoo master password
- [ ] Rotate the Render PostgreSQL password (still committed in `odoo.conf`)
- [ ] Remove `odoo.conf` from the repo and the Docker image; template it
- [ ] Purge credentials from `CLAUDE.md` and the other docs listing them
- [ ] Agree a channel for sharing credentials that is not chat — a password
      manager, shared vault, or nothing

### 6.2 "Admin rights" means the right role, not superuser

A1 asks for the Operations Manager to have admin rights. The correct
implementation is **Security Manager + HR/Payroll Officer groups with explicit
unlink permissions** (Task 1) — not `base.group_system`.

Reasons: `base.group_system` exposes the technical menus, the ability to edit
views and fields live, and — per the bridge design in
[DG-ADR-007](deployguard/adr/DG-ADR-007-authentication.md) — is explicitly
refused SSO tickets. Handing it out casually makes the audit trail meaningless
and breaks the future single-sign-on path.

If, after Task 1, something he needs is still blocked, the answer is to add that
specific permission to the Manager role — not to escalate the account. Every such
addition gets recorded here.

### 6.3 Every change ships with its test and its migration

These are live production models with real data behind them. View simplification
is safe; state-machine changes (Task 5) and ACL changes (Task 1) are not.
Both need tests, and Task 5 needs a migration for existing batches in flight.

### 6.4 Test on staging — which does not exist yet

There is currently **no reachable staging environment** (phase plan §4.4). Until
there is, Task 5's state-machine change should not touch production. Tasks 1–4
are view/ACL changes that can be validated on a local stack first.

---

## 7. Change log

| Date | Change |
|---|---|
| 2026-09-17 | Created from manager feedback. Root-cause audit of the setup chain; seven asks mapped to seven tasks. |
