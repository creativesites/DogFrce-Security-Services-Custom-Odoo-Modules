# 04 — Information Architecture

> Status: Draft · Owner: Product + UX
>
> The Platform shell is a React port of `security_shell` (rail + nav panel + canvas, ⌘K palette, profile card, loading bar). See [05-ux-principles](05-ux-principles.md) and [DG-ADR-017](adr/DG-ADR-017-design-system-and-shell-parity.md). This document defines **what** lives where; 05 defines **how it looks and behaves**.

---

## 1. Shell structure

```
┌──────┬───────────────────┬────────────────────────────────────────────┐
│ RAIL │ NAV PANEL         │ CANVAS                                     │
│ (dark│ (section tree for │  page header (title, context, actions)     │
│  ink)│  the active rail  │  ─────────────────────────────────────────  │
│      │  item; collapsible│  content                                   │
│ Home │  like security_   │                                            │
│ Work │  shell)           │                                            │
│ Learn│                   │                                            │
│ Team │                   │                                            │
│ Inbox│                   │                                            │
│ Insig│                   │                                            │
│ Help │                   │                                            │
│ ···  │                   │                                            │
│ ◉ me │                   │                                            │
└──────┴───────────────────┴────────────────────────────────────────────┘
```

- **Rail** items are role-filtered. Items a tenant hasn't enabled render with the `NOT INSTALLED` chip treatment; planned items render `SOON`. Both are non-clickable and visually identical, as in `security_shell` ([design system §3.2](../DEPLOYGUARD_DESIGN_SYSTEM.md)).
- **Nav panel** is driven by a typed catalogue (`nav_catalog` equivalent in `packages/app`), with leaf flags `soon`, `roles`, `countKey` (live count pill).
- **⌘K / Ctrl+K command palette**: navigate, search people/sites/courses/tasks, run quick actions ("Start site visit checklist", "Report a problem").
- **Profile card** (rail avatar): identity, roles and scopes, device, notification preferences, sign out.
- **Global loading bar** reflects in-flight API requests; **offline banner** sits at the top of the canvas when disconnected.
- **"Open in Odoo"** actions launch a separate Odoo window (desktop) or tab (web). Odoo is never iframed inside the canvas ([17](17-desktop-architecture.md) §6).

## 2. Top-level sections

| Rail item | Purpose | Roles (MVP) |
|---|---|---|
| **Home** | "What do I need to do now?" (employee) or "Today" (manager variant) | All |
| **Work** | My tasks, checklists, verify queue, templates (managers) | Supervisor, Ops Officer, Ops Manager, HR |
| **Learn** | My training, catalogue, assignments, authoring (admins) | All desktop roles |
| **Team** | People, sites, competency/training status of my scope | Supervisor, Ops Officer, Ops Manager, HR |
| **Inbox** | Exceptions and escalations needing attention | Supervisor, Ops Officer, Ops Manager, HR |
| **Insights** | Adoption, analytics, executive overview, briefs | Ops Manager, Owner, HR (training) |
| **Help** | Knowledge base, my support requests, report a problem | All |
| **Admin** (`···`) | Tenant settings, roles, Odoo connection, rules, notification policies, audit | Tenant Admin (+ read for Ops Manager) |

## 3. Navigation trees per role

### 3.1 Site Supervisor

```
Home
Work
  ├─ My work              (count pill: due today)
  ├─ Checklists
  └─ Verify               (count pill: awaiting my verification)
Learn
  ├─ My training
  └─ Assign to my team
Team
  ├─ My guards            (training + competency status, Odoo profile link)
  └─ My sites             (coverage from Odoo, open exceptions, checklists)
Inbox                     (scoped to my sites/team)
Help
  ├─ Knowledge base
  ├─ My requests
  └─ Report a problem
```

### 3.2 Operations Officer

Same as Supervisor, with **Team → Sites** scoped to region, and **Work → Client requests** (template-based task list).

### 3.3 Operations Manager

```
Home (Today)              operations overview: coverage, critical exceptions, overdue work, adoption headline
Inbox
  ├─ Critical
  ├─ Attention
  ├─ Watch
  └─ Resolved (7 days)
Work
  ├─ All work             (filter: site, supervisor, status, template)
  ├─ Verify
  └─ Templates & recurrence
Team
  ├─ People
  ├─ Sites
  └─ Supervisors          (per-supervisor adoption and work health)
Learn
  ├─ Assignments & compliance
  ├─ Catalogue
  └─ My training
Insights
  ├─ Adoption             (company → site → supervisor → person drill-down)
  ├─ Workflow health      (per workflow coverage, friction, abandonment)
  └─ Reports
Help
Admin ··· (read)
```

### 3.4 HR / Admin

```
Home
People
  ├─ Directory & provisioning   (import from Odoo employees, identity mapping)
  ├─ Onboarding programs
  └─ Certifications (from Odoo, read-only) & competencies
Learn
  ├─ Catalogue & authoring
  ├─ Assignments & compliance
  ├─ Question banks
  └─ Review queue         (drafts awaiting approval, incl. AI drafts in V2)
Inbox                     (people category: overdue training, access problems, "my info is wrong")
Help
  └─ Support queue (people category)
```

