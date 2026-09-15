# 24 — API Design

> Status: Draft · Owner: Platform engineering · Decisions: [DG-ADR-002](adr/DG-ADR-002-backend-architecture.md), [DG-ADR-007](adr/DG-ADR-007-authentication.md)

---

## 1. Style

- REST-ish resource routes over HTTPS, JSON only, contract-first from Zod → OpenAPI 3.1 → generated TypeScript client.
- Versioned prefix `/v1`. Breaking changes create `/v2`; additive changes do not.
- Commands that are not CRUD use explicit action routes: `POST /v1/work/checklists/{id}:submit`.
- All list endpoints: cursor pagination, `limit` (≤ 200), stable sort, filter allowlist.
- Timestamps ISO-8601 UTC; IDs UUIDv7 strings; money never appears in the Platform API (ERP concern).

## 2. Authentication & headers

| Header | Purpose |
|---|---|
| `Authorization: Bearer <access token>` | All authenticated calls (desktop and web) |
| Refresh cookie (web) / IPC-held token (desktop) | Token renewal only, on `/v1/auth/*` |
| `X-DG-Correlation-Id` | Client-generated per user intent; echoed in responses and logs |
| `X-DG-Client` | `desktop/0.4.2` or `web/0.4.2`; used for min-version enforcement |
| `Idempotency-Key` | Required on all non-idempotent commands from clients |

## 3. Endpoint groups

| Group | Examples |
|---|---|
| Discovery | `GET /v1/tenants:discover?company_code=` (public, rate-limited, returns Odoo URL + branding) |
| Auth | `POST /v1/auth/exchange` (assertion → tokens), `POST /v1/auth/refresh`, `POST /v1/auth/logout`, `GET /v1/auth/session` |
| Me | `GET /v1/me`, `GET /v1/me/home`, `GET /v1/me/training`, `GET /v1/me/adoption` (policy-gated) |
| Work | `GET /v1/work/tasks`, `POST /v1/work/tasks`, `GET/POST /v1/work/checklists/{id}`, `:start`, `:submit`, `:verify`, `:reject`, `:could-not-complete` |
| Templates | `GET/POST /v1/work/templates`, `:publish`, `GET /v1/work/schedules` |
| Training | `/v1/training/courses`, `/versions`, `:publish`, `/assignments`, `/attempts`, `:submit` |
| Competency | `/v1/competency/framework`, `/evidence`, `/status`, `/certifications` |
| Adoption | `/v1/adoption/snapshots`, `/factors`, `/checkins/{id}:respond` |
| Exceptions | `/v1/exceptions`, `:acknowledge`, `:resolve`, `:dismiss`, `:reassign`, `/rules` |
| Notifications | `/v1/notifications`, `:read`, `/preferences` |
| Feedback & support | `/v1/feedback`, `/v1/support/requests`, `/messages` |
| Knowledge | `/v1/knowledge/articles`, `?route=`, `?workflow=` |
| Odoo | `POST /v1/odoo/open` (SSO ticket broker), `GET /v1/odoo/health` |
| Integrations (inbound) | `POST /v1/integrations/odoo/webhooks` (HMAC-signed, no user token) |
| Events | `POST /v1/events:batch` |
| Sync (desktop) | `POST /v1/sync/commands`, `GET /v1/sync/bootstrap?since=` |
| Files | `POST /v1/files:presign`, `POST /v1/files/{id}:complete` |
| Stream | `GET /v1/stream` (SSE) |
| Admin | `/v1/admin/*` (users, roles, connection, rules, config, audit, exports) |

## 4. Idempotency

- `Idempotency-Key` (client UUIDv7) is stored per tenant with the request fingerprint and response for 24 hours.
- Same key + same fingerprint → original response replayed.
- Same key + different fingerprint → `409 idempotency_key_reuse`.
- Offline sync commands use `command_id` as the key ([20](20-offline-strategy.md) §4).

## 5. Errors

```json
{
  "error": {
    "code": "conflict.already_completed",
    "message": "This checklist was already submitted.",
    "reference": "DG-7F3K2M",
    "details": { "completed_by": "…", "completed_at": "2026-09-16T10:04:11Z" },
    "correlation_id": "0192f1a2-…"
  }
}
```

| Family | HTTP | Examples |
|---|---|---|
| `validation.*` | 400 | `validation.failed`, `validation.unknown_event_type` |
| `auth.*` | 401 | `auth.token_expired`, `auth.assertion_invalid`, `auth.mfa_required` |
| `permission.*` | 403 | `permission.denied`, `permission.out_of_scope` |
| `not_found.*` | 404 | `not_found.resource` |
| `conflict.*` | 409 | `conflict.already_completed`, `conflict.reassigned`, `conflict.version` |
| `rate_limit.*` | 429 | with `Retry-After` |
| `dependency.*` | 424/503 | `dependency.odoo_unavailable`, `dependency.ai_unavailable` |
| `internal.*` | 500 | reference code only, never internal details |

Every error carries a short `reference` derived from the trace id, which support can resolve (NFR-14).

## 6. Webhook contract (Odoo → Platform)

Specified in [12](12-odoo-integration.md) §4: `X-DG-Signature` (timestamped HMAC-SHA256), `X-DG-Contract`, batch of ≤ 200 events, `202` with per-event results, 5-minute clock tolerance, duplicate `event_id` accepted as no-op.

## 7. Compatibility rules

- Additive fields only within a version; clients ignore unknown fields.
- Deprecations announced in `Sunset` headers and the changelog, minimum one release cycle.
- `min_supported_client` is enforced server-side; older clients get `426 upgrade_required` with an upgrade route.
- The generated client is published per API release; contract tests verify old clients against new servers for N-1.
