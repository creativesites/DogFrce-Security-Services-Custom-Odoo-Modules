# 30 — Productization

> Status: Draft · Owner: Product
>
> DogForce is customer #1, not the product's shape. This document defines the layers that keep it that way, and what "onboard a new security company" must eventually mean.

---

## 1. The four layers

| Layer | Contains | Changes for a customer? | Where it lives |
|---|---|---|---|
| **1. Platform primitives** | Tenancy, identity, roles/scopes, events, audit, work primitives, training engine, competency engine, adoption engine, exception engine, notifications, knowledge, AI framework, integration framework | Never per customer | `apps/api/src/modules`, `packages/*` |
| **2. Security-industry domain** | Template library (site visit, handover, attendance posting, patrol confirmation…), standard competency framework, default exception rules, default expected-work definitions, standard course pack, ERP mappings for DeployGuard ERP | Evolves as product content, shared by all customers | `template_library` (platform-global, versioned) |
| **3. Tenant configuration** | Which templates/rules/courses are enabled and their parameters, roles and scopes, reporting lines, branding font, SLAs, notification policies, AI toggles, integration settings | Every customer | Tenant tables ([15](15-multi-tenancy.md) §4) |
| **4. Customer-specific content** | Their own checklists, their SOP-derived courses, their knowledge articles, their sites and people | Every customer | Tenant data |

**Rule:** a request from DogForce lands in layer 3 or 4. If it seems to need layer 1 or 2, it is generalised first (what would three other security companies need?) or refused.

## 2. Configuration packs

A **pack** is an exportable bundle of layer-2/3 content:

```
pack.yaml
├── metadata (name, version, locale, industry variant)
├── roles + scopes
├── expected_work_definitions
├── work_templates (+ schedules)
├── exception_rules (+ escalation policies)
├── courses (versions, lessons, assessments, competency links)
├── knowledge_articles
└── notification_policies
```

- Ships as **"Security Operations Starter (Southern Africa)"** for new tenants.
- A tenant can export its configuration (without personal data) to share or to seed a sibling company.
- Packs are versioned; importing shows a diff and never overwrites customer edits silently.
- DogForce's configuration becomes the first validated pack — the honest test of whether layers 1–2 were built generically.

## 3. Onboarding a new tenant (target state)

| Step | MVP (manual) | FUT (self-serve) |
|---|---|---|
| Create tenant | Platform admin | Signup + verification |
| Install bridge addons in their Odoo | Partner installs per-client baseline | Guided installer + module from an addon store |
| Connect & verify | Manual key exchange | Wizard with connection test |
| Import sites/employees | Automatic initial sync | Same |
| Choose pack | Platform admin applies starter pack | Wizard with industry variant |
| Configure roles, scopes, reporting lines | Admin UI with Odoo-derived suggestions | Same, with bulk confirm |
| Enable users | Per-user DeployGuard access flag | Bulk with review |
| Deploy desktop | Download link; per-user install | MDM package option |
| Activate intelligence | Enable AI capabilities, set budget | Same |

**Target:** a technically competent admin can go from nothing to a working tenant in under a day, without the Platform vendor writing code. That is the productization success test.

## 4. What must never be hard-coded

| Anti-pattern | Correct approach |
|---|---|
| `if (tenant === 'dogforce')` | Tenant configuration value or feature flag |
| Namibian public holidays in code | Working calendar from ERP localisation per tenant |
| "Site supervisor" role assumptions in queries | Role keys + scopes resolved from configuration |
| DogForce site names, shift patterns, cut-off times | Tenant data and expected-work definitions |
| NAD currency or English-only strings | Locale/currency config; externalised ICU strings |
| Odoo model names sprinkled in feature code | `OdooAdapter` + facade ([12](12-odoo-integration.md)) |

CI guard: a lint rule bans the literal strings `dogforce`, `DogForce` (outside fixtures, docs and seed packs) in `apps/` and `packages/`.

## 5. Supporting other ERPs (later)

The integration framework already separates the adapter (`packages/odoo`) from the rest of the Platform, and expresses ERP facts as **projections plus events**. Supporting a second ERP means a new adapter and a new bridge, with the same event contract — no change to work, training, adoption or exceptions. This is deliberately *not* built until a real customer requires it, but the seam exists.

## 6. Commercial packaging (direction, not pricing)

| Edition / add-on | Value it must justify |
|---|---|
| **DeployGuard Platform (base)** | Single login, work and checklists with evidence, knowledge, feedback and support, notifications, audit |
| **Training** | Course engine, competencies, practical verification, compliance reporting, skill matrix |
| **Operations** | Expected work, exception engine, escalations, manager inbox, site/supervisor analytics |
| **Intelligence** | AI briefs, prioritisation, feedback classification, support assistant, recurring-problem detection |
| **Managed Operations** (service) | The partner runs adoption for the customer: content authoring, rule tuning, weekly reviews, support desk |

Recurring-revenue logic: base + Training justify a per-user fee; Operations and Intelligence justify a company-level fee tied to sites/employees; Managed Operations is a service retainer. Pricing, licensing enforcement and how this relates to `security_licensing` tiers stay open (OQ-18) — [DG-ADR-019](adr/DG-ADR-019-product-naming.md) fixes only the naming.

## 7. Productization checklist (run per release)

- [ ] No customer name in code or default content.
- [ ] Every new behaviour has a configuration point or a documented default.
- [ ] New content added to the starter pack where generally useful.
- [ ] Onboarding runbook updated if a new setup step appeared.
- [ ] Export/import still round-trips the tenant configuration.
- [ ] Docs and in-product help describe the *capability*, not DogForce's use of it.
