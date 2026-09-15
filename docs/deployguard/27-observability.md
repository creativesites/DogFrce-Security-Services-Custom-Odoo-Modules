# 27 — Observability

> Status: Draft · Owner: Platform engineering · Decision: [DG-ADR-014](adr/DG-ADR-014-observability.md)

---

## 1. Signals

| Signal | Tooling | Retention (default) |
|---|---|---|
| Traces | OpenTelemetry → provider backend | 30 days |
| Metrics | OpenTelemetry → provider backend | 13 months (aggregated) |
| Logs | pino JSON → provider backend | 30 days |
| Errors / release health | Sentry (desktop Rust + WebView, web, api, worker) | 90 days |
| Product/domain analytics | The Platform's own event store and rollups ([22](22-analytics.md)) | Per [13](13-event-architecture.md) §8 |
| Audit | PostgreSQL, append-only ([23](23-audit-system.md)) | 24–36 months |

Telemetry never contains event `data`, free text, credentials, tokens or personal fields beyond pseudonymous IDs.

## 2. Domain SLIs

| SLI | Why |
|---|---|
| Event dispatcher lag per consumer | Late scoring and exceptions mean late help |
| Odoo webhook lag and poll lag per tenant | Stale ERP facts create false or missed exceptions |
| Bridge outbox backlog and dead letters | Early warning of tenant-side breakage |
| Expected-work materialisation success | Missing expectations silently deflate adoption metrics |
| Adoption snapshot job duration/success per tenant | Nightly correctness |
| Notification delivery success and escalation timeliness per channel | Escalations must actually reach people |
| SSO ticket success rate | Single login is a product promise (R-7) |
| Sync command success and conflict rate | Offline usability |
| AI latency, validation-failure rate, cost per capability | Quality and budget |
| Desktop crash-free sessions and version adoption | Client health |

## 3. SLOs (initial, pilot)

| Service level | Objective |
|---|---|
| API availability (business hours) | 99.5 % monthly |
| API read latency p95 | ≤ 300 ms |
| Event dispatch lag p95 | ≤ 5 s |
| Exception raised within | ≤ 2 min of the triggering fact being known |
| Notification delivered (critical) within | ≤ 1 min of raise |
| Odoo sync freshness (current-day roster/attendance) | ≤ 2 min p95 |
| Crash-free desktop sessions | ≥ 99.5 % |

Error budgets are reviewed monthly; a breached budget pauses feature work in that area until reliability work lands.

## 4. Alerting

Symptom-based, never "a job ran":

| Alert | Condition | Action |
|---|---|---|
| API error rate | 5xx > 2 % for 5 min | Page |
| Dispatcher stalled | Lag > 15 min | Page |
| Tenant sync broken | No successful poll for 30 min, or webhook 401s | Notify ops + tenant admin |
| Critical notifications undelivered | Delivery failure > 5 % for 10 min | Page |
| Nightly adoption job failed | Any tenant failure | Ticket + retry |
| AI budget | 80 % of tenant monthly cap | Notify tenant admin |
| Backup/restore drill failure | Any | Ticket, high priority |
| Desktop crash spike | Crash-free < 99 % on a version | Halt channel promotion |

Every alert links to a runbook in `deployguard-platform/docs/runbooks/`.

## 5. Support diagnostics

- User-visible **reference codes** map to traces (NFR-14).
- Support view (permission-gated): recent client errors, sync status, device and app version, integration health for the tenant — metadata only, no work content.
- The desktop can produce a redacted diagnostics bundle the user reviews before sending.

## 6. Tenant-facing health

Tenant admins see: Odoo connection status, last webhook and poll time, backlog and dead letters, failed notification counts, and a simple "everything is current / delayed / broken" indicator, so a customer can tell whether an issue is theirs or ours.
