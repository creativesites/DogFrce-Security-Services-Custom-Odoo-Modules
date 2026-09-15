# BUILD-ORDER — Recommended Implementation Sequence

> Status: Draft · Owner: Platform engineering
>
> Ordered to minimise rework: tenancy, events and audit exist before any module emits; the bridge and identity exist before any screen needs data; deterministic value ships before AI. Requirement IDs refer to [02](02-product-requirements.md); phases map to milestones in [29](29-roadmap.md).
>
> **Stage 0 prerequisites** ([31](31-dogforce-rollout.md) §2) run in parallel from day one. P1 cannot complete without items 3, 5 and 10.

---

## P0 — Foundations

**Objective:** an empty but production-shaped platform: one tenant, one signed-in test user path, events, audit, CI/CD, design tokens.

| Aspect | Work |
|---|---|
| **Dependencies** | OQ-1 (hosting/budget), OQ-2 (naming), OQ-11 (residency) |
| **Features** | Nothing user-facing |
| **Database** | `tenant`, `tenant_config`, `user`, `role`, `role_assignment`, `team`, `reporting_line`, `device`, `session`, `event` (partitioned), `event_consumer_checkpoint`, `audit_log`, `file_object`, pg-boss schema. RLS enabled + **forced** on every tenant table |
| **API** | Fastify skeleton, Zod→OpenAPI pipeline, error taxonomy, correlation IDs, health/version endpoints, rate limiting |
| **Worker** | Event dispatcher with checkpoints, pg-boss wiring, retention job skeleton |
| **Frontend** | `packages/ui`: verbatim token port + Tailwind preset + lint rules + first shell primitives (Rail, NavPanel, Card, Tile, Pill, Num); component catalogue with axe checks |
| **Desktop** | Not yet |
| **Infra** | Terraform modules, container build, staging + production environments, secrets/KMS, OTel + Sentry bootstrap, backups configured |
| **Testing** | Unit + integration harness (Testcontainers PostgreSQL), **RLS conformance test**, token-drift check for design tokens, CI pipeline green |
| **Acceptance** | A seeded tenant exists; an event written in a transaction reaches a test consumer; an audit row is written and cannot be updated or deleted; CI blocks a hardcoded hex colour and an `!important`; staging deploys automatically from `main` |

## P1 — Odoo bridge, identity source and projections

**Objective:** DeployGuard knows who people are and what the ERP says — and **baseline adoption measurement starts** even before any UI exists.

| Aspect | Work |
|---|---|
| **Dependencies** | P0; Stage 0 items 3 (HTTPS), 5 (Odoo users), 10 (ERP staging) |
| **Features** | Connection setup, initial sync, identity linking, integration health |
| **ERP (this repo)** | `security_deployguard_bridge`: config + key management, integration user/group, `security.deployguard.api` facade, outbox + delivery cron, HMAC signing, **auth/login + totp + sso/ticket + sso/consume**, audit, health. Bus **subscriber registry** refactor in `security_base` (fixes D-4). Domain bridges: attendance, roster, incidents, leave, notifications |
| **Database** | `odoo_connection`, `identity_link`, projections (`site`, `employee`, `shift`, `attendance_batch`, `incident`, `leave`, `alert`), `site_settings`, `sync_watermark`, `sync_run`, `webhook_delivery` |
| **API** | `POST /v1/integrations/odoo/webhooks`, `POST /v1/auth/exchange`, `/v1/auth/refresh`, `/v1/admin/integrations/*`, `GET /v1/odoo/health` |
| **Worker** | Pollers per entity with watermarks, projection upserts, `odoo.*` event emission, circuit breaker, health metrics |
| **Frontend** | Admin: connection setup, health page, identity mapping review (web) |
| **Testing** | Contract tests against a real Odoo 19 container with the bridge installed; signature/replay/skew tests; ticket single-use and expiry; throttling; projection idempotency; Odoo addon unit tests in the ERP repo CI |
| **Acceptance** | Webhook and poll both produce identical projections; killing webhooks for an hour self-heals via polling; a deactivated Odoo user's link is flagged within 5 minutes; **baseline `workflow_coverage` for the 5 MVP workflows is computable from ERP history** |

## P2 — Desktop shell, single login, notifications

**Objective:** pilot users can sign in once and see a real (if sparse) Home.

