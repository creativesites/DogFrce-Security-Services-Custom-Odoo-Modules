# 32 — Open Questions, Contradictions & Assumptions

> Status: Living document · Owner: Platform architecture
>
> Anything here that is still open must not be quietly decided in code. Each item is either resolved by an ADR or by a named decision-maker, then moved to **Resolved** with a link.

---

## 1. Resolved decisions (recorded for traceability)

| ID | Decision | Decided by | Recorded in |
|---|---|---|---|
| R-1 | Desktop MVP serves **office staff and supervisors** (ops officers, site supervisors, HR/admin, ops manager, owner). Guards are reached via the Expo mobile app and WhatsApp. | Product owner, 2026-09-15 | [03](03-personas-and-roles.md), [28](28-mvp-scope.md) |
| R-2 | "Bridge modules" are **Odoo-side addons** in `custom_addons/`, following the existing `security_*_bridge` auto-install convention. | Product owner, 2026-09-15 | [DG-ADR-018](adr/DG-ADR-018-odoo-bridge-addons.md) |
| R-3 | All UI follows [`docs/DEPLOYGUARD_DESIGN_SYSTEM.md`](../DEPLOYGUARD_DESIGN_SYSTEM.md); **`security_shell` is the canonical UX reference**. | Product owner, 2026-09-15 | [05](05-ux-principles.md), [DG-ADR-017](adr/DG-ADR-017-design-system-and-shell-parity.md) |
| R-4 | **Gemini is the default AI provider** for both the Platform and the Odoo `security_ai_engine`. | Product owner, 2026-09-15 | [DG-ADR-010](adr/DG-ADR-010-ai-architecture.md) |
| R-5 | **`security_suite` is outdated**; per-client module baselines replace it. | Product owner, 2026-09-15 | [26](26-deployment-strategy.md), [31](31-dogforce-rollout.md) |
| R-6 | Module code is never deleted for a client; only per-database install state changes. | Product owner, 2026-09-15 | [30](30-productization.md) |
| R-7 | **Single login is mandatory from MVP day one.** Users never see two logins. Odoo credentials (+ Odoo TOTP) are the identity source; the Platform trusts a signed assertion from the bridge addon and brokers one-time tickets to open Odoo. *(was OQ-4)* | Product owner, 2026-09-15 — "multiple logins… we are already losing the users" | [DG-ADR-007](adr/DG-ADR-007-authentication.md) |
| R-8 | **Winston (implementation partner lead) authors and approves** DogForce training content and SOP-derived templates, including any AI-drafted content. *(was OQ-5)* | Product owner, 2026-09-15 | [07](07-training-platform.md), [11](11-ai-intelligence.md) |
| R-9 | **There are no shared computers** at DogForce; every desktop user has their own machine. Shared-device / kiosk mode is removed from scope. *(was OQ-9)* | Product owner, 2026-09-15 | [02](02-product-requirements.md), [17](17-desktop-architecture.md) |

---

## 2. Contradictions register

