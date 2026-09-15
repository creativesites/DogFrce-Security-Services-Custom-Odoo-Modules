# 23 — Audit System

> Status: Draft · Owner: Platform architecture + security
>
> Audit answers "who did what, when, on whose behalf, and why" — for security review, dispute resolution and customer trust. It is separate from events ([13](13-event-architecture.md)) and from telemetry ([27](27-observability.md)).

---

## 1. Record shape

| Field | Notes |
|---|---|
| `id`, `at` | UUIDv7, timestamptz |
| `tenant_id` | Null for platform-level actions |
| `actor` | `{type: user\|platform_staff\|system\|integration\|ai, id, roles[], on_behalf_of?}` |
| `action` | Stable verb key, e.g. `training.course.published`, `identity.session.revoked` |
| `resource` | `{type, id, label}` |
| `outcome` | `success\|denied\|error` (+ reason code) |
| `before_digest` / `after_digest` | SHA-256 of the canonicalised relevant fields, plus a redacted diff of allowlisted fields |
| `reason` | Required for sensitive actions (break-glass, override, dismissal, export) |
| `context` | `{ip, user_agent_class, device_id, app_version, correlation_id, request_id}` |
| `linked` | Related event ids, exception id, AI run id |

Append-only: no updates or deletes; enforced by table permissions (no `UPDATE`/`DELETE` grants to the application role) and verified in CI.

## 2. What is audited

| Area | Audited actions |
|---|---|
| Authentication | Sign-in success/failure class, MFA outcomes, token refresh reuse detection, sign-out, session and device revocation, lockouts |
| Authorisation | Role assignment changes, scope changes, custom role edits, permission denials on sensitive resources |
| Identity linking | Link created/changed, DeployGuard access granted/revoked, drift resolution |
| Configuration | Tenant settings, exception rules and thresholds, expected-work definitions, notification policies, escalation policies, feature flags, AI capability toggles and budgets |
| Content | Course/template/article draft → review → publish → retire, version pinning, deletion |
| Work | Verification approve/reject with reason, due-date changes, reassignment, cancellation, bulk operations |
| Training & competency | Assignment create/waive, attempt invalidation, competency level award/revoke, certification issue/expiry override |
| Adoption | Score recomputation/replay, suppression or exclusion of expected items, visibility policy changes |
| Exceptions | Dismissals (reason mandatory), owner reassignment, manual severity change, rule enable/disable |
| Support & privacy | Access to another user's support content, export generation, privacy-request handling, monitoring-notice version changes |
| AI | Run executed, output validation failures, recommendation approved/rejected/applied, prompt/template version change |
| Integration | Connection created/updated, secret rotation, allowlisted command execution, contract version change |
| Platform staff | Break-glass request/grant/expiry and every tenant record class accessed during it |

## 3. Retention and access

| Class | Retention | Who can read |
|---|---|---|
| Security and identity | 24 months (longer if legally required) | Tenant admin (own tenant), platform security |
| Configuration and content | 36 months | Tenant admin, ops manager (read) |
| Work/training operational overrides | 24 months | Tenant admin, ops manager, HR for people-related |
| AI decisions | 36 months | Tenant admin, ops manager |
| Platform staff access | 36 months | Platform security; tenant admin sees entries touching their tenant |

Audit reads are themselves audited when they concern another person's data. Exports are signed and record the query used.

## 4. Integrity

- Daily hash chain per tenant: each day's audit rows are hashed in sequence, and the day's terminal hash is stored in a separate table and copied to the backup bucket, so tampering with history is detectable.
- Backups of audit tables are retained independently of operational data retention.
- Clock: server time only; client-claimed times are recorded as data, never as `at`.

## 5. Relationship to ERP audit

DeployGuard ERP keeps its own audit (mail tracking, `security.deployguard.audit` in the bridge). Cross-system actions (SSO ticket issuance, allowlisted commands) are audited **on both sides** with the same `correlation_id`, so an investigation can join them.