| Aspect | Work |
|---|---|
| **Dependencies** | P1; OQ-7 (code signing started), OQ-10 (email), OQ-20 (TOTP policy) |
| **Features** | PR-IAM-02/05/06/09/11, PR-WS-01–04 (skeleton), PR-NTF-01–03 |
| **Database** | `notification`, `notification_delivery`, `notification_preference`, `policy_acknowledgement` |
| **API** | `/v1/tenants:discover`, `/v1/me`, `/v1/me/home`, `/v1/odoo/open`, `/v1/notifications*`, `/v1/stream` (SSE), `/v1/events:batch` |
| **Frontend** | Full shell with `security_shell` parity (rail, nav panel, canvas, ⌘K palette, profile card, loading bar), Home skeleton, notification centre, preferences, error/empty/offline states, monitoring-notice acknowledgement |
| **Desktop** | Tauri app: keychain, device keypair, SQLCipher store, token refresh in Rust, OS notifications, tray/autostart, deep links, **Odoo window with zero IPC**, updater, Sentry, diagnostics bundle |
| **Testing** | E2E: first run → company code → sign-in (+TOTP) → device registered → Home; Open in Odoo lands on a record; revocation locks the client; Rust unit tests; **visual parity screenshots vs `security_shell`** |
| **Acceptance** | A pilot user installs and signs in unaided; no second login anywhere, including Odoo; notifications arrive on desktop; update from version N→N+1 succeeds on a test machine |

## P3 — Training core

**Objective:** the DogForce course pack can be authored, assigned, taken and verified.

| Aspect | Work |
|---|---|
| **Dependencies** | P2; content from the ops manager (OQ-19); approver named (R-8) |
| **Features** | PR-TRN-01–05, 11; PR-WS-06 (training part) |
| **Database** | `training_program`, `course`, `course_version`, `course_section`, `lesson`, `assessment`, `question`, `question_bank`, `training_assignment`, `lesson_progress`, `attempt`, `attempt_answer`, `competency*`, `competency_evidence`, `role_competency_requirement` |
| **API** | `/v1/training/*`, `/v1/competency/*`, authoring endpoints with draft→review→publish |
| **Frontend** | My training, lesson player, assessment runner with feedback, practical sign-off, authoring UI, assignment/compliance views |
| **Desktop** | Lesson content caching for later offline (read-only in MVP) |
| **Testing** | Version pinning (assignment keeps its version through a publish), pass/fail paths, attempt limits, competency evidence from verification, authoring permissions |
| **Acceptance** | Courses 1–3 authored, approved, assigned; a supervisor completes one end-to-end; a practical sign-off produces level-3 competency evidence with a link to the real record |

## P4 — Work management

**Objective:** recurring, evidence-backed work runs — including auto-completion from ERP facts.

| Aspect | Work |
|---|---|
| **Dependencies** | P1 (shift projections), P2 |
| **Features** | PR-WRK-01–06, 08, 09 (3 templates); PR-OFF-01, 02 |
| **Database** | `task_template`, `checklist_template`, `checklist_item_def`, `schedule_rule`, `task`, `checklist_instance`, `checklist_response`, `evidence_attachment`, `verification`, `comment` |
| **API** | `/v1/work/*` including `:start`, `:submit`, `:verify`, `:reject`, `:could-not-complete`; `/v1/sync/commands`, `/v1/sync/bootstrap`, `/v1/files:presign` |
| **Worker** | Recurrence materialisation (7-day horizon), roster-change reconciliation, overdue sweeps, auto-complete matching from `odoo.*` events |
| **Frontend** | My work, checklist runner with evidence capture, task detail, verify queue, template + schedule admin |
| **Desktop** | Offline cache and **command outbox** with conflict handling; evidence capture, compression, encryption, resumable upload |
| **Testing** | Every conflict row in [20](20-offline-strategy.md) §5; recurrence idempotency; auto-complete matching; verification permissions; airplane-mode soak |
| **Acceptance** | `attendance.post`, `site.visit`, `incident.review` generate correctly for a real week of DogForce roster data; posting a batch in Odoo auto-completes the expected item within 2 minutes; an offline checklist syncs and never shows false success |

## P5 — Adoption engine

**Objective:** honest, explainable adoption measurement with the assistance loop.

| Aspect | Work |
|---|---|
| **Dependencies** | P4 (work), P1 (ERP facts), OQ-6 (privacy sign-off), OQ-13 (visibility policy) |
| **Features** | PR-ADO-01–07 |
| **Database** | `expected_work_definition`, `expected_work_item`, `adoption_snapshot`, `score_factor`, `abandonment_signal`, `checkin` |
| **API** | `/v1/adoption/*`, `/v1/adoption/checkins/{id}:respond`, `/v1/me/adoption` |
| **Worker** | Nightly materialisation and scoring per tenant timezone; excusal resolution (leave/absence/fault); abandonment detection with investigation checks; check-in dispatch |
| **Domain** | `packages/domain/adoption`: expected work, factors, weights, confidence, baselines — pure and fixture-tested |
| **Frontend** | Adoption overview, explanation screen with evidence, check-in dialog, own-score view |
| **Testing** | Fixture month → expected snapshots; excusal correctness (leave, fault, roster change); retroactive fault excusal restores scores; confidence gating; no score for < 5 items |
| **Acceptance** | Every score on screen can be explained down to individual events and missing items; a resolved `platform_fault` support request visibly restores prior scores |

## P6 — Exceptions, inbox, escalations

**Objective:** management starts the day in one ranked list.

