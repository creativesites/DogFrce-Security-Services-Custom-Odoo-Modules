# 13 — Event Architecture

> Status: Draft · Owner: Platform architecture · Decision: [DG-ADR-009](adr/DG-ADR-009-event-architecture.md)
>
> Events are immutable facts about something that happened. They power adoption scoring ([09](09-adoption-engine.md)), exceptions ([10](10-exception-engine.md)), notifications ([21](21-notification-system.md)), AI evidence ([11](11-ai-intelligence.md)) and analytics ([22](22-analytics.md)). Audit records are separate ([23](23-audit-system.md)), although many audit entries are written in the same transaction as an event.

---

## 1. Envelope

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | UUIDv7 | ✓ | Globally unique, time-ordered. Clients may generate it (offline). |
| `global_seq` | bigint | server | Assigned on insert; dispatcher cursor. Not exposed to clients. |
| `type` | string | ✓ | `<domain>.<entity>.<action>` — see §2. |
| `version` | int | ✓ | Schema version of `data` for this `type`. |
| `tenant_id` | UUID | server | **Always taken from the authenticated context**, never from the payload. |
| `occurred_at` | timestamptz | ✓ | When it happened (client or source clock). |
| `recorded_at` | timestamptz | server | When the Platform stored it. Lag = `recorded_at − occurred_at`. |
| `actor` | object | ✓ | `{type: user\|guard\|system\|integration\|ai, id, role?}`. For clients, stamped from the token. |
| `subject` | object | ✓ | `{type, id}` — the primary entity the event is about (task, checklist_instance, attendance_batch, user…). |
| `scope` | object | ○ | `{site_id?, team_id?}` for fast scoped queries and RLS-friendly rollups. |
| `source` | object | ✓ | `{system: platform\|desktop\|web\|mobile\|odoo, app_version?, device_id?, channel?: api\|webhook\|poll\|job}` |
| `correlation_id` | UUID | ✓ | Groups everything caused by one user intent or job run; propagated from `X-DG-Correlation-Id`. |
| `causation_id` | UUID | ○ | `id` of the event that directly caused this one. |
| `idempotency_key` | string | ✓ for external | Unique per tenant. Client events: `client:{id}`. Odoo: `odoo:{event_id}`. Internal: defaults to `id`. |
| `privacy_class` | enum | ✓ | `P0` operational, `P1` personal-work, `P2` sensitive (§7). |
| `odoo` | object | ○ | `{model, res_id, write_date}` for Odoo-originated or Odoo-linked events. |
| `data` | JSONB | ✓ | Type-specific payload validated by `packages/contracts/events/<type>.v<version>.ts`. |

## 2. Naming & versioning

- **Pattern:** `<domain>.<entity>.<action>`, lower snake case segments, action in **past tense** (`submitted`, `overdue`, `raised`).
- **Domains:** `identity`, `work`, `training`, `competency`, `adoption`, `exception`, `notification`, `feedback`, `support`, `knowledge`, `ai`, `client`, `odoo`, `integration`.
- **Odoo-originated facts** are prefixed `odoo.` so no one mistakes an ERP fact for a Platform-owned fact.
- **Versions:**
  - Additive optional fields do not bump the version.
  - Renaming, removing or re-typing a field, or changing semantics, requires `version + 1`.
  - Producers emit only the latest version; consumers accept the latest and the previous version for one release cycle.
- **Registry:** a type is invalid unless registered in `packages/contracts/events/registry.ts` with schema, privacy class, retention class, producers and consumers. CI fails on unregistered emits.

## 3. MVP event catalogue

