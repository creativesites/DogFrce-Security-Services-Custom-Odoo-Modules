# 10 — Exception Engine & Management Views

> Status: Draft · Owner: Product + Platform · Data model: [14](14-data-model.md) §8
>
> Management attention is the scarcest resource in the company. The exception engine converts facts into **a short, ranked list of things that need a human**, each with evidence and a recommended action.

---

## 1. Principles

1. **Deterministic.** Rules decide what is an exception. AI may rank, explain or summarise, never create or close ([11](11-ai-intelligence.md)).
2. **One owner.** Every exception has exactly one accountable owner at any time.
3. **Evidence attached.** Every exception links to the events, projections or metrics that produced it.
4. **Recommended action.** If we can say what should happen next, we say it.
5. **Dedupe and decay.** Recurrence updates one exception; noise is a bug.
6. **Pause on blindness.** If the underlying data is stale (ERP unreachable), rules that depend on it pause instead of firing false alarms.
7. **Help before escalation.** Where an exception is about a person's missed work, the assistance path ([09](09-adoption-engine.md) §5) runs first.

## 2. Severity

| Severity | Meaning | Response expectation |
|---|---|---|
| **Critical** | Operational or client risk right now (uncovered post, unhandled serious incident) | Immediate, all channels, escalates fast |
| **Attention** | Will become a problem or breaches policy (overdue reviews, overdue mandatory training) | Same working day |
| **Watch** | Trend or signal needing awareness (adoption drop, rising friction) | Weekly review |

Severity can be raised by escalation steps or by rule-defined aging (e.g. Attention unresolved for 48 h → Critical for the manager).

## 3. Lifecycle

```
open → acknowledged → in_progress → resolved
   ↘ dismissed (reason, audited)          ↘ reopened (recurrence within window)
```

| Aspect | Rule |
|---|---|
| Ownership | Resolved at raise time from `owner_rule` (role at scope, assignee, or reporting line); reassignment is audited |
| Acknowledgement | Stops the current escalation step, starts the resolution clock |
| Resolution | Requires a `resolution_code` (`fixed`, `covered`, `explained`, `not_an_issue`, `duplicate`, `deferred`) plus a note for `not_an_issue` and `deferred` |
| Dismissal | Reason mandatory; dismissal of Critical requires manager role; all dismissals audited and reviewed in the weekly digest |
| Dedupe | One open exception per (`rule_id`, `subject`); recurrences increment `recurrence_count`, append evidence and can bump severity |
| Reopen | Same rule + subject recurring within the rule's reopen window reopens the original with its history |
| Auto-resolve | When the underlying condition clears (e.g. slot filled), the exception auto-resolves with `resolution_code = fixed` and a timeline note |

## 4. MVP rule catalogue

| Rule id | Condition (deterministic) | Severity | Owner | Escalation |
|---|---|---|---|---|
| `roster.post_uncovered` | Roster slot within next 12 h has no assigned guard | Critical | Ops manager (scope site) | Immediate → owner; +1 h manager; +2 h owner+owner's manager |
| `roster.supervisor_missing` | Shift at site without an assigned supervisor | Critical | Ops manager | As above |
| `attendance.batch_not_posted` | `attendance.post` expected item missed (past cut-off) | Attention → Critical after 12 h | Site supervisor | +2 h supervisor email; +4 h ops manager |
| `attendance.awol_unaddressed` | AWOL marked in ERP with no follow-up task/incident within 24 h | Attention | Site supervisor | +24 h ops manager |
| `incident.review_overdue` | Incident ≥ threshold not reviewed within SLA | Attention | Ops officer | +24 h ops manager |
| `incident.unresolved_aging` | Incident open > 7 days | Attention | Ops manager | Weekly digest |
| `work.overdue` | Task/checklist overdue beyond grace | Attention | Assignee | +1 day supervisor; +3 days manager |
| `work.unassigned` | Generated work could not resolve an assignee | Attention | Tenant admin | +4 h ops manager |
| `work.verification_overdue` | Submitted work awaiting verification > 48 h | Attention | Verifier | +24 h ops manager |
| `training.mandatory_overdue` | Mandatory assignment past due | Attention | Learner's supervisor (learner notified first) | +3 days HR; +7 days manager |
| `competency.gap_operational` | Person performing a role without the required competency level beyond grace | Attention | HR + ops manager | Weekly |
| `compliance.document_expiring` | ERP certification/document expiring within threshold (from `odoo.alert.raised`) | Attention → Critical at expiry for firearm/eligibility-critical | HR | +3 days ops manager |
| `adoption.abandonment_confirmed` | Abandonment signal unresolved after assistance ([09](09-adoption-engine.md) §5) | Attention | Site supervisor | +5 working days ops manager |
| `adoption.site_drop` | Site workflow coverage down ≥ 15 points week-over-week with Medium+ confidence | Watch | Ops manager | Weekly digest |
| `support.recurring_issue` | ≥ 3 problem reports of the same category/screen in 7 days | Watch | Tenant admin | Weekly |
| `integration.sync_broken` | No successful Odoo poll for 30 min, or webhook auth failures | Critical (ops) | Tenant admin + platform ops | Immediate |
| `access.likely_blocking` | Investigation found a permission change coinciding with missed work | Attention | Tenant admin | +1 day ops manager |

