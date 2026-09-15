# 31 — DogForce Rollout Plan

> Status: Draft · Owner: Implementation partner (Winston) with the DogForce operations manager
>
> Context: 210 employees, 4 internal Odoo users, a mature Odoo 19 ERP that people largely do not use ([00](00-current-state.md)). The rollout's job is to change *behaviour*, not to install software.

---

## 1. Success criteria (agree before Stage 1)

| Measure | Baseline | 90-day target |
|---|---|---|
| `workflow_coverage` (pilot group, 5 MVP workflows) | Measured from ERP data for 4 weeks **before** rollout | ≥ 80 % |
| Attendance batches posted before cut-off | From ERP history | ≥ 85 % on time |
| Incident review within SLA | From ERP history | ≥ 90 % |
| Pilot users verified competent on courses 1–6 | 0 | 100 % |
| Median time from abandonment signal to resolution | n/a | < 2 working days |
| Manual follow-ups by the partner ("chasing") | Count for 4 weeks pre-rollout | Downward every month |
| Pilot users who would be "annoyed if it was taken away" | n/a | ≥ 70 % |

The baseline is collected by the bridge + projections **before** any desktop rollout — Stage 1 delivers this even if nothing else ships.

## 2. Stage 0 — Prerequisites (start now, parallel with P0)

| # | Action | Owner | Blocking |
|---|---|---|---|
| 1 | Rotate every credential exposed in repo docs and `odoo.conf`; purge secrets from the image and docs (S-1) | Partner | Pilot |
| 2 | Replace the tokenised git remote (S-2) | Partner | No |
| 3 | HTTPS verified for the Odoo production domain; confirm nginx vs Caddy (OQ-16) | Partner | Pilot |
| 4 | Authenticate the WhatsApp webhook; stop publishing the sidecar port (S-3) | Partner | Pilot |
| 5 | Create Odoo internal users for all pilot staff with correct groups (OQ-8) | Ops manager + partner | Stage 1 |
| 6 | Decide TOTP policy (OQ-20) and enrol managers/HR/owner | Owner + partner | Stage 2 |
| 7 | Switch `security_ai_engine` default to Gemini (D-1) | Partner | V1 |
| 8 | Replace `security_suite` references with the per-client module baseline incl. `security_shell` (R-5, C-4) | Partner | Stage 1 |
| 9 | Fix `action_scan_certification_expiry` model name (D-3) | Partner | No |
| 10 | Restart and validate the ERP **staging** stack for Platform staging | Partner | Stage 1 |
| 11 | Privacy/legal review of adoption monitoring; employment-contract notice (OQ-6) | Owner + adviser | Stage 5 |
| 12 | Confirm pilot participants and their machines (A-1, A-2) | Ops manager | Stage 2 |

## 3. Stages

| Stage | Objective | Key activities | Exit criteria |
|---|---|---|---|
| **1. Infrastructure + identity** | Platform connected, baseline measurable | Bridge addons installed; connection verified; initial sync; identity links; **baseline metrics collection starts** | Projections current; baseline dashboard shows 4 weeks of ERP-derived coverage |
| **2. Desktop client** | Pilot users signed in, one login | Install on pilot machines; first-run guided setup; single login verified end-to-end incl. "Open in Odoo"; notifications working | Every pilot user signs in unaided; zero second-login prompts |
| **3. Training** | Everyone knows how to do the core work | Author courses 1–6 with the ops manager (approved by Winston); assign; two 45-minute live sessions; practical sign-offs scheduled | 100 % of pilot users complete courses 1–3; supervisors verified on `attendance.posting` |
| **4. Tasks & checklists** | Work runs through the system | Enable `attendance.post`, `site.visit`, `incident.review`; tune cut-offs and SLAs with the ops manager; supervisors run a week supported | ≥ 90 % of generated work is actioned (completed or explicitly "couldn't complete") |
| **5. Adoption tracking** | Honest visibility, framed as support | Enable expected work + scoring (monitoring notice acknowledged first); review first snapshots with the ops manager privately before showing anyone else; enable check-ins | Scores explainable on every pilot user; no unresolved fairness complaints |
| **6. Manager visibility** | The inbox becomes the manager's start page | Enable exception rules gradually (coverage → work → training → adoption); tune thresholds for two weeks; owner weekly digest on | Critical inbox ≤ 5 items/day; ops manager starts the day in the inbox |
| **7. AI intelligence (V1)** | Explanations and briefs | Enable capabilities one at a time with citations visible; compare AI brief to the deterministic digest for 2 weeks | Manager rates ≥ 70 % of explanations useful; no fabrication incidents |
| **8. Optimisation** | Fewer exceptions, better processes | Monthly review of recurring problems; adjust templates, expectations and training; retire noisy rules | Downward trend in repeat exceptions and support load |

## 4. Pilot group

| Role | Count | Why |
|---|---|---|
| Operations manager | 1 | Owns adoption; primary inbox user |
| Site supervisors | 3 | Different sites and shift patterns, mixed digital confidence |
| Operations officer | 1 | Incident and report flow |
| HR/Admin | 1 | Provisioning, training compliance, people data corrections |
| Owner | 1 | Weekly digest only |

Start with willing, credible supervisors — early success stories travel. Add the remaining supervisors in week 5 after fixing what the pilot exposes.

## 5. Training and support during rollout

- Two live 45-minute sessions per role group, recorded and turned into the course content itself.
- A one-page job aid per workflow, printable for the office wall.
- Daily 15-minute "office hours" for the first two weeks; response within one hour for blocking issues.
- Every support request in the pilot is treated as a product signal: fix the cause, then update the article and course.

## 6. Communication (decisive for adoption)

| Message | Delivered by | When |
|---|---|---|
| "This exists to make your job easier and to stop things falling through the cracks." | Owner + ops manager | Before Stage 2 |
| "The system will notice when something isn't done — and ask what's blocking you. It is not a disciplinary tool." | Ops manager, in writing | Before Stage 5 |
| What is measured, what is not (no keystrokes, no screens, no location) and who can see it | Partner + written notice acknowledged in-app | Before Stage 5 |
| "If it's broken, report it in the app — that's how it gets fixed, and it protects your record." | Partner | Stage 4 |
| Weekly progress: coverage improving, problems fixed because people reported them | Ops manager | Weekly from Stage 4 |

Naming matters: adoption screens say "support" and "coverage", never "compliance score".

## 7. Risks

| Risk | Mitigation |
|---|---|
| Staff read adoption tracking as surveillance | Notice + non-disciplinary policy + fault excusal + own-score visibility; owner states the framing |
| Supervisors lack Odoo accounts or machines | Stage 0 items 5 and 12; no rollout to a user without both |
| Odoo screens are the real blocker (not training) | Friction signals and support categories separate "doesn't know" from "can't"; ERP UX fixes are a valid outcome |
| Partner becomes the chaser again | Escalations route to supervisors/manager, never to the partner; measure partner follow-ups as a KPI |
| Content authoring stalls | Only 3 courses block Stage 4; reuse session recordings |
| Pilot fatigue from noisy exceptions | Enable rules gradually with tuning weeks; track dismissal rates |

## 8. Post-pilot

1. Review success criteria against baseline with the owner and ops manager.
2. Decide the expansion: remaining supervisors, then guards via mobile (V2, OQ-17).
3. Turn DogForce's configuration into the first starter pack ([30](30-productization.md) §2).
4. Write the customer case study: baseline, interventions, measured change.