| Aspect | Work |
|---|---|
| **Dependencies** | P4, P5, P2 (notifications) |
| **Features** | PR-EXC-01–04, PR-INB-01/02, PR-NTF-04 |
| **Database** | `exception_rule`, `exception`, `exception_evidence`, `exception_timeline_entry`, `escalation_policy` |
| **API** | `/v1/exceptions*` with `:acknowledge`, `:resolve`, `:dismiss`, `:reassign`; `/v1/admin/rules*` |
| **Worker** | Rule evaluation on events and schedules, dedupe, auto-resolve, escalation scheduling and cancellation, stale-data pausing |
| **Frontend** | Manager inbox (Critical/Attention/Watch) with keyboard triage, exception detail with evidence and recommended action, scoped supervisor inbox, rule admin |
| **Testing** | Each MVP rule with positive/negative fixtures; dedupe and recurrence; escalation timing against the working calendar; pause on stale projections; dismissal permissions and audit |
| **Acceptance** | A missing night supervisor raises Critical within 2 minutes and escalates on schedule; acknowledging stops escalation; the inbox is empty when nothing needs a human |

## P7 — Feedback & support

**Objective:** the assist path is complete, and faults stop penalising people.

| Aspect | Work |
|---|---|
| **Dependencies** | P4, P6 |
| **Features** | PR-FBK-01–03, PR-SUP-01, 02 |
| **Database** | `feedback`, `support_request`, `support_message`, `knowledge_article`, `article_version`, `article_target` |
| **API** | `/v1/feedback`, `/v1/support/*`, `/v1/knowledge/*` |
| **Frontend** | Post-task feedback, "Something's wrong" with auto-context, my requests, support queue, contextual help panel, article reader |
| **Worker** | SLA timers, recurring-issue detection, fault-excusal propagation to adoption |
| **Testing** | Context capture completeness and redaction; `platform_fault` resolution → retroactive excusal; article targeting by route/workflow |
| **Acceptance** | A blocked supervisor reports a problem in under 20 seconds with full context; resolving it as a fault restores their coverage figures and closes the linked abandonment signal |

## P8 — Owner view, digests, analytics

**Objective:** the owner sees operational health weekly without asking anyone.

| Aspect | Work |
|---|---|
| **Dependencies** | P5, P6 |
| **Features** | PR-EXE-01, PR-ANL-01 |
| **Database** | `metric_daily` rollups |
| **API** | `/v1/analytics/*`, `/v1/digests/*` |
| **Worker** | Nightly rollups, weekly digest composition and send |
| **Frontend** | Owner overview tiles, digest view, drill-downs, exports with metric definitions |
| **Testing** | Metric definitions match drill-down data exactly; digest links resolve; export permissions and audit |
| **Acceptance** | The weekly digest's every number is reproducible from a drill-down; owner can reach the evidence in two clicks |

## P9 — AI intelligence layer (V1)

**Objective:** explanations and briefs on top of trustworthy deterministic data.

| Aspect | Work |
|---|---|
| **Dependencies** | P8, pilot data, OQ-6 and OQ-15 closed |
| **Features** | PR-AI-01–05, PR-INB-03, PR-EXE-02, PR-SUP-03/04, PR-TRN-07 |
| **Database** | `ai_capability_config`, `ai_run`, `ai_insight`, `ai_recommendation`, `ai_feedback`; pgvector for knowledge retrieval |
| **API** | `/v1/intelligence/*`, approval endpoints |
| **Worker** | Capability triggers, context assembly, provider calls, validation, budget enforcement |
| **Frontend** | Insight cards with citations and confidence, "Why am I seeing this?", approve/edit/dismiss, AI admin (toggles, budgets, spend) |
| **Testing** | Eval sets per capability (schema, citation integrity, numeric fidelity, refusal on thin evidence, tone); prompt change blocks merge on regression; budget cutoff behaviour |
| **Acceptance** | Every AI statement links to evidence the reader can open; disabling AI leaves all deterministic features intact; no output contains a number absent from the facts block |

## P10 — Pilot hardening

**Objective:** ship to real users safely.

| Aspect | Work |
|---|---|
| **Dependencies** | P6 minimum (P9 not required) |
| **Work** | Independent security review of auth + bridge; performance gates ([25](25-testing-strategy.md) §4); Windows code signing and staged channels; runbooks and alerts; restore drill; per-tenant export tool; accessibility audit; content and copy review; pilot user training sessions |
| **Acceptance** | All NFR gates met; restore drill completed within RTO; zero open P1 defects; rollout Stage 2 can begin |

---

## Cross-phase rules

1. **No phase ships without its tests** (the acceptance row is the definition of done).
2. **Every phase emits events and audit** from the start, never "added later".
3. **Every screen implements all required states** ([05](05-ux-principles.md) §6) before review.
4. **Tenant configuration over code** in every phase; the productization checklist ([30](30-productization.md) §7) runs at each phase end.
5. **Contract changes** (API, events, webhooks) bump versions and update the vendored schemas in the ERP repo in the same change set.
6. **Each phase updates these docs** — planning documents are living, and a phase that changes a decision updates the ADR rather than diverging silently.