Each rule is configurable per tenant (enable, thresholds, owner, escalation policy) and versioned; changes are audited.

## 5. Evidence and recommended action

An exception carries:

- **Evidence**: event ids, projection snapshots (e.g. the roster slot as it was), metric values with definitions, related feedback or support requests.
- **Context**: what changed recently (roster edits, role changes, ERP outage), so the reader isn't guessing.
- **Recommended action**: from the rule's action template, e.g. "Assign an available supervisor" with a deep link to the ERP roster board, or "Open support request #88 first — this person reported a permission error".
- **History**: recurrence count, previous resolutions of the same rule for this subject, which prevents the same "fix" being applied repeatedly to a structural problem.

## 6. Manager inbox

```
Critical    (act now)        — never more than a handful; if it is, the thresholds are wrong
Attention   (today)          — grouped by theme: coverage · reports · training · people · system
Watch       (this week)      — trends, recurring issues, adoption movement
Resolved (7 days)            — with who resolved and how
```

Behaviour:

- Two-interaction rule: every item can be acted on in at most two interactions (open → act), or provides the exact deep link that does.
- Bulk actions where safe (acknowledge, remind, assign the same owner) with audit.
- Keyboard triage (`j`/`k`, `a` acknowledge, `e` resolve, `Enter` open).
- Filters by site, supervisor, rule, age.
- **Empty state is a success state**: "Nothing needs you right now. 12 items were handled by supervisors today."
- V1: AI orders within severity bands and writes a one-line "why this matters now", with citations.

## 7. Role-specific views

| Role | View |
|---|---|
| **Site supervisor** | Only their sites and team; mostly `work.*`, `attendance.*`, verification and their people's training; assistance framing |
| **Ops officer** | Their region's operational exceptions and client requests |
| **Ops manager** | Everything in the tenant, ranked; plus supervisor-level patterns |
| **HR/Admin** | People-related: training, competency, access problems, "my info is wrong" |
| **Owner** | Critical only, plus weekly digest of themes and aging |
| **Tenant admin** | System and integration exceptions, configuration problems |

## 8. Quality control of the engine itself

| Risk | Control |
|---|---|
| Alert fatigue | Per-rule metrics: volume, acknowledge rate, resolve time, dismissal rate. A rule with > 30 % dismissals is reviewed and re-tuned automatically flagged in the weekly ops review |
| False positives from stale data | Rules declare their data dependencies; stale projections pause those rules and show "paused — Odoo data stale" |
| Duplicate human effort | Dedupe plus cross-rule suppression (e.g. `work.overdue` is suppressed for items already covered by `adoption.abandonment_confirmed`) |
| Structural problems treated as incidents | Recurrence counters and the `support.recurring_issue` rule surface patterns for a configuration or training fix |
| Rules drifting from reality | Every rule has an owner and a review date; unreviewed rules appear in the admin health page |