### 3.5 Owner (web)

```
Overview                  health tiles: operations, staffing (Odoo), compliance, training, adoption, incidents, client issues
Briefs                    weekly digest archive (MVP) → AI briefs with citations (V1)
Risks & exceptions        critical and aging exceptions only
Adoption                  company + site trend
People & capability       training compliance, competency gaps (V1)
```

### 3.6 Tenant Admin (web, `Admin`)

```
Organisation              name, locale, currency, branding (font from theme), working calendar
Sites & teams             synced from Odoo sites; team definitions
Roles & access            role assignments, scopes, custom roles
Reporting lines
Integrations
  ├─ Odoo connection      (URL, integration user, API key, webhook secret, health, lag)
  ├─ Identity mapping
  └─ Sync log
Rules
  ├─ Exception rules      (enable, thresholds, owners, escalation policies)
  ├─ Expected work        (workflow expectations per role)
  └─ Notification policies
Content                   templates, courses (publish rights)
AI (V1)                   provider, capabilities on/off, budgets
Devices & sessions
Audit log
```

## 4. Screen inventory (MVP)

| ID | Screen | Roles | Primary data | Key actions |
|---|---|---|---|---|
| SCR-001 | Sign in / MFA / device registration | All | — | Sign in, enrol MFA, trust device |
| SCR-002 | Home (employee) | Desktop roles | Shift, due/overdue work, training, acknowledgements | Open item, get help |
| SCR-003 | Home — Today (manager) | Ops Manager | Coverage, critical exceptions, overdue work, adoption headline | Open inbox item, drill down |
| SCR-010 | My work list | Work roles | Tasks, checklist instances | Filter, open, complete |
| SCR-011 | Checklist runner | Work roles | Checklist instance, items, evidence | Answer, attach, submit, couldn't complete |
| SCR-012 | Task detail | Work roles | Task, comments, attachments, linked Odoo record | Comment, complete, open in Odoo |
| SCR-013 | Verify queue | Supervisor+, Ops Manager | Submitted instances | Approve, reject with reason |
| SCR-014 | Templates & recurrence | Ops Manager, Tenant Admin | Templates, schedules | Create, version, publish |
| SCR-020 | My training | All | Assignments, progress | Start/resume |
| SCR-021 | Lesson player | All | Lesson version | Complete, next |
| SCR-022 | Assessment | All | Attempt | Answer, submit, review result |
| SCR-023 | Practical sign-off | Supervisor, Ops Manager | Practical assignment, evidence | Verify competency |
| SCR-024 | Catalogue & authoring | HR, Tenant Admin | Programs, courses, versions | Edit draft, submit for review, publish |
| SCR-025 | Assignments & compliance | HR, Ops Manager, Supervisor | Assignments by scope | Assign, remind, export |
| SCR-030 | People directory | HR, Ops Manager | Users, mapping status | Provision, map, deactivate |
| SCR-031 | Person profile | Scoped managers | Roles, training, competencies, adoption (scoped), Odoo link | Assign training, view factors |
| SCR-032 | Sites | Scoped | Site projection, open exceptions, checklist status | Open site, open in Odoo |
| SCR-040 | Inbox | Supervisor+, HR | Exceptions | Acknowledge, act, resolve, dismiss, escalate |
| SCR-041 | Exception detail | Same | Evidence timeline, recommended action | Act, reassign, resolve |
| SCR-050 | Adoption overview | Ops Manager, Owner | Scores, trends | Drill down |
| SCR-051 | Adoption explanation | Scoped | Factors, deltas, contributing and missing events | Open evidence, start check-in |
| SCR-060 | Owner overview | Owner | Health tiles | Drill to exceptions/adoption |
| SCR-061 | Weekly digest | Owner, Ops Manager | Digest | Open cited items |
| SCR-070 | Help center | All | Articles | Search, read, rate |
| SCR-071 | Report a problem | All | Auto-captured context | Choose category, describe, submit |
| SCR-072 | My requests | All | Support requests | Reply |
| SCR-073 | Support queue | HR, Tenant Admin | Requests | Assign, respond, resolve, link article |
| SCR-080 | Notifications center | All | Notifications | Open, mark read, preferences |
| SCR-090 | Admin sections (3.6) | Tenant Admin | Configuration | Configure |

## 5. Deep links & routing

- Canonical route pattern: `/{section}/{entity}/{id}` (e.g. `/work/checklists/0192…`, `/inbox/exceptions/0193…`).
- Desktop registers the `deployguard://` URL scheme; notifications and emails link via `https://app.<domain>/…`, which the desktop intercepts when installed.
- Odoo deep links are generated only by the `OdooAdapter` (`/odoo/action-<xmlid>/<id>` style for Odoo 19) so that URL formats live in one place ([12](12-odoo-integration.md)).
- Every exception, notification and AI citation resolves to a route. Nothing links to a dead end.

## 6. Search

- Command palette search spans people, sites, courses, articles, templates, tasks and exceptions, filtered by the caller's permissions server-side.
- MVP uses PostgreSQL full-text search (`tsvector`) per entity; no separate search cluster.
