# 02 — Product Requirements

> Status: Draft · Owner: Product · Release tags: **MVP**, **V1**, **V2**, **FUT** (see [28-mvp-scope](28-mvp-scope.md))
>
> Requirement IDs are stable. Implementation tickets, tests and acceptance criteria in [BUILD-ORDER](BUILD-ORDER.md) reference them. "Must" = required for the tagged release; "Should" = strong expectation that can slip one release.

---

## 1. Identity & access (IAM)

| ID | Requirement | Release |
|---|---|---|
| PR-IAM-01 | Every record belongs to exactly one tenant. Cross-tenant reads are impossible through the API and enforced again at database level (RLS). | MVP |
| PR-IAM-02 | **Single login (R-7).** Users sign in once, in the DeployGuard app, with their DeployGuard ERP (Odoo) credentials, plus Odoo TOTP where enrolled or required. They are never asked to sign in again to open Odoo from the app. | MVP |
| PR-IAM-03 | Role-based access with tenant-defined role assignments from the default catalogue ([03](03-personas-and-roles.md)); permissions are scoped by tenant, site, team and self. | MVP |
| PR-IAM-04 | Supervisor relationships and reporting lines form a hierarchy used for visibility, verification and escalation routing. | MVP |
| PR-IAM-05 | Each desktop installation registers as a device with a device keypair. Platform sessions are bound to the device; admins can revoke a device or session. | MVP |
| PR-IAM-06 | Password reset and TOTP recovery use DeployGuard ERP's (Odoo) own flows, launched from the app's sign-in screen. The Platform stores no end-user passwords. | MVP |
| PR-IAM-07 | Each Platform user is linked to exactly one Odoo `res.users` (internal) and optionally one `hr.employee` per connected Odoo instance. The link is established from the verified sign-in assertion; ambiguous employee matches need admin confirmation. | MVP |
| PR-IAM-08 | Platform access is provisioned from Odoo: an Odoo internal user becomes a Platform user when the tenant admin enables DeployGuard access and assigns a role (bulk, with review). | MVP |
| PR-IAM-09 | Opening any Odoo screen from the desktop or web app uses a Platform-brokered, single-use, short-lived login ticket issued by the bridge addon. Odoo admin-level accounts (`base.group_system`) are excluded from ticket login and sign in to Odoo directly. | MVP |
| PR-IAM-10 | Deactivating an Odoo user, changing their password, or removing their DeployGuard access revokes all their Platform sessions within 5 minutes. | MVP |
| PR-IAM-11 | Sign-in is rate-limited and protected against credential stuffing: per account, per IP and per device throttles with progressive delay and lockout alerts. | MVP |
| PR-IAM-12 | Internal platform staff (`platform_admin`, `support_agent`) use Platform-native credentials with mandatory phishing-resistant MFA (WebAuthn), separate from tenant identities. | V1 |

## 2. Employee workspace (WS)

| ID | Requirement | Release |
|---|---|---|
| PR-WS-01 | Home answers "What do I need to do now?": current or next shift (from Odoo), due-now and overdue work, assigned training, required acknowledgements, announcements. | MVP |
| PR-WS-02 | Items on Home are ordered by urgency (overdue → due today → upcoming), never by module. | MVP |
| PR-WS-03 | Every item offers one primary action (open checklist, start lesson, open the right Odoo screen). | MVP |
| PR-WS-04 | "Get help" is reachable from every screen in one action and captures context automatically ([34](34-feedback-and-support.md)). | MVP |
| PR-WS-05 | An employee never sees management analytics or other employees' scores. | MVP |
| PR-WS-06 | Employees can see their own adoption and training status with plain-language explanations. | MVP (training), V1 (adoption — pending OQ-13) |

## 3. Work management (WRK)

| ID | Requirement | Release |
|---|---|---|
| PR-WRK-01 | Tasks with assignee (user, role-at-site or team), due date, priority, status, comments and attachments. | MVP |
| PR-WRK-02 | Task and checklist templates with recurrence rules: calendar-based, shift-based (derived from Odoo roster), and site-based. | MVP |
| PR-WRK-03 | Checklists with typed items: yes/no, choice, number, text, photo/file evidence, signature; required vs optional items. | MVP |
| PR-WRK-04 | Verification step: a designated verifier (usually the supervisor) approves or rejects with a reason. | MVP |
| PR-WRK-05 | Overdue detection is deterministic and emits `task.overdue` exactly once per due-state transition. | MVP |
| PR-WRK-06 | Items can link to an Odoo record (e.g. attendance batch, incident) and complete automatically when a matching Odoo event arrives. | MVP |
| PR-WRK-07 | Multi-step workflows with ordered steps, approvals and dependencies. | V1 |
| PR-WRK-08 | "Couldn't complete" outcome with mandatory reason, routed to supervisor instead of silently overdue. | MVP |
| PR-WRK-09 | Security domain template library: site inspection, shift handover, site opening/closing, equipment check, occurrence review, patrol confirmation, client request. | MVP (3 templates), V1 (full library) |