| ID | Contradiction | Resolution | Status |
|---|---|---|---|
| C-1 | ADR-0004 (modular monolith, "no microservices / no event bus") and ADR-0009 (thin clients) vs. a separate DeployGuard Platform backend. ADR-0008 (Odoo session auth, separate auth service rejected) vs. Platform tokens. | [DG-ADR-015](adr/DG-ADR-015-relationship-to-odoo-adrs.md): ADR-0004/0009 stay in force **inside DeployGuard ERP**. The Platform is a separate product layer and is itself a single modular monolith. **ADR-0008 is extended, not superseded** (R-7): Odoo stays the identity source, and the Platform issues its own tokens only after verifying an Odoo-originated assertion. | Proposed |
| C-2 | The name "DeployGuard OS" already refers to the Odoo suite (`security_licensing`, launcher commits, `DOGFORCE_TECHNICAL_DOCUMENTATION.md`). | [DG-ADR-019](adr/DG-ADR-019-product-naming.md): **DeployGuard OS** = the product family; **DeployGuard ERP** = the Odoo `security_*` suite; **DeployGuard Platform** = backend + desktop + web. | Proposed — confirm with product owner |
| C-3 | Gemini-first vs. `security_ai_engine` defaulting to Claude. | R-4. Defect D-1 in [00](00-current-state.md) is fixed in rollout Stage 0. | Resolved |
| C-4 | `security_suite` presented as the all-in-one installer vs. being outdated and lacking `security_shell`. | R-5. Replace references in `scripts/setup_staging.sh` and `DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md` with explicit per-client baselines. | Resolved (doc/script update pending) |
| C-5 | Exceptions: `security_notifications` scanners (roster gaps, missing check-ins, expiries) vs. the Platform exception engine. | The Platform **ingests** Odoo scanner output as signals and never re-scans the same facts. The Platform owns the management-facing exception lifecycle (owner, escalation, resolution). Odoo notifications remain for in-Odoo users. See [10](10-exception-engine.md). | Proposed |
| C-6 | Help and onboarding: `security_help` / `security_tour` vs. the Platform knowledge base and training. | The Platform is authoritative for training and the knowledge base. `security_help` stays as in-Odoo contextual help and is imported once as seed content. A later one-way Platform→Odoo sync is an option (OQ-12). | Proposed |
| C-7 | Certifications: Odoo `security.employee.certification` (legal, roster eligibility) vs. Platform competencies. | Odoo stays authoritative for legal certificates and eligibility. The Platform owns competency evidence and assessments. A human-approved Platform certification may create an Odoo certification record through the bridge. See [07](07-training-platform.md), [14](14-data-model.md). | Proposed |
| C-8 | The Expo mobile theme (`#4F46E5`) and offline "fake 200" pattern conflict with the design system and the Platform offline principles. | Mobile retrofit is out of MVP scope. Platform clients must never fabricate success (see [20](20-offline-strategy.md)). | Deferred to V2 |
| C-9 | Stale docs: Odoo 17 claims, `API.md`, `KNOWN_ISSUES.md`, ADR-0007/0008, Caddy container vs. nginx-only repo config, prod "not provisioned" in `DEPLOYMENT.md`. | Listed in [00](00-current-state.md) §8. Planning docs use verified facts only. Updating legacy docs is a separate housekeeping task. | Open |
| C-10 | The brief says "employees primarily use Windows" vs. 200 of 210 employees being field guards. | R-1. Guard adoption is measured from Odoo-originated events (attendance, patrols/incidents via mobile), not desktop telemetry. See [09](09-adoption-engine.md). | Resolved |
| C-11 | Master plan says push goes through FCM; the code uses the Expo push service. | The Platform notification system abstracts channels; Expo push remains the guard mobile channel. See [21](21-notification-system.md). | Resolved |
| C-12 | Licensing memory/plan uses different brand colours (`#2563EB`, `#0D9488`) from the design system. | R-3: design system wins for all product UI. The marketing site is out of scope. | Resolved |
| C-13 | The brief lists "authentication, account recovery" as Platform-owned vs. R-7 making Odoo the identity source. | The Platform owns **sessions, devices, authorisation, scopes and revocation**. Odoo owns **credentials, password reset and TOTP**. Only internal platform staff have Platform-native credentials. See [DG-ADR-007](adr/DG-ADR-007-authentication.md). | Resolved |

---

## 3. Open questions

