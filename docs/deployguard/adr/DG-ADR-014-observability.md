# DG-ADR-014 — Observability

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [27-observability](../27-observability.md), [DG-ADR-013](DG-ADR-013-deployment.md), [23-audit-system](../23-audit-system.md)

## Context

A single engineer must operate the Platform for a production customer. Failures span:

- desktop (Rust + WebView);
- web;
- API;
- worker;
- event dispatch;
- Odoo webhooks and polling on customer infrastructure;
- email;
- AI providers.

Support must be able to turn a user's "it didn't work" into a trace (NFR-14). Privacy rules forbid leaking employee data into third-party telemetry.

## Decision

1. **OpenTelemetry** as the instrumentation standard:
   - Node SDK auto-instrumentation (HTTP, Fastify, pg);
   - manual spans for domain operations: event dispatch per consumer, scoring runs, exception rule evaluation, Odoo adapter calls, AI runs.
   - Export via OTLP to the hosting provider's backend (Cloud Trace / Monitoring / Logging on the primary option). The collector configuration keeps backends swappable.
2. **Sentry** for error monitoring and release health on all clients and services:
   - `@sentry/react` (web and desktop WebView);
   - the Rust `sentry` crate (Tauri core);
   - `@sentry/node` (API and worker).
   - Source maps and debug symbols uploaded in CI.
   - `beforeSend` scrubbing removes PII; `sendDefaultPii` is off.
3. **Correlation:**
   - Every client request carries `traceparent` (W3C Trace Context) and an `X-DG-Correlation-Id`.
   - Events store `correlation_id`.
   - User-facing errors display a short **reference code**, derived from the trace ID, which support can look up.
4. **Structured logs:**
   - pino JSON logs with `trace_id`, `span_id`, `tenant_id`, `module`, `event_type`.
   - **Never** event `data`, free text, tokens, or personal fields.
   - Log levels are configurable per module at runtime.
5. **Metrics:**
   - **RED** (rate, errors, duration) per route.
   - Plus the domain SLIs:
     - event dispatcher lag per consumer;
     - Odoo webhook delivery lag and poll lag per tenant;
     - outbox dead letters (reported by the bridge health endpoint);
     - adoption snapshot job duration and success;
     - notification delivery success per channel;
     - AI latency, error rate and cost per capability and tenant;
     - desktop update adoption per version.
6. **SLOs and alerting** ([27](../27-observability.md) §4): symptom-based alerts only, routed to the on-call email/phone channel. An error-budget review happens monthly.
7. **Tenant-facing health:** the integration health page (PR-ODO-06) reads the same metrics.
8. **Audit ≠ observability.** Audit records are domain data in PostgreSQL with retention rules ([23](../23-audit-system.md)); telemetry is operational and short-lived (30 days traces/logs by default).

## Alternatives

| Option | Why not |
|---|---|
| Provider-native SDKs only (no OTel) | Lock-in; harder to move hosting (DG-ADR-013 portability). |
| Self-hosted Grafana/Prometheus/Loki/Tempo | Operational burden for one engineer; revisit only if cost demands it. |
| Datadog / New Relic all-in-one | Strong products, but cost scales quickly and more employee-data exposure surface; Sentry + OTel covers needs. |
| Logs only | Insufficient for cross-system latency and failure analysis. |

## Tradeoffs

| We gain | We accept |
|---|---|
| End-to-end traceability, desktop to Odoo | Instrumentation effort; sampling configuration to control cost |
| Vendor flexibility | Two tools (OTel backend + Sentry) |
| Privacy-safe telemetry by default | Some debugging requires audit/DB access under break-glass rather than logs |

## Consequences

- **P0:** telemetry bootstrap in `apps/api/src/platform/telemetry` and the Sentry setup for web.
- **P2:** desktop Rust and WebView Sentry, and the reference-code error component.
- **Runbooks** for top alerts live in `deployguard-platform/docs/runbooks/`.
