# 06 — Feature Map

> Status: Draft · Owner: Product
>
> Capability × role × release. This is the canonical list of *what* ships *when*. [28-mvp-scope](28-mvp-scope.md) explains the boundary; [BUILD-ORDER](BUILD-ORDER.md) sequences the MVP items. Requirement IDs refer to [02](02-product-requirements.md).
>
> Roles: **Sup** Site Supervisor · **Ops** Operations Officer · **Mgr** Operations Manager · **HR** HR/Admin · **Own** Owner · **Adm** Tenant Admin · **Grd** Guard (via mobile)
> Release: **MVP** · **V1** · **V2** · **FUT** (future) · ✗ = not planned

---

## 1. Platform foundations

| Feature | Roles | Release | Req |
|---|---|---|---|
| Tenant, sites (synced from Odoo), teams, reporting lines | Adm, Mgr | MVP | PR-IAM-01, 04 |
| **Single login with Odoo credentials + TOTP** | All | **MVP** | PR-IAM-02, 06 |
| Device registration and revocation | All / Adm | MVP | PR-IAM-05 |
| Brokered "Open in Odoo" without second login | All | MVP | PR-IAM-09, PR-ODO-04 |
| Session revocation on Odoo deactivation or password change | Adm | MVP | PR-IAM-10 |
| Roles, scopes, custom roles | Adm | MVP (catalogue roles), V1 (custom roles) | PR-IAM-03 |
| Provision Platform access from Odoo users | Adm, HR | MVP | PR-IAM-08 |
| Platform-native staff accounts with WebAuthn | Internal | V1 | PR-IAM-12 |
| Shared-device mode | — | ✗ (no shared computers, R-9) | — |
| Audit log (write) | System | MVP | PR-AUD-01 |
| Audit log (query/export UI) | Adm, Own | V1 | PR-AUD-02 |
| Internationalisation framework (English content) | All | MVP | NFR-09 |

## 2. Employee workspace

| Feature | Roles | Release | Req |
|---|---|---|---|
| Home — "What do I need to do now?" | Sup, Ops, HR, Mgr | MVP | PR-WS-01–03 |
| Current or next shift from Odoo roster | Sup, Ops | MVP | PR-WS-01 |
| Announcements with acknowledgement | All | V1 | — |
| Get help / Report a problem from every screen | All | MVP | PR-WS-04 |
| Own training status | All | MVP | PR-WS-06 |
| Own adoption explanation | All | V1 (pending OQ-13) | PR-WS-06 |
| Command palette (⌘K / Ctrl+K) | All | MVP | — |
| Notification centre + OS notifications | All | MVP | PR-NTF-01 |

## 3. Work management

| Feature | Roles | Release | Req |
|---|---|---|---|
| Tasks (assign, due, comments, attachments) | Sup, Ops, Mgr, HR | MVP | PR-WRK-01 |
| Checklist templates + runner (typed items, evidence) | Sup, Ops | MVP | PR-WRK-03 |
| Recurrence: calendar, shift-based, site-based | Mgr, Adm | MVP | PR-WRK-02 |
| Verification (approve/reject with reason) | Sup, Mgr | MVP | PR-WRK-04 |
| Auto-complete from matching Odoo event | System | MVP | PR-WRK-06 |
| "Couldn't complete" with reason | Sup, Ops | MVP | PR-WRK-08 |
| MVP templates: attendance batch posting, supervisor site visit, incident review | Sup, Ops, Mgr | MVP | PR-WRK-09 |
| Full security template library (inspection, handover, open/close, equipment, patrol confirmation, client request) | Sup, Ops | V1 | PR-WRK-09 |
| Multi-step workflows, approvals, dependencies | Mgr, Adm | V1 | PR-WRK-07 |
| Guard shift checklists on mobile | Grd | V2 | — |
| Visual workflow builder | Adm | FUT | — |
| Kanban / Gantt / generic project boards | — | ✗ | — |

## 4. Training & competency

| Feature | Roles | Release | Req |
|---|---|---|---|
| Programs, courses, sections, lessons (text, video, document) | HR, Adm author; all take | MVP | PR-TRN-01 |
| Assessments (MCQ, multi-select, T/F, scenario), question banks | All | MVP | PR-TRN-02 |
| Assignment by role/site/team/person, due dates | HR, Mgr, Sup | MVP | PR-TRN-03 |
| Practical sign-off by supervisor | Sup, Mgr | MVP | PR-TRN-04 |
| Competency levels + evidence | HR, Sup, Mgr | MVP | PR-TRN-05 |
| Content versioning + approval (approver: Winston, R-8) | HR, Adm | MVP | PR-TRN-11 |
| "Using DeployGuard ERP" competency track (DogForce content) | All desktop roles | MVP | — |
| Interactive walkthroughs (guided steps over Odoo screens) | All | V1 | PR-TRN-01 |
| Competency expiry / re-certification automation | HR | V1 | PR-TRN-05 |
| Skill matrix | Mgr, HR | V1 | PR-TRN-06 |
| Rule-based refresher assignment | System | V1 | PR-TRN-07 |
| Offline lessons and attempts | All | V1 | PR-TRN-10, PR-OFF-03 |
| Push approved certifications to Odoo certifications | HR | V1 | C-7 |
| Adaptive remediation (mistake taxonomy, measured improvement) | System | V2 | PR-TRN-08 |
| AI-drafted courses/lessons/questions (human approval) | HR, Adm | V2 | PR-TRN-09 |
| Simulations (sandbox Odoo exercises) | All | V2 | — |
| Guard micro-lessons in mobile | Grd | V2 | — |
| SCORM/xAPI import | — | FUT | — |