| ID | Question | Why it matters | Needed by | Suggested owner |
|---|---|---|---|---|
| OQ-1 | Hosting target and monthly budget for the Platform (managed PaaS in Johannesburg vs. dedicated VPS)? | Drives [DG-ADR-013](adr/DG-ADR-013-deployment.md) and the cost model. | Before build phase P0 | Product owner |
| OQ-2 | Confirm product naming (C-2). | Every UI string, installer name and document. | P0 | Product owner |
| OQ-3 | Should the Platform AI layer and `security_ai_engine` converge (e.g. Odoo calling the Platform AI service) or stay separate? | Duplicate provider config, cost tracking and prompt governance. | V1 | Architecture |
| OQ-6 | Employee privacy requirements: employment-contract clauses, consent, Namibian data-protection obligations (and the Zambia Data Protection Act 2021 for future tenants)? | Adoption telemetry is personal data. Needs legal review before pilot. | Before pilot | Owner + legal adviser |
| OQ-7 | Windows code-signing route (Azure Trusted Signing eligibility vs. OV/EV certificate) for a Namibia-registered entity? | Unsigned installers trigger SmartScreen warnings and harm adoption. | P2 | Platform lead |
| OQ-8 | Exact list of office staff, supervisors and managers to provision as Odoo users and Platform users? | Only 4 Odoo users exist today; with R-7 **every desktop user needs an Odoo internal user**. | Stage 1 | Operations manager |
| OQ-10 | Transactional email provider and sender domain? | Notifications; Odoo password-reset emails must also work (R-7). | P2 | Platform lead |
| OQ-11 | Data residency preference (Namibia / South Africa / EU)? | Hosting region; Gemini processing location. | P0 | Owner |
| OQ-12 | Should approved Platform knowledge articles sync back into `security_help`? | Avoids two diverging help systems for Odoo users. | V1 | Architecture |
| OQ-13 | Can employees see their own adoption score? (Recommendation: yes, with factor explanations.) | Trust, fairness, labour relations. | Stage 5 | Owner + ops manager |
| OQ-14 | Retention periods for raw events, AI prompts and outputs, and audit logs? | Storage, privacy, compliance. | P0 (defaults), pilot (final) | Owner + legal |
| OQ-15 | Gemini commercial terms: paid tier with no training on customer data, and processing region? | Personal data in prompts. | P9 | Platform lead |
| OQ-16 | Which reverse proxy fronts DogForce production (nginx vs. Caddy), and will Platform ↔ Odoo traffic use the public internet (TLS + allowlist) or a private link? | Network design; the bridge login endpoint must be reachable from staff machines. | P1 | Platform lead |
| OQ-17 | Will guards get Platform-backed training and tasks in the Expo app (V2)? Do guards have personal or company smartphones? | V2 scope, device policy. | V1 planning | Operations manager |
| OQ-18 | Does the Platform enforce its own entitlements, or read `security_licensing` tiers? | Productization and packaging ([30](30-productization.md)). | Future | Product owner |
| OQ-19 | Which DogForce SOPs exist in writing (site opening/closing, handover, occurrence book)? | Seed checklist templates and training content. | Stage 3–4 | Operations manager |
| OQ-20 | Should TOTP be mandatory in Odoo for managers, HR and owner accounts from day one, or only after the pilot's first two weeks? | Security vs. first-login friction. | Stage 1 | Owner + ops manager |

---

## 4. Assumptions

| ID | Assumption | Impact if wrong |
|---|---|---|
| A-1 | Office and supervisory users number roughly 15–40 at DogForce. | Capacity assumptions; pilot size. |
| A-2 | Desktop users run Windows 10 22H2+ or Windows 11 with the Evergreen WebView2 runtime (or it can be installed). | Tauri viability on those machines ([DG-ADR-001](adr/DG-ADR-001-desktop-framework.md)). |
| A-3 | Offices have mostly reliable connectivity; sites and vehicles are intermittent. | Offline scope ([20](20-offline-strategy.md)). |
| A-4 | The Odoo production instance is reachable over HTTPS by staff machines and the Platform, and can deliver outbound signed webhooks. | Integration and login mode. |
| A-5 | Future tenants run DeployGuard ERP on Odoo 19+ (JSON-2 API available) **and every Platform user has an Odoo internal user** (R-7). | Adapter scope ([12](12-odoo-integration.md)); tenants without Odoo are not supported. |
| A-6 | Expected tenant scale over 3 years is tens to low hundreds of tenants and fewer than 50 000 users in total. | Multi-tenancy model ([15](15-multi-tenancy.md)). |
| A-7 | A single engineer (with AI assistance) builds the MVP, so operational simplicity outweighs theoretical scalability. | Every ADR's tradeoff weighting. |
| A-8 | English is the working language for MVP content; localisation (e.g. Oshiwambo, Afrikaans, Bemba) is later. | i18n is built in from P0, but content ships in English. |
| A-9 | Each desktop is used by one person (R-9). | Session model assumes one user per device profile; Windows account separation handles rare exceptions. |