## 4. Training & competency (TRN)

| ID | Requirement | Release |
|---|---|---|
| PR-TRN-01 | Programs → Courses → Sections → Lessons (rich text, video, document, interactive walkthrough). | MVP (walkthrough V1) |
| PR-TRN-02 | Assessments: multiple choice, multi-select, true/false, scenario questions; question banks; pass mark; attempt limits. | MVP |
| PR-TRN-03 | Assignment by role, site, team or individual, with due dates and mandatory/optional flags. | MVP |
| PR-TRN-04 | Practical assignments requiring supervisor verification of a real task as competency evidence. | MVP |
| PR-TRN-05 | Competency framework with levels (0–4), evidence types, expiry and re-certification rules. | MVP (levels + evidence), V1 (expiry automation) |
| PR-TRN-06 | Skill matrix per site/team/company showing gaps against role requirements. | V1 |
| PR-TRN-07 | Rule-based refresher assignment after repeated failures or detected workflow errors. | V1 |
| PR-TRN-08 | Adaptive remediation using mistake taxonomy per question and measured improvement. | V2 |
| PR-TRN-09 | AI-drafted courses, lessons and questions; always draft until a named human approves. | V2 |
| PR-TRN-10 | Offline access to downloaded lessons; attempts sync on reconnect. | V1 |
| PR-TRN-11 | Content versioning: published versions are immutable; attempts reference the version taken. | MVP |

## 5. Adoption engine (ADO)

| ID | Requirement | Release |
|---|---|---|
| PR-ADO-01 | Ingest events from desktop, web, mobile (V2) and Odoo bridge with idempotency. | MVP |
| PR-ADO-02 | Expected Work Model: derive what each person should do per day from role, roster, assignments and templates; exclude leave and absence. | MVP (5 key workflows) |
| PR-ADO-03 | Operational Adoption Score per person, site, team and company, recomputed daily, with factor breakdown. | MVP |
| PR-ADO-04 | Every score change is explainable: factors, deltas and links to contributing events or missing expected events. | MVP |
| PR-ADO-05 | Silent-abandonment detection from deviation against personal baseline; starts with an assistance check-in, never a penalty. | MVP |
| PR-ADO-06 | Minimum-data guard: no score is shown for fewer than N expected items in the window; show "insufficient data". | MVP |
| PR-ADO-07 | Adoption data must not be exported into Odoo HR or discipline records. | MVP |

## 6. Feedback & support (FBK / SUP)

