# DG-ADR-013 — Deployment & Hosting

- **Status:** Proposed (hosting provider pending OQ-1 budget and OQ-11 residency)
- **Date:** 2026-09-15
- **Related:** [26-deployment-strategy](../26-deployment-strategy.md), [DG-ADR-002](DG-ADR-002-backend-architecture.md), [DG-ADR-003](DG-ADR-003-database.md), [DG-ADR-010](DG-ADR-010-ai-architecture.md)

## Context

The Platform consists of:

- one container image with two entrypoints (API server, worker);
- PostgreSQL 16;
- object storage for evidence and training media;
- a static web app;
- a signed Windows desktop installer with an update feed.

Constraints and inputs:

- **Users** are in Southern Africa (Namibia first), so latency and residency point to a South African region.
- **Operations:** one engineer (A-7) needs managed services, backups, secrets and TLS with minimal toil.
- **Current production host:** DeployGuard ERP runs on a single VPS that is **shared with unrelated production stacks**. Adding the Platform there would enlarge the blast radius of any incident and couple resource contention.
- **AI:** Gemini is the default AI provider (R-4).

## Decision

1. **Separate hosting from the ERP production VPS.** The Platform never runs on the shared DogForce Odoo host.
2. **Recommended primary option: Google Cloud, `africa-south1` (Johannesburg):**

   | Component | Service |
   |---|---|
   | API server | Cloud Run service (min instances 1, autoscale) |
   | Worker | Cloud Run service with always-allocated CPU, min 1, max N (pg-boss consumers) — or a small managed instance group if long-lived connections prove problematic |
   | Database | Cloud SQL for PostgreSQL 16, HA configuration from pilot onward, automated backups + PITR, private IP |
   | Object storage | Cloud Storage (evidence, media, desktop update artefacts), CMEK optional |
   | Secrets & keys | Secret Manager + Cloud KMS (tenant data-key wrapping, DG-ADR-008) |
   | Edge | HTTPS load balancer or Cloud Run domain mapping; Cloud Armor rate limiting/WAF for the API |
   | Static web | Cloud Storage + Cloud CDN (or Firebase Hosting) |
   | AI | Gemini via **Vertex AI** (enterprise terms, regional processing options; OQ-15) |

   Rationale: managed PostgreSQL with PITR in-region, serverless containers with low toil, KMS, and a single commercial relationship with the default AI provider.

3. **Portable by construction.** Everything is containers, standard PostgreSQL, S3-compatible object-storage abstraction, OTel telemetry and env-var configuration. **Fallback option:** two VMs in a South African region (Azure South Africa North or AWS af-south-1 equivalents) with Docker Compose, managed PostgreSQL, and Caddy/nginx. The Terraform module structure keeps provider specifics in one layer.
4. **Environments:** `local` (compose: postgres, api, worker, odoo:19 with bridge addons, mail catcher), `staging` (separate project, connected to DeployGuard ERP **staging**), `production`. Each has its own secrets, keys and AI budget.
5. **Infrastructure as code:** Terraform. There is no hand-configured production resource.
6. **CI/CD** (GitHub Actions):
   - PR: lint, typecheck, test, contract tests, build.
   - `main`: deploy to staging automatically, including migrations run as a one-off job before rollout, with an expand/contract pattern.
   - Tagged release: deploy to production with manual approval.
7. **Desktop distribution:**
   - Windows NSIS/MSI installer built on Windows CI runners.
   - Code-signed (OQ-7).
   - Tauri updater artefacts signed with the updater key, held in the CI secret store with offline backup.
   - Update feed JSON on object storage/CDN with **channels** `pilot` and `stable`.
   - Staged rollout: pilot users first, then stable after 48 h without regressions.
8. **Backups & DR:**
   - DB PITR (7–35 days) plus a daily logical export per tenant to a separate bucket with retention lock.
   - Object versioning on evidence.
   - Monthly restore drill.
   - RPO ≤ 15 min, RTO ≤ 4 h for MVP.

## Alternatives

| Option | Why not (primary) |
|---|---|
| Run the Platform on the existing DogForce production VPS | Shared with unrelated stacks; single point of failure; resource contention; no managed PITR. |
| Kubernetes (GKE/EKS/AKS) | Premature operational complexity for two services. |
| Fly.io | Simple, but its Johannesburg footprint and managed PostgreSQL maturity in-region are less certain; the existing repo's Fly setup is stale. |
| Render / Railway | Limited or no African regions; latency and residency. |
| Azure South Africa North (Container Apps + Flexible Server) | A strong alternative with equivalent services; chosen as fallback rather than primary only because of Vertex/Gemini consolidation. Viable if DogForce or future customers prefer Microsoft. |
| AWS af-south-1 | Viable; generally higher regional pricing; Gemini outside the provider. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Managed DB, secrets, TLS and scaling with little toil | Cloud costs above a bare VPS (estimate before P0, OQ-1) |
| Clear isolation from ERP infrastructure | Cross-provider latency between the Platform (GCP JNB) and each tenant's Odoo host |
| Regional proximity | Some managed features may lag in `africa-south1`; verify service availability before P0 |

## Consequences

- **Before P0:** confirm budget and residency (OQ-1, OQ-11), verify service availability in `africa-south1`, and produce a monthly cost estimate for pilot scale.
- **Terraform modules:** `network`, `database`, `run-services`, `storage`, `secrets-kms`, `edge`, `observability`.
- **DeployGuard ERP staging must be running** (currently stopped) for the Platform staging environment (rollout Stage 0).