| Type | Producer | Key `data` | Main consumers |
|---|---|---|---|
| `identity.session.started` | identity | `{method: odoo_assertion, amr[], device_id}` | analytics |
| `identity.session.ended` / `.revoked` | identity | `{reason}` | analytics, audit |
| `identity.device.registered` | identity | `{platform, app_version}` | audit |
| `identity.user.linked` | identity | `{odoo_uid, employee_id?}` | projections |
| `odoo.identity.user.deactivated` / `.password_changed` / `.totp_changed` / `odoo.identity.access.revoked` | odoo-sync | `{odoo_uid}` | identity (revocation) |
| `odoo.roster.batch.published` | odoo-sync | `{site_id, period}` | expected work |
| `odoo.roster.slot.assigned` / `.unfilled` | odoo-sync | `{site_id, post_id, shift_start, shift_end, employee_id?}` | expected work, exceptions |
| `odoo.attendance.batch.created` / `.submitted` / `.reviewed` / `.locked` | odoo-sync | `{site_id, shift_date, shift, state, responsible_user_id, counts{}}` | expected work, work-autocomplete, exceptions |
| `odoo.attendance.record.checked_in` / `.checked_out` | odoo-sync | `{employee_id, site_id, slot_id, at, late_minutes?}` | adoption (guards via site), exceptions |
| `odoo.attendance.missed` | odoo-sync | `{employee_id, slot_id, site_id}` | exceptions |
| `odoo.incident.created` / `.state_changed` | odoo-sync | `{incident_id, type, severity, site_id, from?, to}` | expected work (review), exceptions |
| `odoo.leave.approved` / `.cancelled` | odoo-sync | `{employee_id, date_from, date_to}` | expected work exclusions |
| `odoo.alert.raised` | odoo-sync | `{alert_type, severity, related{model,id}}` | exceptions |
| `work.task.created` / `.assigned` / `.started` / `.completed` / `.overdue` / `.could_not_complete` | work | `{task_id, template_id?, assignee, due_at, reason?}` | adoption, exceptions, notifications |
| `work.checklist.started` / `.submitted` / `.verified` / `.rejected` | work | `{instance_id, template_id, template_version, site_id?, answered, required_missing, evidence_count, verifier?, reason?}` | adoption, exceptions, training (practical evidence) |
| `training.assignment.created` / `.overdue` | training | `{assignment_id, course_id, due_at, mandatory}` | notifications, exceptions, adoption |
| `training.lesson.started` / `.completed` | training | `{course_version_id, lesson_id, duration_s}` | adoption, analytics |
| `training.attempt.passed` / `.failed` | training | `{attempt_id, assessment_id, score, pass_mark, attempt_no, missed_tags[]}` | adaptive training (V1+), adoption |
| `training.course.completed` | training | `{course_version_id, assignment_id?}` | competency, notifications |
| `competency.evidence.recorded` | competency | `{competency_id, evidence_type, source_ref, verifier?}` | competency status |
| `competency.level.changed` | competency | `{competency_id, from, to, basis}` | analytics, exceptions (gaps) |
| `client.workflow.started` / `.abandoned` | desktop/web | `{workflow_key, step, elapsed_s}` | adoption (friction) |
| `client.error.shown` | desktop/web | `{code, route, ref}` | adoption (friction), support context |
| `client.odoo.opened` | desktop/web | `{target_kind, ticket_ok}` | analytics |
| `feedback.task.rated` | feedback | `{subject{type,id}, rating: easy\|okay\|difficult\|could_not_complete}` | adoption (friction), analytics |
| `feedback.problem.reported` | feedback | `{category, subject?, support_request_id}` | support, adoption (friction) |
| `support.request.created` / `.resolved` | support | `{request_id, category, resolution_code?}` | adoption (suppression), analytics |
| `adoption.expected_work.missed` | adoption | `{expected_item_id, workflow_key, due_at}` | exceptions, abandonment |
| `adoption.snapshot.computed` | adoption | `{subject, date, score?, confidence, factors_ref}` | analytics |
| `adoption.score.changed` | adoption | `{subject, from, to, window, top_factors[]}` (only when change ≥ threshold) | exceptions (watch), notifications |
| `adoption.abandonment.suspected` | adoption | `{subject_user, workflow_key, baseline, observed, window}` | check-in flow, exceptions |
| `adoption.checkin.responded` | adoption | `{checkin_id, answer_code}` | support routing, exceptions |
| `exception.raised` / `.acknowledged` / `.escalated` / `.resolved` / `.dismissed` / `.reopened` | exceptions | `{exception_id, rule_id, severity, owner, step?, resolution_code?}` | notifications, analytics, audit |
| `notification.delivery.failed` | notifications | `{channel, reason}` | ops metrics |
| `ai.run.completed` | intelligence | `{run_id, capability, status, cost_micro}` | ops metrics |
| `ai.recommendation.proposed` / `.approved` / `.rejected` | intelligence | `{recommendation_id, capability, approver?}` | inbox, audit |

### 3.1 Mapping from the brief's event names

| Brief name | Platform event(s) |
|---|---|
| `user.logged_in` | `identity.session.started` |
| `shift.started` / `shift.completed` | `odoo.attendance.record.checked_in` / `.checked_out` |
| `attendance.submitted` | `odoo.attendance.batch.submitted` |
| `task.created/started/completed/overdue` | `work.task.*` |
| `checklist.started/completed` | `work.checklist.started` / `.submitted` (+ `.verified`) |
| `incident.created/updated/resolved` | `odoo.incident.created` / `.state_changed` |
| `report.submitted` / `report.reviewed` | `work.checklist.submitted` / `.verified` for Platform reports; `odoo.incident.*` for ERP occurrence reports |
| `training.started` / `training.completed` | `training.lesson.started` / `training.course.completed` |
| `quiz.failed` / `quiz.passed` | `training.attempt.failed` / `.passed` |
| `support.requested` | `support.request.created` |
| `feedback.submitted` | `feedback.task.rated`, `feedback.problem.reported` |
| `workflow.abandoned` | `client.workflow.abandoned` |
| `system.error` | `client.error.shown` (user-visible); server errors go to observability, not the event store ([27](27-observability.md)) |