## 5. Adoption engine

| Feature | Roles | Release | Req |
|---|---|---|---|
| Event ingestion (desktop, web, bridge) | System | MVP | PR-ADO-01 |
| Expected Work Model for 5 key workflows | Adm, System | MVP | PR-ADO-02 |
| Operational Adoption Score (person/site/team/company) | Mgr, Own, Sup (scoped) | MVP | PR-ADO-03 |
| Score explanation (factors, events, missing work) | Mgr, Sup | MVP | PR-ADO-04 |
| Silent-abandonment detection + assistance check-in | System → person → Sup | MVP | PR-ADO-05 |
| Minimum-data guard and confidence | System | MVP | PR-ADO-06 |
| Expected Work Model for all configured templates and workflows | Adm | V1 | PR-ADO-02 |
| AI interpretation of adoption drops | Mgr | V1 | PR-AI-* |
| Guard adoption from mobile telemetry | Grd | V2 | — |

## 6. Feedback & support

| Feature | Roles | Release | Req |
|---|---|---|---|
| Post-task one-tap feedback | All | MVP | PR-FBK-01 |
| "Something's wrong" taxonomy + auto context | All | MVP | PR-FBK-02, 03 |
| Support requests (queue, SLA, notes, resolution) | HR, Adm | MVP | PR-SUP-01 |
| Knowledge base (seeded from `security_help`) | All | MVP | PR-SUP-02 |
| AI support assistant with citations | All | V1 | PR-SUP-03 |
| AI feedback classification and clustering | Adm, Mgr | V1 | PR-SUP-04 |

## 7. Exceptions, inbox, management views

| Feature | Roles | Release | Req |
|---|---|---|---|
| Deterministic exception rules (MVP catalogue, [10](10-exception-engine.md) §4) | System | MVP | PR-EXC-01 |
| Ingest Odoo alerts as signals | System | MVP | PR-EXC-04 |
| Lifecycle, dedupe, reopen | Sup, Ops, Mgr, HR | MVP | PR-EXC-02, 03 |
| Manager inbox (Critical / Attention / Watch) | Mgr | MVP | PR-INB-01 |
| Supervisor-scoped inbox | Sup, Ops | MVP | PR-INB-02 |
| Escalation ladders | System | MVP | PR-NTF-04 |
| Ops Manager "Today" view | Mgr | MVP | — |
| Owner overview + weekly deterministic digest | Own | MVP | PR-EXE-01 |
| AI inbox prioritisation and explanations | Mgr | V1 | PR-INB-03 |
| AI operational brief with citations | Own, Mgr | V1 | PR-EXE-02 |
| Unusual site behaviour detection | Mgr | V2 | — |

## 8. AI intelligence

| Feature | Roles | Release | Req |
|---|---|---|---|
| `AIProvider` interface + Gemini provider (no user-facing features) | System | MVP (interface only) | PR-AI-01 |
| Context assembler, evidence, confidence, AI audit | System | V1 | PR-AI-02, 03 |
| Human approval gate for proposals | Mgr, HR, Own | V1 | PR-AI-04 |
| Per-tenant and per-capability toggles and budgets | Adm | V1 | PR-AI-05 |
| Additional providers (OpenAI, Anthropic, local) | Adm | FUT | PR-AI-01 |

## 9. Integration, notifications, analytics, offline

| Feature | Roles | Release | Req |
|---|---|---|---|
| `OdooAdapter` (JSON-2, integration user API key) | System | MVP | PR-ODO-01 |
| `security_deployguard_bridge` (auth, SSO tickets, signed webhooks, identity events) | System | MVP | PR-ODO-02, DG-ADR-007 |
| Domain bridge addons: attendance, incidents, roster, leave | System | MVP | DG-ADR-018 |
| Polling reconciliation | System | MVP | PR-ODO-03 |
| Integration health UI | Adm | MVP | PR-ODO-06 |
| Allowlisted write-back to Odoo | System | V1 | PR-ODO-05 |
| In-app, OS, email notifications; preferences; digests; quiet hours | All | MVP | PR-NTF-01–03 |
| WhatsApp / SMS channels | All | V2 | PR-NTF-05 |
| Core analytics (employee/site/supervisor/team/company) | Mgr, Own, HR | MVP | PR-ANL-01 |
| Platform-level cross-tenant ops metrics | Internal | V1 | PR-ANL-02 |
| Offline: cached Home/work/downloaded training, offline checklists | Sup, Ops | MVP | PR-OFF-01, 02 |

## 10. Productization

| Feature | Release |
|---|---|
| Tenant configuration packs (roles, templates, rules, courses) exportable and importable | V1 |
| Self-serve tenant onboarding wizard (connect Odoo, install bridge, map identities) | FUT |
| Entitlements / packaging (link with `security_licensing`, OQ-18) | FUT |
| macOS / Linux desktop distribution | FUT |
| Partner API | FUT |
