# DG-ADR-005 — Repository & Monorepo Strategy

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [19-backend-architecture](../19-backend-architecture.md), [DG-ADR-016](DG-ADR-016-web-framework.md), [DG-ADR-018](DG-ADR-018-odoo-bridge-addons.md)

## Context

The Platform has three deployable TypeScript apps (desktop, web, API/worker) that share contracts, UI, domain rules and an Odoo adapter. The DeployGuard ERP Odoo addons are Python and are deployed per client through existing scripts.

We need maximum reuse without an "abstraction maze" of dozens of tiny packages. We also need clear boundaries, fast CI, and no accidental coupling between the Platform release cycle and Odoo module deployments.

## Decision

1. **Create a new repository `deployguard-platform`**, a pnpm workspace orchestrated by **Turborepo**.
2. **Bridge addons stay in this Odoo repository** (`custom_addons/security_deployguard_*`), deployed with DeployGuard ERP ([DG-ADR-018](DG-ADR-018-odoo-bridge-addons.md)).
3. **Contracts cross the repo boundary as generated artefacts.** The Platform publishes the webhook and event JSON Schemas (generated from Zod) to a versioned directory. The bridge addon vendors a pinned copy for its contract tests.
4. **Planning documentation** stays in `docs/deployguard/` here until the Platform repo exists, then moves to `deployguard-platform/docs/`, leaving a pointer here.

### Structure

```
deployguard-platform/
├─ apps/
│  ├─ api/                    Fastify server + worker entrypoints (one codebase)
│  │  ├─ src/modules/         identity, tenancy, odoo-sync, work, training, competency,
│  │  │                       adoption, exceptions, notifications, feedback-support,
│  │  │                       knowledge, analytics, intelligence, audit, admin
│  │  ├─ src/platform/        http, db, events/outbox, jobs, auth, config, telemetry
│  │  ├─ src/server.ts
│  │  └─ src/worker.ts
│  ├─ desktop/                Tauri v2 (src-tauri Rust + thin Vite entry)
│  └─ web/                    Vite SPA entry (same app as desktop)
├─ packages/
│  ├─ app/                    shared screens, routes, nav catalogue, platform adapter (web|tauri)
│  ├─ ui/                     design tokens (ds/dgs verbatim), shell, components, Tailwind preset
│  ├─ contracts/              Zod schemas: API DTOs, event envelope + event types, webhook payloads
│  ├─ api-client/             generated typed client from OpenAPI
│  ├─ domain/                 pure, dependency-free rules: expected work, scoring, exception rules,
│  │                          recurrence, escalation ladders (unit-testable, shared by api & tests)
│  ├─ odoo/                   OdooAdapter (JSON-2 client, mappers, deep-link builder)
│  ├─ ai/                     AIProvider interface, Gemini provider, context assembler primitives
│  └─ config/                 eslint, stylelint, tsconfig, vitest presets
├─ tooling/                   codegen scripts, token-sync check, schema export
└─ docs/
```

**Rules that prevent the abstraction maze:**

- **Feature modules live inside `apps/api/src/modules/*`, not in `packages/`.** A new package is created only when code must be shared by at least two apps *today*.
- Maximum of ~8 packages; adding one requires a short ADR note.
- `packages/domain` has **no** I/O dependencies (no DB, HTTP or Tauri). It takes data in and returns decisions.
- Module boundary lint: `modules/a` may import only `modules/b/index.ts` (its public interface), never internal files.
- `packages/app` never imports `@tauri-apps/*` directly; it goes through `packages/app/src/platform/` adapters.

## Alternatives

| Option | Why not |
|---|---|
| Put the Platform inside this Odoo repo | Mixes Python addon deployment (rsync per client) with Node/Rust build pipelines; CI slows; the `.dockerignore`/image build for Odoo would need constant exclusions; unclear ownership. |
| Polyrepo (desktop, web, api separately) | Contract drift between repos; painful coordinated changes; no shared UI. |
| Nx | Capable but heavier conventions and plugins; Turborepo plus pnpm workspaces is sufficient at this size. |
| One package per feature (`packages/training`, `packages/tasks`, …) | Creates artificial boundaries and version churn; feature code is only used by the API. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Atomic changes across API, contracts, UI and desktop | Two repositories (Platform + ERP) to coordinate for bridge changes |
| Fast cached builds (Turborepo) | Some tooling setup cost in P0 |
| Clear seam between ERP and Platform release cycles | Contract artefacts must be versioned and vendored deliberately |

## Consequences

- CI pipelines: `lint → typecheck → unit → integration (Postgres) → contract (vs Odoo 19 container + bridge addon) → build (web, api image, Windows desktop)`.
- Semantic versioning for the webhook contract (`/api/deployguard/v1`) and the event schemas.
- The Odoo repo's CI gains a job running the bridge addon's tests against the vendored contract schemas.
