# DG-ADR-019 — Product Naming & Boundaries

- **Status:** Proposed (awaiting confirmation, OQ-2)
- **Date:** 2026-09-15
- **Related:** [01-product-vision](../01-product-vision.md) §5, [30-productization](../30-productization.md), [32-open-questions](../32-open-questions.md) C-2

## Context

"DeployGuard OS" is already used inconsistently:

- the licensing module and docs describe `security_licensing` as licensing "for DeployGuard OS";
- commit history built a "DeployGuard OS Main Launcher" inside Odoo;
- the technical documentation calls the Odoo system "DeployGuard Enterprise Security OS";
- the brief uses "DeployGuard OS" for the new layer *above* Odoo;
- the mobile app is branded "DeployGuard"; code and data still say "DogForce" in places.

Ambiguous names cause confusion in sales conversations, documentation, installer names, support tickets and architecture discussions ("is this an OS change or an ERP change?").

## Decision

| Name | Definition | Examples of correct use |
|---|---|---|
| **DeployGuard OS** | The complete product family a security company adopts. Umbrella brand only; not a codebase. | "DogForce runs DeployGuard OS." |
| **DeployGuard ERP** | The Odoo 19 `security_*` addon suite and its Odoo shell (`security_shell`). System of record for operations, people, payroll, billing. | "Rostering lives in DeployGuard ERP." |
| **DeployGuard Platform** | Backend, desktop app and web app for training, work, adoption, exceptions and intelligence. | "The adoption engine is a Platform module." |
| **DeployGuard Desktop** | The Windows (later macOS/Linux) installed client of the Platform. Installer and app name. | "Install DeployGuard Desktop." |
| **DeployGuard Mobile** | The Expo app for guards and field roles. | — |
| **Bridge addons** | `security_deployguard_*` Odoo addons connecting ERP and Platform. | — |
| **Tenant** | A customer organisation in the Platform (e.g. DogForce Security Services). | — |

Rules:

- User-facing UI says "DeployGuard" (plus the tenant's name); internal technical docs use the precise names above.
- "DogForce" appears only in DogForce's tenant data and configuration, never in Platform code, package names or generic UI strings (NFR-11).
- Commercial packaging names (Training, Operations, Intelligence, Managed Operations) are **editions or add-ons** of DeployGuard OS ([30](../30-productization.md) §6), not separate products.

## Alternatives

- **"DeployGuard OS" = only the new Platform:** conflicts with existing usage for the ERP and licensing; forces renaming history.
- **A completely new name for the Platform (e.g. "DeployGuard Pulse"):** adds a brand to explain; the umbrella + descriptive-suffix approach scales better.
- **Keep names informal:** status quo confusion.

## Tradeoffs

Existing documents that call the Odoo suite "DeployGuard OS" become slightly imprecise; they remain correct under the umbrella meaning.

## Consequences

- The installer, window title and web title use "DeployGuard". Package names use `deployguard-platform`, `@deployguard/*`.
- Legacy docs are updated opportunistically (C-9); no mass rename of Odoo technical names (`security_*`) is required.
