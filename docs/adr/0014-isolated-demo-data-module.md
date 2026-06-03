# ADR-0014: Isolated Demo Data in security_demo_data

**Date:** 2026-05-29  
**Status:** Accepted

## Context

Developers, sales demos, and CI need realistic data: Namibian clients, sites, guards, rosters, attendance, payroll, and billing samples. Options:

- **`demo=True` in each module's XML** — loads on every install; pollutes production
- **Shared fixtures only in tests** — good for CI, not for manual UAT/demos
- **Dedicated demo module with post-install hook** — optional install, programmatic seeding

Production must never receive demo guards, fake bank accounts, or sample payslips.

## Decision

Create optional module **`security_demo_data`**:

- Depends on full suite chain (base through fleet, billing, client reports)
- No XML data files — **`post_init_hook`** runs `DemoBuilder` in `hooks.py`
- Creates rule sets, guards, sites, rosters, attendance, payroll, equipment, fleet programmatically
- External IDs namespaced under `security_demo_data.*` via `ir.model.data`

Install via `./scripts/seed-db.sh` for local dev only. **Excluded** from production deploy checklist in DEPLOYMENT.md.

## Consequences

### Positive

- Production installs stay clean — demo is explicit opt-in
- DemoBuilder can create coherent cross-module scenarios (attendance → payslip)
- Easy to extend for sales scenarios without touching core module XML

### Negative

- Hook runs on every install of demo module — can be slow (3–10 minutes)
- Demo data can drift from model changes if hook is not maintained
- Mistaken production install would create fake financial records

### Neutral

- `security_demo_data` not required for module tests — tests create own fixtures
- Namibia-specific demo content reinforces ADR-0005 but is isolated from `security_l10n_na` data XML
