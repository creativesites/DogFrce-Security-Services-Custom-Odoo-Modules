# 35 — Competitive & Category Analysis

> Status: Draft · Owner: Product
>
> Category-level analysis of what adjacent products do well and where they leave the problem unsolved. Capability statements are general and directional; verify specifics before using any of this in sales material.

---

## 1. The categories we overlap

| Category | Examples | What they do well | What they don't solve for a security company |
|---|---|---|---|
| **ERP / security workforce ERP** | Odoo (our own DeployGuard ERP), industry suites for guarding | System of record: rosters, attendance, payroll, billing, client contracts | Whether people *use* it. No training, no adoption measurement, no assistance loop. The DogForce reality: 210 employees, 4 users |
| **Work/project management** | Asana, ClickUp, Monday, Trello | Flexible tasks, boards, automations, dashboards | Generic: no shift/site/roster-driven expectations, no ERP fact coupling, no competency link, no "expected work" concept. Adoption is assumed |
| **LMS / training platforms** | Moodle, TalentLMS, corporate LMS, compliance training tools | Content delivery, quizzes, certificates, completion reporting | Completion ≠ capability. Rarely tied to real work performed in another system; no verification of practice; no feedback into operations |
| **Workforce management / field service** | Deputy, Connecteam, Skedulo, field-service suites | Scheduling, mobile time capture, forms, dispatch | Built for scheduling and timekeeping, not for making an existing ERP investment actually operate; limited competency modelling; not an intelligence layer above another system |
| **Security-specific guard tools** | Guard-tour and patrol systems, incident reporting apps | Patrol proof, incident capture, client reports | Point solutions for guards, not for the supervisory and office layer where system adoption breaks down |
| **Digital adoption platforms (DAP)** | WalkMe, Pendo, Whatfix, Userpilot | In-app guidance, usage analytics, onboarding flows | Measure *software* usage inside a product, not *operational work completion* across systems; no domain workflows, no competency, no exception management, and typically no offline field client |
| **Operational intelligence / BI** | Power BI, Metabase, Looker | Flexible analysis of whatever you load | Dashboards, not action: no ownership, no escalation, no assistance, no training loop. Requires an analyst to interpret |
| **ITSM / helpdesk** | Jira Service Management, Freshservice, Zendesk | Ticketing, SLAs, knowledge bases | Reactive by design; someone must already know to ask for help. No detection of silent abandonment |

## 2. The gap DeployGuard OS fills

No category combines these five properties:

1. **Expected work derived from the ERP's own reality** (roster, sites, contracts) rather than tasks someone remembered to create.
2. **Detection of what is *not* happening**, including silent abandonment, with assistance before escalation.
3. **Training tied to verified real work** producing competency evidence, not completion certificates.
4. **Exception-first management** with ownership, evidence and escalation — not another dashboard.
5. **Domain shape for security operations** (shifts, posts, handovers, occurrence reports, patrol confirmation, AWOL) rather than generic tasks.

Positioning sentence:

> DAPs measure whether people use software. LMSs measure whether people watched training. Work tools measure tasks someone created. **DeployGuard OS measures whether the operational work a security company is contractually obliged to perform actually happened in its systems — and drives the help, training and escalation that close the gap.**

## 3. Where we deliberately do not compete

- Against ERPs on rostering, payroll or billing depth — that is DeployGuard ERP's job.
- Against project-management tools on flexibility — our constraints are the product.
- Against LMS platforms on content marketplaces, SCORM ecosystems or academic features.
- Against BI tools on ad-hoc analysis.

## 4. Competitive risks

| Risk | Assessment | Response |
|---|---|---|
| An ERP vendor adds adoption analytics | Plausible for large vendors, but tied to their own product and usually per-database | Cross-tenant intelligence, desktop client, training + competency depth, and ERP-neutral seam ([30](30-productization.md) §5) |
| A DAP moves toward operational work | Possible upmarket; their model is in-app guidance, not multi-system operational expectations | Domain depth for security; offline field client; competency verification |
| A workforce-management suite adds training | Common; usually shallow completion tracking | Verified competency, adaptive remediation, evidence trail |
| Customers build it themselves in Odoo | Realistic for one company — that is exactly what DogForce's situation shows is hard to sustain | Productized configuration packs, multi-tenant operation, maintained content, intelligence layer |
| "Good enough" WhatsApp + spreadsheets | The real incumbent everywhere | Reduce friction below the WhatsApp alternative; work where people are; measure honestly |

## 5. The honest incumbent

For most African security companies the competitor is not software: it is **WhatsApp, paper occurrence books and a supervisor's memory**. Implications for the product:

- Every workflow must be faster than sending a WhatsApp message, or it loses.
- Offline and low-bandwidth behaviour is a competitive feature, not a nicety.
- The first value must be visible in days: "I can see what I must do today", "I can see who needs help".
- WhatsApp is a channel to embrace (V2 notifications and guard flows), not a rival to defeat.
