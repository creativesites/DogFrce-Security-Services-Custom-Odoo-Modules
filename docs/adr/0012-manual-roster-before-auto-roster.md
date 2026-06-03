# ADR-0012: Manual Roster MVP Before Auto-Rostering

**Date:** 2026-05-26  
**Status:** Accepted

## Context

The functional specification calls for automated rostering with grade/certification matching, fairness weighting, and understaffing alerts. Auto-roster is algorithmically complex: eligibility constraints, 12-hour rest rules, consecutive-day limits, leave conflicts, guard exclusions, and supervisor overrides.

Shipping auto-roster early risks **incorrect guard assignments** — a safety and contractual liability for a security company.

PROJECT_PLAN.md principle #4: "A correct manual roster with validations is more valuable than a fragile auto-roster."

## Decision

Phase 1 operations (`security_operations`) implement:

- Full **manual roster** creation via `security.roster.batch` and `security.roster.slot`
- **Validation constraints** on assignment (grade, certifications, disqualification, leave)
- **Supervisor override** with reason (audit trail)
- Understaffing comparison vs contract requirements

**Defer** automated roster generation wizard and fairness optimizer to Phase 3 (PROJECT_PLAN.md).

## Consequences

### Positive

- Supervisors retain control during early DogForce UAT
- Validation logic is testable independently of optimization algorithm
- Reduces go-live risk — wrong auto-roster is worse than slow manual roster

### Negative

- Higher supervisor workload until automation ships
- Client expectation management required (spec mentions automation)
- Mobile and attendance flows work with manual rosters only today

### Neutral

- Roster slots still link cleanly to attendance posting sheets
- Demo data in `security_demo_data` seeds manual roster batches for sales demos