## 4. Examples

**Platform domain event**

```json
{
  "id": "0192f1a2-3b4c-7d5e-8f60-718293a4b5c6",
  "type": "work.checklist.submitted",
  "version": 1,
  "tenant_id": "0191aa00-0000-7000-8000-000000000001",
  "occurred_at": "2026-09-16T10:14:03Z",
  "recorded_at": "2026-09-16T10:14:03.412Z",
  "actor": { "type": "user", "id": "0191ab10-…", "role": "site_supervisor" },
  "subject": { "type": "checklist_instance", "id": "0192f19f-…" },
  "scope": { "site_id": "0191ac20-…" },
  "source": { "system": "desktop", "app_version": "0.4.2", "device_id": "0191ad30-…", "channel": "api" },
  "correlation_id": "0192f1a2-3b40-7aaa-9bbb-ccccdddd0001",
  "causation_id": null,
  "idempotency_key": "client:0192f1a2-3b4c-7d5e-8f60-718293a4b5c6",
  "privacy_class": "P1",
  "data": {
    "instance_id": "0192f19f-…",
    "template_id": "0191b001-…",
    "template_version": 3,
    "answered": 14,
    "required_missing": 0,
    "evidence_count": 3
  }
}
```

**Offline client event (queued, synced later)**

```json
{
  "id": "0192f0f1-aaaa-7bbb-8ccc-dddd00000002",
  "type": "client.workflow.abandoned",
  "version": 1,
  "occurred_at": "2026-09-16T07:02:44Z",
  "actor": { "type": "user", "id": "(stamped by server)" },
  "subject": { "type": "checklist_instance", "id": "0192f0e0-…" },
  "source": { "system": "desktop", "app_version": "0.4.2", "device_id": "(stamped)", "channel": "api" },
  "correlation_id": "0192f0f1-aaaa-7bbb-8ccc-dddd00000001",
  "idempotency_key": "client:0192f0f1-aaaa-7bbb-8ccc-dddd00000002",
  "privacy_class": "P1",
  "data": { "workflow_key": "checklist.site_visit", "step": "evidence_photo", "elapsed_s": 312 }
}
```

**Odoo-originated event after ingestion**

```json
{
  "id": "0192f0c8-6f7a-7c21-9d3e-1b5a2c3d4e5f",
  "type": "odoo.attendance.batch.submitted",
  "version": 1,
  "occurred_at": "2026-09-16T05:42:10Z",
  "recorded_at": "2026-09-16T05:42:12.050Z",
  "actor": { "type": "user", "id": "0191ab10-…", "role": "site_supervisor" },
  "subject": { "type": "attendance_batch", "id": "odoo:security.attendance.batch:8812" },
  "scope": { "site_id": "0191ac20-…" },
  "source": { "system": "odoo", "channel": "webhook" },
  "correlation_id": "0192f0c8-6f6e-7a11-8c3d-aa11bb22cc33",
  "idempotency_key": "odoo:0192f0c8-6f7a-7c21-9d3e-1b5a2c3d4e5f",
  "privacy_class": "P1",
  "odoo": { "model": "security.attendance.batch", "res_id": 8812, "write_date": "2026-09-16T05:42:10Z" },
  "data": { "site_id": "0191ac20-…", "shift_date": "2026-09-15", "shift": "night", "state": "captured", "counts": { "present": 11, "absent": 1, "awol": 0, "not_marked": 0 } }
}
```

(The actor is resolved from `odoo_uid` via identity links; unmapped actors become `{type: "integration", id: "odoo_uid:57"}`.)

**Derived adoption event**

```json
{
  "id": "0192f3c0-…",
  "type": "adoption.score.changed",
  "version": 1,
  "actor": { "type": "system", "id": "adoption-scorer" },
  "subject": { "type": "user", "id": "0191ab10-…" },
  "source": { "system": "platform", "channel": "job" },
  "correlation_id": "0192f3bf-…(nightly run)",
  "causation_id": "0192f3bf-…(adoption.snapshot.computed)",
  "privacy_class": "P1",
  "data": {
    "window": "7d",
    "from": 72, "to": 64,
    "confidence": "high",
    "top_factors": [
      { "factor": "workflow_coverage", "delta": -12, "evidence_ref": "snapshot:0192f3be-…#coverage" },
      { "factor": "training_currency", "delta": -3 }
    ]
  }
}
```

