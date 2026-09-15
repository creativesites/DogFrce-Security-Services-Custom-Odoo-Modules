# 26 — Deployment Strategy

> Status: Draft · Owner: Platform engineering · Decision: [DG-ADR-013](adr/DG-ADR-013-deployment.md)

---

## 1. Environments

| Environment | Purpose | Data | ERP it talks to |
|---|---|---|---|
| `local` | Development | Seeded fixtures | Local `odoo:19` container with bridge addons |
| `staging` | Integration and release validation | Synthetic tenant only | **DeployGuard ERP staging** (must be restarted — it has been down; Stage 0) |
| `production` | Live tenants | Customer data | Each tenant's production Odoo |

No environment ever connects to another environment's ERP. Production credentials exist only in production secret storage.

## 2. Topology (primary option)

```
Clients ──HTTPS──> Edge (LB + WAF/rate limit)
                     ├─> api service (containers, autoscaled, min 1)
                     └─> web static assets (CDN)
api/worker ──> PostgreSQL 16 (managed, HA, PITR, private networking)
           ├─> Object storage (evidence, media, desktop artefacts)
           ├─> Secret Manager + KMS
           └─> Outbound: tenant Odoo (HTTPS), email provider, AI provider
worker      (containers, min 1, always-on CPU): dispatcher, schedules, queues
```

Region: South Africa (Johannesburg) per [DG-ADR-013](adr/DG-ADR-013-deployment.md), pending OQ-1/OQ-11.

## 3. Build and release

| Trigger | Pipeline |
|---|---|
| PR | lint → typecheck → unit → integration (PostgreSQL) → contract (API + Odoo container) → build artefacts → E2E smoke |
| Merge to `main` | Build immutable image (SHA tag) → deploy to staging → run migrations job → E2E full → visual parity → performance smoke |
| Tag `vX.Y.Z` | Manual approval → production migration job → rolling deploy → post-deploy checks → desktop artefacts published to the `pilot` channel |
| Promotion | After 48 h without regression, promote the desktop build to `stable`; the API has no separate promotion (single production version) |

**Migrations** follow expand → migrate → contract, so a running old version tolerates the new schema. Destructive changes wait one release. Every migration is reversible or has a documented forward fix.

## 4. Desktop distribution

- Built on Windows CI runners; NSIS (per-user) plus optional MSI for managed fleets.
- Code signing (OQ-7) before pilot; unsigned builds are development-only.
- Tauri updater manifests signed with the updater key; artefacts in object storage behind CDN.
- Channels `pilot` / `stable`; `min_supported_client` enforced by the API.
- Release notes are user-facing and written in plain language; the app shows "What's new" after an update.

## 5. Configuration and secrets

- Infrastructure config via environment variables from the secret manager; no secrets in images or repos.
- Tenant behaviour is database configuration ([15](15-multi-tenancy.md) §4), never environment variables.
- Rotation runbooks for every secret class ([16](16-security-architecture.md) §6).

## 6. Backups and disaster recovery

| Item | Mechanism | Target |
|---|---|---|
| PostgreSQL | Managed automated backups + PITR (7–35 days) | RPO ≤ 15 min |
| Per-tenant logical export | Nightly, to a separate bucket with retention lock | Tenant restore without full-cluster rollback |
| Object storage | Versioning + lifecycle rules | Accidental deletion recovery |
| Secrets/keys | KMS with versioning; offline copy of the updater key | Key loss prevention |
| Restore drill | Monthly restore into a scratch project; documented time | RTO ≤ 4 h |

## 7. Relationship to DeployGuard ERP deployment

The Platform does **not** change how ERP modules deploy (rsync/zip + container restart, `promote_staging_to_prod.sh`). Two coupling points:

1. **Bridge addon releases** must be compatible with the Platform contract version in production; the Platform reports unsupported contracts as a health alert.
2. **Per-client module baselines** replace `security_suite` (R-5). Each client's baseline lists ERP modules plus the bridge addons they install — for DogForce (Namibia), including `security_shell` and excluding Zambia-only modules.

**Rollback:** Platform rolls back by redeploying the previous image (schema permitting, per expand/contract). ERP rollback remains the existing snapshot procedure — noting that the current promotion script does *not* auto-restore its snapshot ([00](00-current-state.md) §2), which Stage 0 should either fix or document accurately.
