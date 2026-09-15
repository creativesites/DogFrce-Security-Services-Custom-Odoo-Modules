# 08 — Work Management

> Status: Draft · Owner: Product · Data model: [14](14-data-model.md) §5
>
> Not a project tool. Security operations work is **recurring, shift- and site-bound, evidence-backed and verified**. We build small generic primitives and express the domain as templates and rules on top.

---

## 1. Generic primitives vs domain layer

| Generic primitive (core code) | Domain expression (configuration) |
|---|---|
| `Task` (assignee, due, status, evidence, comments) | "Review occurrence report #214 before 17:00" |
| `ChecklistTemplate` + `ChecklistInstance` with typed items | "Site visit inspection", "Shift handover" |
| `ScheduleRule` (calendar / shift / site-event recurrence) | "Every published night shift at Site 12, 30 min before start" |
| `Verification` (approve/reject + reason) | Supervisor signs off a guard's practical competency |
| `AutoCompleteRule` (event pattern → fulfils item) | `odoo.attendance.batch.submitted` completes "Post attendance" |
| `WorkflowDefinition` (V1: ordered steps, approvals, dependencies) | "Client complaint handling: acknowledge → investigate → respond → close" |

**Rule:** if a security-specific concept would require new core tables, first try to express it as a template + schedule + auto-complete rule. Core gains a concept only when three or more domain templates need it.

## 2. Task and checklist lifecycle

```
generated/created → open → in_progress → submitted → verified
                                   ↘ could_not_complete (reason) ↘ rejected (reason) → in_progress
```

- **Overdue** is derived deterministically from `due_at` and the tenant working calendar, and emits `work.task.overdue` once per transition.
- **"Couldn't complete"** is a first-class outcome with a mandatory reason (`blocked_permission`, `system_error`, `information_missing`, `site_access`, `time`, `other` + free text). It routes to the supervisor and feeds friction signals — the alternative is silent non-completion, which is what we are trying to eliminate.
- **Rejection** returns the instance to the assignee with the reason visible, and (for practicals) records no competency evidence.
- **Cancellation** requires a reason and is audited; cancelled work is excluded from expected-work denominators.

## 3. Recurrence and generation

| Mode | Source | Example |
|---|---|---|
| `calendar` | RRULE + working calendar | "Every Monday 08:00, ops officer: weekly client report review" |
| `shift` | ERP roster projection (`ShiftProjection`) | "For every published shift at a site with a supervisor assigned: handover checklist, due 30 min after shift start" |
| `site_event` | ERP event | "When an incident of severity ≥ high is created: review task for the ops officer, due in 4 h" |

Generation rules:

- Materialised by the worker **ahead of time** (default 7 days) and refreshed when the roster changes; a roster change can create, reassign or cancel future instances (never past ones).
- Assignment resolution order: `slot_employee` → `role_at_site` → `specific_user` → fallback `role_at_tenant`; unassigned work raises an exception rather than sitting invisible.
- Leave and absence (from ERP) reassign to the covering person where the roster says so; otherwise the item is excused and the gap is surfaced.
- Idempotent: regeneration never duplicates an instance for the same (template, scope, period).

## 4. Auto-completion from ERP

A template item can declare an `AutoCompleteRule`: an event pattern plus a matching key.

```yaml
template: attendance.post
expects_event: odoo.attendance.batch.submitted
match:
  site_id: {from: scope.site_id}
  shift_date: {from: period.date}
  shift: {from: scope.shift}
on_match: complete_item(actor = event.actor)
```

This is what makes the Platform a **layer above** the ERP rather than duplicate data entry: the supervisor does the work in Odoo, and the Platform closes the loop automatically. Manual completion of an auto-completable item is allowed only with a reason (and is flagged for review), so the system does not become a place to claim credit for work not done.

## 5. Evidence and verification

- Item types: yes/no, choice, number (with range), short text, **photo**, file, signature.
- Evidence requirements are per item; photos capture time and (optionally, if the tenant enables it and the user consents) coarse location — **off by default**, because the Platform does not track people ([16](16-security-architecture.md) §9).
- Verification is required where the template says so; `verifier_rule` resolves to the supervisor of the assignee's site, the ops manager, or a named role.
- A verified instance can record **competency evidence** ([07](07-training-platform.md) §5) when the template links to a competency.

## 6. Security template library

**MVP (3 templates, deep rather than broad):**

| Template | Cadence | Items (summary) | Verification | Auto-complete |
|---|---|---|---|---|
| `attendance.post` | Per site per shift-day, due at cut-off | Confirm roster vs actual, mark absences with reason, submit batch in ERP | None (ERP state is the proof) | `odoo.attendance.batch.submitted` |
| `site.visit` | Weekly per site (configurable) | Arrival time, guard presentation, post condition, equipment present, client feedback, 2+ photos, issues found | Ops manager or senior supervisor | — |
| `incident.review` | Per ERP incident above a severity threshold | Read report, completeness check, client notification needed?, action taken, close-out note | Ops manager for high severity | `odoo.incident.state_changed → reviewed` |

**V1 library:**

| Template | Notes |
|---|---|
| `shift.handover` | Outgoing → incoming: open issues, occurrences, equipment, keys, client instructions; verified by the incoming supervisor |
| `site.open` / `site.close` | Opening and closing procedures per client SOP |
| `equipment.check` | Periodic equipment inspection; links to ERP equipment records |
| `patrol.confirmation` | Confirms guard patrol logs exist and are plausible for the shift (ERP patrol entries are `security.incident` records today) |
| `client.request` | Intake → action → response, with SLA |
| `compliance.check` | Document/certification expiry follow-up per site |
| `vehicle.pre_departure` | Complements the ERP vehicle inspection where an extra sign-off is required |

Each shipped template is a **starting point**: tenants clone and adapt, and their versions are tenant data ([30](30-productization.md)).

## 7. What we deliberately do not build

- Kanban boards, Gantt charts, sprints, story points, time tracking.
- Free-form project hierarchies (epics/subtasks beyond one level of checklist items).
- A general workflow designer in MVP (templates + recurrence cover the real cases; a builder arrives only if tenants genuinely need novel flows).
- Duplicate ERP entities: no rosters, no payroll, no invoices, no equipment master data.

## 8. Relationship to adoption and exceptions

- Completed expected work is the numerator of `workflow_coverage` ([09](09-adoption-engine.md)).
- Overdue, unassigned, repeatedly rejected or "couldn't complete" work raises exceptions ([10](10-exception-engine.md)).
- Friction signals from work (abandonment, errors, difficulty ratings) feed both the adoption explanation and the training remediation loop, so the system's first response to failure is help.
