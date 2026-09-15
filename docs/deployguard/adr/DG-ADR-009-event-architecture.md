# DG-ADR-009 — Event Architecture

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [13-event-architecture](../13-event-architecture.md), [09-adoption-engine](../09-adoption-engine.md), [10-exception-engine](../10-exception-engine.md), [DG-ADR-003](DG-ADR-003-database.md), [DG-ADR-006](DG-ADR-006-odoo-integration.md)

## Context

Events are central to the product:

- the adoption engine measures behaviour from them;
- exceptions and escalations react to them;
- notifications fan out from them;
- AI cites them as evidence;
- audit and analytics depend on them.

Events arrive from four sources:

1. Platform domain modules (e.g. `checklist.instance.submitted`);
2. desktop and web clients (e.g. `workflow.abandoned`, `client.error`), possibly in offline batches;
3. Odoo bridge webhooks (e.g. `odoo.attendance.batch.submitted`);
4. scheduled detectors (e.g. `task.overdue`).

Requirements:

- at-least-once delivery with idempotent consumers;
- replay after fixing a scoring bug;
- ordering per subject where it matters;
- privacy classification and retention;
- no event-infrastructure operations burden (A-7).

Existing DeployGuard ERP ADRs reject a separate event bus. The Odoo bus (`security.event.log`) dispatches synchronously to a hardcoded list.

## Decision

A **PostgreSQL-native event log with a transactional outbox**. This is *not* event sourcing of aggregates.

1. **State stays relational.** Modules persist aggregates normally, and emit immutable events describing facts that happened.
2. **Transactional outbox.** A domain command writes its state change **and** its event rows to `event` in the same transaction, so no event is lost or phantom.
3. **Event store = `event` table**:
   - append-only;
   - partitioned monthly;
   - envelope columns indexed: `tenant_id`, `type`, `occurred_at`, `subject_type/subject_id`, `actor_id`, `correlation_id`;
   - `data` in JSONB;
   - a unique `(tenant_id, idempotency_key)` constraint for externally submitted events.
4. **Dispatch.**
   - A lightweight dispatcher in the worker reads new events by `global_seq` (bigserial) after the last checkpoint of each **consumer**. Consumers: `projections`, `adoption`, `exceptions`, `notifications`, `work-autocomplete`, `analytics`, `intelligence-triggers`.
   - Each consumer has its own checkpoint in `event_consumer_checkpoint` and processes idempotently (dedupe table `(consumer, event_id)` for side-effecting consumers).
   - `LISTEN/NOTIFY` wakes the dispatcher promptly; polling (every 2 s) is the fallback.
5. **Work queues.** Heavy or retryable work (send email, call Gemini, poll Odoo) is enqueued via **pg-boss** jobs from consumers, with retries and dead-lettering.
6. **Client ingestion.**
   - `POST /v1/events:batch` accepts up to 500 client events.
   - Each event carries a client-generated UUIDv7 `id` and `idempotency_key`.
   - The server validates against registered schemas, stamps `recorded_at` and trusted actor/tenant/device from the token (clients cannot assert actor identity), and rejects unknown types.
7. **Odoo ingestion.** Webhook batches are verified (HMAC), then converted to `odoo.*` events with `source.system = "odoo"` and an `odoo` block (model, res_id, write_date).
8. **Schema governance.** Every event type is a versioned Zod schema in `packages/contracts/events` (`type` + `version`). Breaking changes create a new version; consumers support N and N-1.
9. **Replay.** Consumer checkpoints can be reset for a tenant and time range. Derived tables (projections, scores) are rebuilt deterministically from events plus projections. Side-effecting consumers (notifications) are never replayed; they are skipped by a replay flag.
10. **Retention.** Per privacy class and type (defaults in [13](../13-event-architecture.md) §8). Raw client telemetry is shortest; audit-relevant events are retained per [23](../23-audit-system.md).

## Alternatives

| Option | Why not (now) |
|---|---|
| Kafka / Redpanda | Excellent at massive scale; unnecessary operations and cost at our volumes; still needs an outbox for consistency. |
| Redis Streams / BullMQ | Adds a second datastore; durability and replay weaker than PostgreSQL for audit-relevant events. |
| NATS JetStream | Lightweight but still extra infrastructure; no transactional coupling with our writes. |
| EventStoreDB / full event sourcing | Aggregate rebuild complexity for CRUD-heavy domains (courses, templates) with no product benefit. |
| `LISTEN/NOTIFY` only | Not durable; messages lost when no listener. Used only as a wake-up signal. |
| CDC on the Platform DB (Debezium) | Operational weight; events would mirror table changes instead of domain intent. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Transactional consistency between state and events | Throughput ceiling of a single PostgreSQL primary (ample for A-6); partition maintenance jobs |
| Replayable, auditable history in one datastore | Consumers must be idempotent (enforced by tests) |
| Zero extra infrastructure | Dispatcher is our code (small, well-tested) |

## Consequences

- `apps/api/src/platform/events/`: `emit()` (transaction-bound), dispatcher, checkpoint store, replay tool, schema registry.
- **Load test gate before pilot:** 50 events/s sustained with dispatcher lag p95 < 5 s.
- **Revisit trigger:** sustained > 1 000 events/s platform-wide, or consumer lag breaching SLO after vertical scaling. Then evaluate moving the transport to NATS or Kafka while keeping the outbox and envelope.