**Exception raised**

```json
{
  "type": "exception.raised",
  "version": 1,
  "actor": { "type": "system", "id": "rule:roster.supervisor_missing" },
  "subject": { "type": "exception", "id": "0192f400-…" },
  "scope": { "site_id": "0191ac20-…" },
  "source": { "system": "platform", "channel": "job" },
  "causation_id": "0192f3f9-…(odoo.roster.slot.unfilled)",
  "privacy_class": "P0",
  "data": { "exception_id": "0192f400-…", "rule_id": "roster.supervisor_missing", "severity": "critical", "owner": { "type": "role_at_scope", "role": "ops_manager" } }
}
```

**AI recommendation proposed (V1)**

```json
{
  "type": "ai.recommendation.proposed",
  "version": 1,
  "actor": { "type": "ai", "id": "capability:adoption.drop.explain@1" },
  "subject": { "type": "ai_recommendation", "id": "0192f500-…" },
  "privacy_class": "P1",
  "data": { "recommendation_id": "0192f500-…", "capability": "adoption.drop.explain", "risk_tier": "proposal", "evidence_count": 6, "confidence": "medium" }
}
```

## 5. Correlation, causation, ordering

- **Correlation:** one user intent (e.g. submitting a checklist) → one `correlation_id` shared by the API request trace, domain events, notifications and resulting exception updates. Jobs create a new `correlation_id` per run.
- **Causation:** set when a consumer emits an event because of another event. This makes chains inspectable ("why was this exception raised?").
- **Ordering:**
  - Guaranteed per `global_seq` insertion order.
  - Consumers that need per-subject order process by `(subject_type, subject_id)` partitions and ignore out-of-order older versions using `occurred_at` + `odoo.write_date` comparisons.
  - Client-supplied `occurred_at` is trusted only within ±24 h of `recorded_at` (beyond → clamped and flagged `clock_suspect`).

## 6. Idempotency

| Source | Key | Duplicate behaviour |
|---|---|---|
| Client | `client:{event.id}` | Insert ignored; `200` with `duplicate: true` |
| Odoo webhook / poll | `odoo:{bridge event_id}` / `odoo-poll:{model}:{res_id}:{write_date}:{type}` | Ignored |
| Internal emit | `id` | N/A (transactional) |
| Consumers with side effects | `(consumer, event_id)` in `event_consumer_effect` | Skip |

## 7. Privacy classes

| Class | Meaning | Examples | Rules |
|---|---|---|---|
| **P0** Operational | No personal data, or only IDs of organisational entities | site coverage, exception raised on a site | Standard retention |
| **P1** Personal-work | Work behaviour linked to an identifiable person | checklist submitted, attempt failed, abandonment suspected | Scoped access (self, reporting line, authorised roles); purpose-limited to support, training and operations; never exported to HR/discipline systems (PR-ADO-07) |
| **P2** Sensitive | Health, disciplinary content, free-text narratives about people, precise location | **Not stored in events.** Events carry references (e.g. `incident_id`), never the content | Content stays in its authoritative system (Odoo) under its own access rules |

Client telemetry never includes typed free text, field values, screen content, keystrokes, clipboard or location.

## 8. Retention (defaults — final values per OQ-14)

| Class of event | Hot (queryable) | Then |
|---|---|---|
| `client.*` telemetry | 90 days | Aggregated into daily metrics, raw deleted |
| `work.*`, `training.*`, `competency.*`, `feedback.*`, `support.*` | 24 months | Archived to object storage (encrypted) for 5 years, or deleted per tenant policy |
| `odoo.*` | 13 months (projections keep current state) | Deleted |
| `adoption.*` | 24 months | Aggregated; raw deleted |
| `exception.*`, `ai.recommendation.*` | 36 months | Archived |
| `identity.*` | 13 months | Security-relevant copies live in the audit log |

Partition drop jobs enforce retention. Per-user erasure requests pseudonymise `actor.id`/`subject.id` in retained partitions where legal retention applies.

## 9. Replay

- **CLI:** `platform events replay --tenant <id> --consumer adoption --from 2026-09-01 --to 2026-09-15 [--dry-run]`.
- Resets the consumer checkpoint for the tenant range, purges derived rows in that range (e.g. `adoption_snapshot`), then reprocesses.
- **Side-effecting consumers** (notifications, email, AI calls) refuse replay unless `--allow-effects` is passed by a platform admin; audited.
- Replays are used after fixing scoring bugs or changing rule versions. Derived records store `rule_version` so a report can say which logic produced a number.
