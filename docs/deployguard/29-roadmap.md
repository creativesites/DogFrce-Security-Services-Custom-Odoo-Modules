# 29 — Roadmap

> Status: Draft · Owner: Product
>
> Sequencing, not date promises. Durations assume one engineer with AI assistance (A-7) and are **estimates to be re-baselined after P0**. Build phases are specified in [BUILD-ORDER](BUILD-ORDER.md).

---

## 1. Shape

```
Stage 0 ─ prerequisites (ERP hardening, Odoo users, staging, HTTPS)
   │
MVP ──── P0 foundations → P1 bridge+sync → P2 desktop shell+auth → P3 training
   │      → P4 work → P5 adoption → P6 exceptions+inbox → P7 feedback/support
   │      → P8 owner digest+analytics → P10 pilot hardening
   │                                   (P9 AI is deliberately after the pilot)
V1 ───── AI layer · full template library · workflows · skill matrix · write-back · offline learning
   │
V2 ───── guard mobile features · WhatsApp · adaptive training · AI content · mobile SSO
   │
FUT ──── self-serve onboarding · entitlements · multi-platform · partner API
```

## 2. Milestones

| Milestone | Contents | Rough effort | Depends on |
|---|---|---|---|
| **M0 — Ready to build** | OQ-1/2/11 closed, budget agreed, Stage 0 ERP prerequisites underway | 1–2 weeks (mostly decisions) | Product owner |
| **M1 — Skeleton alive** | P0 + P1: tenant, RLS, events, audit, bridge addon, projections, integration health | 4–6 weeks | M0 |
| **M2 — People can sign in and see something** | P2: desktop shell with `security_shell` parity, single login, Home, notifications, updater | 3–4 weeks | M1 |
| **M3 — Training runs** | P3 + the DogForce course pack authored and approved | 3–4 weeks | M2, content from ops manager (OQ-19) |
| **M4 — Work runs** | P4: templates, recurrence, checklist runner, verification, auto-complete, offline | 4–5 weeks | M2 |
| **M5 — We can see adoption** | P5: expected work, scoring, explanations, abandonment + check-ins | 3–4 weeks | M4 |
| **M6 — Management value** | P6 + P7 + P8: exceptions, inbox, escalations, feedback/support, owner digest | 4–5 weeks | M5 |
| **M7 — Pilot ready** | P10: security review, performance, code signing, runbooks, restore drill, training of pilot users | 2–3 weeks | M6, OQ-6, OQ-7 |
| **M8 — Pilot (4 weeks)** | Rollout Stages 1–6 ([31](31-dogforce-rollout.md)) | 4 weeks | M7 |
| **M9 — V1 intelligence** | P9 AI capabilities with citations, plus V1 backlog | 6–8 weeks | M8 + OQ-6/15 |
| **M10 — Second tenant ready** | Configuration packs, onboarding runbook, pen test, export/delete tooling | 4 weeks | M9 |

## 3. Why AI comes after the pilot

1. Deterministic exceptions and adoption must be trustworthy first — AI explaining wrong numbers destroys confidence faster than no AI.
2. Evals need real, consented data.
3. Privacy and provider terms (OQ-6, OQ-15) must be settled before employee data reaches a model.
4. The pilot tells us which explanations managers actually want.

The `AIProvider` interface still ships in MVP so nothing has to be retrofitted.

## 4. Decision checkpoints

| When | Decision |
|---|---|
| Before P0 | Hosting, budget, residency (OQ-1, OQ-11); naming (OQ-2) |
| During P1 | Network path for webhooks (OQ-16); TOTP policy (OQ-20) |
| Before P2 | Code-signing route (OQ-7); email provider (OQ-10) |
| Before P5 | Adoption visibility policy (OQ-13); privacy/legal sign-off (OQ-6) |
| Before P9 | AI provider terms and region (OQ-15); AI/ERP convergence (OQ-3) |
| After pilot | Guard mobile scope (OQ-17); entitlements approach (OQ-18) |

## 5. Risks to the schedule

| Risk | Mitigation |
|---|---|
| ERP prerequisites (users, HTTPS, staging) slip | Stage 0 starts immediately, in parallel with P0 |
| Content authoring capacity (courses, SOPs) | Start with 3 courses; AI drafting only in V2; ops manager time booked weekly |
| Odoo API surprises (JSON-2, TOTP behaviour) | Contract tests against a real Odoo 19 container from P1 |
| Windows code-signing lead time | Begin the application at M2 |
| Pilot user resistance | Rollout communications and the "help before blame" framing ([31](31-dogforce-rollout.md) §6) |