| ID | Requirement | Release |
|---|---|---|
| PR-FBK-01 | One-tap post-task feedback (Easy / Okay / Difficult / Couldn't complete). | MVP |
| PR-FBK-02 | "Something's wrong" flow with taxonomy (don't understand, not working, no permission, can't find, my info is wrong, other). | MVP |
| PR-FBK-03 | Automatic context capture: user, role, screen, task, Odoo record, device, app version, recent client errors, correlation ID. | MVP |
| PR-SUP-01 | Support requests with status, assignee, SLA, internal notes and resolution; linkable to knowledge articles. | MVP |
| PR-SUP-02 | Knowledge base with role and screen targeting; search. | MVP |
| PR-SUP-03 | AI support assistant using controlled context, citing articles; escalates to human support. | V1 |
| PR-SUP-04 | AI classification and clustering of feedback into recurring issues. | V1 |

## 7. Exceptions, inbox & executive views (EXC / INB / EXE)

| ID | Requirement | Release |
|---|---|---|
| PR-EXC-01 | Deterministic rule catalogue producing exceptions with severity, source, owner, evidence, recommended action and escalation policy. | MVP |
| PR-EXC-02 | Exception lifecycle: open → acknowledged → in progress → resolved / dismissed (with reason); reopen on recurrence. | MVP |
| PR-EXC-03 | De-duplication: one open exception per rule + subject; recurrence updates evidence and counters. | MVP |
| PR-EXC-04 | Ingest Odoo-originated alerts (roster gaps, missed check-ins, expiries) as exception signals without re-scanning. | MVP |
| PR-INB-01 | Manager inbox grouped Critical / Attention / Watch; every item actionable in ≤ 2 interactions. | MVP |
| PR-INB-02 | Supervisor view scoped to assigned sites and teams. | MVP |
| PR-INB-03 | AI-assisted prioritisation and explanation of inbox ordering. | V1 |
| PR-EXE-01 | Owner weekly digest (deterministic metrics and changes). | MVP |
| PR-EXE-02 | AI operational brief (what happened / needs attention / changed / risks / recommended actions / positives) with citations to source data. | V1 |

## 8. AI intelligence (AI)

| ID | Requirement | Release |
|---|---|---|
| PR-AI-01 | Provider abstraction; **Gemini default**; provider and model configurable per tenant and per capability. | V1 (MVP interface only) |
| PR-AI-02 | Context assembled by a controlled pipeline with per-capability allowlists; no raw database dumps. | V1 |
| PR-AI-03 | Every AI output stores inputs reference, prompt version, model, cost, evidence citations and confidence. | V1 |
| PR-AI-04 | AI cannot perform consequential actions; proposals require human approval by an authorised role. | V1 |
| PR-AI-05 | AI features can be disabled per tenant and per capability without breaking deterministic features. | V1 |

## 9. Odoo integration (ODO)

| ID | Requirement | Release |
|---|---|---|
| PR-ODO-01 | All Odoo access goes through the `OdooAdapter`, using the Odoo 19 JSON-2 API with a dedicated integration user API key. | MVP |
| PR-ODO-02 | Bridge addon delivers signed, retried, idempotent webhooks for configured events. | MVP |
| PR-ODO-03 | Polling reconciliation with watermarks recovers missed webhooks. | MVP |
| PR-ODO-04 | Deep links open the exact Odoo record or action in a dedicated Odoo window. | MVP |
| PR-ODO-05 | Write-back to Odoo limited to explicitly allowlisted operations, each audited. | V1 |
| PR-ODO-06 | Connection health, lag and error rates visible to tenant admins. | MVP |

## 10. Notifications (NTF)

| ID | Requirement | Release |
|---|---|---|
| PR-NTF-01 | Channels: in-app, desktop OS notification, email. | MVP |
| PR-NTF-02 | Per-user preferences with tenant-mandated minimums (critical cannot be muted). | MVP |
| PR-NTF-03 | Digesting and quiet hours; rate limits per user per hour. | MVP |
| PR-NTF-04 | Escalation ladders driven by exception policies. | MVP |
| PR-NTF-05 | WhatsApp channel via approved provider; SMS fallback. | V2 |

## 11. Analytics, audit, offline (ANL / AUD / OFF)

| ID | Requirement | Release |
|---|---|---|
| PR-ANL-01 | Metrics at employee, site, supervisor, team and company level, with defined formulas ([22](22-analytics.md)). | MVP (core set) |
| PR-ANL-02 | Platform-level cross-tenant operational metrics for platform admins (no tenant content). | V1 |
| PR-AUD-01 | Append-only audit log for auth, permission, configuration, content, competency, exception, AI and Odoo-sync actions. | MVP |
| PR-AUD-02 | Audit is queryable by tenant admins and exportable. | V1 |
| PR-OFF-01 | Desktop shows cached Home, assigned work and downloaded training when offline, clearly labelled with last-sync time. | MVP |
| PR-OFF-02 | Checklist completion and evidence capture work offline and sync idempotently; no fabricated success states. | MVP |
| PR-OFF-03 | Offline lesson completion and quiz attempts. | V1 |

---

## 12. Non-functional requirements (NFR)

| ID | Category | Requirement |
|---|---|---|
| NFR-01 | Performance | Desktop cold start ≤ 3 s on a 4 GB RAM Windows machine; Home interactive ≤ 1.5 s with warm cache. API p95 ≤ 300 ms for read endpoints under pilot load. |
| NFR-02 | Footprint | Windows installer ≤ 20 MB; idle memory ≤ 200 MB. |
| NFR-03 | Availability | API 99.5 % monthly during business hours for MVP; the desktop degrades to offline mode rather than failing. |
| NFR-04 | Data durability | Point-in-time recovery ≤ 15 min RPO; restore tested monthly; offsite encrypted backups. |
| NFR-05 | Security | OWASP ASVS L2 for API and web; TLS 1.2+ everywhere; secrets in a managed secret store; signed desktop builds and updates ([16](16-security-architecture.md)). |
| NFR-06 | Privacy | Data minimisation for events; no keystroke, screen or location capture from desktop; purpose-limited adoption data; retention policies enforced by jobs. |
| NFR-07 | Accessibility | WCAG 2.2 AA: contrast ≥ 4.5:1, full keyboard navigation, focus visibility, `aria-label` on icon-only controls, Esc closes overlays. |
| NFR-08 | Design consistency | All UI uses the `--ds-*` / `--dgs-*` tokens and hard rules of the DeployGuard design system; enforced by lint in CI ([DG-ADR-017](adr/DG-ADR-017-design-system-and-shell-parity.md)). |
| NFR-09 | Internationalisation | All UI strings externalised from P0; dates, numbers and currency locale-aware (NAD, ZMW, ZAR). |
| NFR-10 | Observability | Distributed traces across desktop → API → worker → Odoo adapter with correlation IDs; error reporting on all clients. |
| NFR-11 | Multi-tenancy | No DogForce-specific code paths in core modules; tenant differences expressed as configuration or tenant extension packs. |
| NFR-12 | Maintainability | Module boundaries enforced (lint rule: no cross-module imports except via published module interfaces). |
| NFR-13 | Compatibility | Windows 10 22H2+ / Windows 11 with WebView2; web app on current Chrome, Edge, Firefox, Safari; Odoo 19.0+. |
| NFR-14 | Supportability | Every error shown to a user carries a short reference code that resolves to trace and context for support staff. |
