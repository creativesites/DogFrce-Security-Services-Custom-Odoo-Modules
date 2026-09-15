# 22 — Analytics

> Status: Draft · Owner: Product + Platform
>
> Metrics must be **defined once** and reused everywhere (screens, digests, AI context). A number without a definition and a drill-down is not shipped.

---

## 1. Metric contract

Every metric has: `key`, display name, plain-language definition, formula, source events/projections, grain, window, owner role, and a drill-down route. They live in `packages/domain/metrics` and are the only source used by UI, digests and AI.

## 2. Core metric catalogue (MVP)

| Key | Definition | Formula | Grain |
|---|---|---|---|
| `workflow_coverage` | Share of expected operational work completed in the system | fulfilled ÷ (expected − excused) | user, site, team, supervisor, tenant / 7 d, 28 d |
| `on_time_rate` | Of completed expected work, share completed before its due time | on_time ÷ fulfilled | same |
| `overdue_open` | Count of currently overdue tasks/checklists | count(status ∈ open, due_at < now) | user, site, team |
| `verification_latency` | Median hours from submit to verify | median(verified_at − submitted_at) | supervisor, site |
| `incident_review_latency` | Median hours from ERP incident creation to review | from `odoo.incident.*` | site, tenant |
| `attendance_batch_timeliness` | Batches submitted before cut-off ÷ batches expected | expected work of type `attendance.post` | site, supervisor |
| `training_compliance` | Mandatory assignments completed by due date ÷ mandatory assigned | training events | user, role, site, tenant |
| `competency_coverage` | Users meeting the required level ÷ users requiring it | competency status vs requirements | role, site, tenant |
| `adoption_score` | Composite operational adoption ([09](09-adoption-engine.md)) | weighted factors | user, site, team, supervisor, tenant |
| `friction_rate` | Friction signals per 100 expected items | (abandonments + errors + "couldn't complete" + problem reports) ÷ expected × 100 | user, site, workflow |
| `support_load` | Open support requests and median time to resolution | support events | tenant, category |
| `exception_load` | Open exceptions by severity, and median time to resolution | exception events | scope |
| `escalation_rate` | Exceptions escalated beyond step 1 ÷ exceptions raised | exception timeline | rule, scope |
| `coverage_gap` (ERP) | Roster slots unfilled within the next 24 h | `odoo.roster.slot.unfilled` + projections | site, tenant |

**Deliberately excluded:** login counts, session duration, "activity" measures, and anything that rewards presence over outcomes.

## 3. Levels and audiences

| Level | Audience | Typical questions |
|---|---|---|
| **Employee** | Self (+ their supervisor) | "Am I up to date? What is outstanding for me?" |
| **Site** | Supervisor, ops officer, manager | "Is this site running through the system? Where does it break?" |
| **Supervisor/team** | Manager | "Which supervisors need support (not blame)?" |
| **Company** | Manager, owner | "Is adoption improving? Where is operational risk?" |
| **Platform** | Internal staff | "Tenant health, sync lag, AI cost, release adoption" — never tenant content |

## 4. Rollups

- Nightly per tenant timezone: `metric_daily(tenant, metric_key, grain, subject_id, date, value, numerator, denominator, rule_version)`.
- Rolling windows (7 d, 28 d) computed from daily rows; sparse periods are marked `insufficient_data` rather than shown as zero.
- Backfill and replay recompute daily rows deterministically ([13](13-event-architecture.md) §9).
- Query services read rollups; screens never aggregate raw events on demand except for small drill-downs.

## 5. Presentation rules

- Every metric tile shows: value, comparison to the previous window, confidence/sufficiency, and a link to its drill-down.
- Numerals use `--dgs-mono` with tabular figures; the coverage/metric ramp is the only gradient ([05](05-ux-principles.md) §3).
- Trends need at least 3 comparable periods; otherwise show the raw value only.
- People-level metrics are visible only within the viewer's scope and reporting line.
- Where a metric can be read as judgement of a person, the UI pairs it with the support action (open check-in, view friction signals) rather than a ranking.

## 6. Exports and reporting

- CSV/XLSX export of any table the user can see, with the metric definitions included in the export header (audited).
- Weekly digest (MVP) composes existing metrics; the AI brief (V1) narrates the **same numbers** and may not invent others ([11](11-ai-intelligence.md) §6).
- ERP reporting (client service reports, payroll, billing) stays in DeployGuard ERP.
