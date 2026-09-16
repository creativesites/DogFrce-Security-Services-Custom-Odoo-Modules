# 28 — MVP Scope

> Status: Draft · Owner: Product · Detail per capability: [06](06-feature-map.md) · Sequence: [BUILD-ORDER](BUILD-ORDER.md)
>
> **MVP goal:** get DogForce's office staff and supervisors trained, working through the system, and give management visibility into adoption and exceptions — without expanding into ERP territory.

---

## 1. The MVP promise

> A supervisor opens DeployGuard, signs in **once**, sees exactly what they must do today, does it (in the Platform or one click into Odoo), gets help the moment something breaks — and their manager sees, in one list, what still needs a human.

If a proposed feature does not serve that sentence, it is not MVP.

## 2. In scope

| Area | What ships |
|---|---|
| **Identity** | Single login with Odoo credentials + TOTP (R-7), device registration, roles and scopes, reporting lines, provisioning from Odoo users, revocation on Odoo deactivation |
| **Integration** | `security_deployguard_bridge` + attendance/roster/incidents/leave/notifications bridges; signed webhooks; polling reconciliation; projections; integration health; brokered "Open in Odoo" |
| **Desktop (Windows)** | Shell with `security_shell` parity, Home, My Work, checklist runner, Learn, Team (scoped), Inbox, Help; offline for the field set; OS notifications; auto-update |
| **Web** | Same app for owner, managers and admins; admin configuration screens |
| **Work** | Tasks, checklist templates + runner with evidence, recurrence (calendar/shift/site-event), verification, auto-complete from ERP events, "couldn't complete"; 3 domain templates (`attendance.post`, `site.visit`, `incident.review`) |
| **Training** | Courses/versions/lessons/assessments, role assignment, practical sign-off, competency levels with evidence, content approval workflow, the 8-course "Using DeployGuard ERP" pack |
| **Adoption** | Expected Work Model for 5 workflows, daily scoring with factor explanations, confidence gating, retroactive fault excusal, silent-abandonment detection with the assistance check-in |
| **Exceptions** | The MVP rule catalogue ([10](10-exception-engine.md) §4), lifecycle, dedupe, evidence, escalation ladders, manager inbox, scoped supervisor inbox |
| **Feedback & support** | Post-task feedback, "Something's wrong" with auto-context, support queue with SLAs, knowledge base seeded from `security_help` |
| **Notifications** | In-app, desktop OS, email; preferences, quiet hours, digests, escalations |
| **Owner** | Overview tiles + weekly deterministic digest |
| **Foundations** | Multi-tenancy with RLS, audit log, event store with replay, observability, backups, CI/CD, `AIProvider` interface (no user-facing AI yet) |

## 3. Explicitly not in MVP

| Not building | Why | When |
|---|---|---|
| User-facing AI (briefs, classification, assistant, prioritisation) | Deterministic value must land first; AI needs real data and privacy sign-off (OQ-6, OQ-15) | V1 |
| Guard-facing Platform features | Guards are not desktop users (R-1); their signals come from ERP | V2 |
| Interactive walkthroughs, simulations, adaptive remediation | Higher build cost than the first adoption win | V1/V2 |
| Multi-step workflows with approvals and dependencies | Templates + recurrence cover MVP cases | V1 |
| Skill matrix, competency expiry automation | Needs a competency baseline first | V1 |
| WhatsApp/SMS notifications | Requires official Business API onboarding | V2 |
| Offline lessons and quiz attempts | Offline work items matter more | V1 |
| Write-back to Odoo (certifications, chatter notes) | Read-first reduces risk during the pilot | V1 |
| Self-serve tenant onboarding, entitlements/billing, custom roles | One tenant in MVP | V1/FUT |
| macOS/Linux distribution, mobile retrofit to the design system | No user need yet | FUT |
| Any ERP capability (rosters, payroll, billing, equipment) | Odoo is the system of record | Never |

### 3.1 Sales guardrail — say this out loud in every MVP conversation

**MVP contains no AI-generated text, insight, or recommendation anywhere
in the product.** Every number, status and exception the user sees is
produced by a deterministic rule (§2's Foundations row: rules decide
facts, per [11-ai-intelligence.md](11-ai-intelligence.md) §1). That is
correct, deliberate engineering — deterministic value has to be real and
trusted before AI reasons over it (see
[29-roadmap.md](29-roadmap.md) §3, "Why AI comes after the pilot"). It is
**not** the same product as "an AI intelligence engine," and the two must
never be conflated in a sales conversation, a demo, or a proposal.

If asked "is this AI?" during the MVP, the honest answer is: **"Not yet —
that's V1, and it's already designed"** (point to
[11-ai-intelligence.md](11-ai-intelligence.md) and
[DG-ADR-010](adr/DG-ADR-010-ai-architecture.md)). Do not let anyone —
including an eager owner — walk away from an MVP demo believing they
bought AI-generated insight when what they saw was a (very real, very
useful) rules engine.

## 4. Release definitions

| Release | Theme | Exit criteria |
|---|---|---|
| **MVP** | Trained, working, visible | Pilot group uses it daily for 4 weeks; baseline vs post-rollout coverage measured; exceptions actioned; no P1 defects open |
| **V1** | Intelligent and complete | AI briefs/classification/assistant live with citations; full template library; workflows; skill matrix; write-back; offline learning |
| **V2** | Field and reach | Guard features in mobile, WhatsApp channel, adaptive training, AI content generation, Odoo SSO for mobile |
| **FUT** | Product at scale | Self-serve onboarding, entitlements, multi-platform desktop, partner API, dedicated cells |

## 5. Scope guards

1. **The ERP boundary**: any request to store rosters, payroll, invoices or equipment in the Platform is refused and redirected to DeployGuard ERP.
2. **The template test**: new "features" that are really a new checklist or expectation are delivered as configuration, not code ([08](08-work-management.md) §1).
3. **The AI test**: if a rule can decide it, a rule decides it ([11](11-ai-intelligence.md) §1).
4. **The one-question test**: employee screens answer one question; anything else belongs in a management view.
5. **The tenancy test**: no DogForce-specific code path; if it cannot be configuration, it is not built (NFR-11).
