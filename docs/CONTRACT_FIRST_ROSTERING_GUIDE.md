# DogForce / DeployGuard — Contract-First Rostering Architecture Guide

## 1. Executive Summary & Core Objective

The DogForce operational platform simplifies setup by establishing the **Client Contract as the Single Source of Truth** for operational deployment.

### The Mental Model

```
                    ┌───────────────────────────┐
                    │      CLIENT (Partner)     │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │      CLIENT CONTRACT      │
                    │  (Commercial & Staffing)  │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │      CONTRACT SITES       │
                    │   (Physical Premises)     │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │      POSTS & RECIPES      │
                    │  (Staffing Requirements)  │
                    └─────────────┬─────────────┘
                                  │
                                  ▼
                    ┌───────────────────────────┐
                    │       ROSTER SLOTS        │
                    │   (21st to 20th Cycle)    │
                    └───────────────────────────┘
```

Non-technical operational supervisors and branch managers no longer navigate disparate configuration menus across multiple modules. They configure the contract in a single progressive workspace, and the system atomically synchronizes live operational sites, posts, and shift requirements.

---

## 2. Field Ownership Reference & Propagation Matrix

To prevent data desynchronization, every configuration attribute has an authoritative owner:

| Attribute / Configuration | Authoritative Owner | Propagation Target | Operational Role |
| :--- | :--- | :--- | :--- |
| **Client / Company** | `res.partner` | Read-only link on Contract | Billing entity |
| **Contract Ref & Dates** | `security.client.contract` | Read-only on Sites & Batches | Commercial period & billing cap |
| **Billing & Guard Rates** | `security.client.contract` (or requirement override) | `security.shift.requirement.bill_rate` | Invoicing & guard wage calculation |
| **Physical Sites & Address** | `security.contract.site` | `security.client.site` | GPS location, sector, premises |
| **Site Operations & Contacts**| `security.client.site` | Retained locally on site | Supervisor, emergency contact, notes |
| **Guard Posts (Gate, Patrol)**| `security.contract.post` | `security.post` | Static/patrol guarding position |
| **Shift Recipes (Days, Hours)**| `security.contract.shift.requirement`| `security.shift.requirement` | Days active (Mon-Sun), guard count |
| **Operational Schedule** | `security.roster.batch` | `security.roster.slot` | Slot assignments (21st–20th) |

---

## 3. Contract Workspace (`security_operations.contract_workspace`)

The Contract Workspace is an interactive OWL interface designed for progressive disclosure:

1. **Top Summary & Diagnostic Strip**:
   - Contract reference, status badge, 21st-to-20th cycle dates.
   - Aggregate metrics: Configured Sites, Posts, Shift Requirements, and Estimated Monthly Slots.
   - Setup Health Progress Bar (0% to 100%) and issue counter.
   - Action buttons: "Activate Operational Setup" and "Edit Contract Record".

2. **Tabs Structure**:
   - **Sites & Scope**: Visual card grid of all contracted sites with readiness status (`ready`, `incomplete`, `missing_posts`, `missing_shifts`). Includes quick site creation and setup duplication.
   - **Posts & Shifts (Recipe Builder)**: Drills down into an individual site. Displays security posts and recurring weekly shift recipes (with Mon-Sun active day pills). Offers quick actions: "Add Shift", "All Days", "Duplicate Shift", and "Rate Override".
   - **Rate Cards**: Client-agreed hourly bill rates categorized by shift and guard grade.
   - **Setup Health & Diagnostics**: Automated pre-flight validator. Lists missing posts, uncovered days, or unassigned supervisors with direct fix links.
   - **Review & Activate**: Pre-flight verification summary showing slot counts and operational guarantees prior to atomic activation.

---

## 4. Client Sites Operational Workbench (`security_operations.client_sites_workbench`)

The Operational Workbench replaces the flat sites list with a hierarchical client portfolio:

- **Filter Chips**:
  - `All Sites`: Complete company portfolio.
  - `Needs Setup`: Highlights sites with incomplete recipes or pending issues.
  - `Coverage Risk`: Sites with zero active posts or zero shift requirements.
  - `Expiring Contracts`: Contracts ending within 30 days.
  - `No Supervisor`: Sites missing an assigned operational supervisor.
- **Client Cards**: Collapsible sections grouping sites by client company with active contract indicators.
- **Quick Actions Per Site**:
  - `Contract Setup`: Launches the Contract Workspace for the site's parent contract.
  - `Site Hub`: Opens the calendar and daily attendance command center.
  - `Site Ops`: Opens the operational site record.
  - `Generate Roster`: Triggers roster batch generation for the upcoming 21st–20th cycle.

---

## 5. Operational Cycle: 21st to 20th

DogForce operational rostering and payroll cutoff operates on a **21st to 20th monthly cycle** (rather than the calendar month).

### Calculation Logic
- If reference date is on or after the 21st:
  - Cycle starts on the 21st of current month and ends on the 20th of next month (e.g., 21 March 2026 to 20 April 2026).
- If reference date is before the 21st:
  - Cycle starts on the 21st of previous month and ends on the 20th of current month (e.g., 21 February 2026 to 20 March 2026).

Roster batch generation jobs and auto-assign cron tasks run against this operational window.

---

## 6. Deterministic Fairness Constraints

The automated shift assignment engine enforces hard fairness and labor constraints deterministically:

1. **Max 1 Sunday per Guard per Cycle**:
   - Guards may be assigned to a maximum of **1 Sunday** per 21st-to-20th cycle.
   - If a guard has an existing confirmed or active Sunday slot in the cycle, subsequent Sunday slots reject the guard with: `"Exceeded Sunday limit (max 1 Sunday per cycle)"`.
2. **Max Working Days Limit (Default 22 Days)**:
   - Configured via system parameter `security_roster.max_working_days_per_cycle`.
   - Protects guard fatigue by ensuring rest periods across the cycle.
3. **Rest Intervals (Day/Night Transitions)**:
   - Guards completing a night shift (18:00 – 06:00) cannot be assigned to a morning day shift (06:00 – 18:00) on the same day (minimum 12 hours rest required).
4. **Historical Protection**:
   - Confirmed and published roster slots are never modified by auto-generation runs.

> ⚠️ **Note**: The experimental AI optimizer is permanently parked. Only deterministic scheduling logic is active.

---

## 7. Migration & Duplicate Normalization

### Legacy Contract Migration Wizard (`security.legacy.contract.migration.wizard`)
- Maps existing operational sites, posts, and shift requirements into contract-managed hierarchy.
- Preserves all database record IDs (`security.client.site`, `security.post`, `security.shift.requirement`).
- Guarantees 100% preservation of historical rosters, shifts, and attendance logs.

### Duplicate Detection & Normalization Wizard (`security.duplicate.audit.wizard`)
- Detects near-identical client names (e.g., `"Namibia Breweries"` vs `"Namibia Breweries Ltd"`).
- Detects duplicate site names under the same client and corrupt single-character/numeric records.
- Dry-run audit displays all candidates with approve/dismiss toggles.
- Safe merge reassigns operational links to the keeper record and safely archives the duplicate (`active = False`). **Records are never deleted from the database.**

---

## 8. Verification & Acceptance Testing

Test coverage has been implemented in:
- `custom_addons/security_operations/tests/test_contract_workspace.py`:
  - 21st-20th cycle calculation
  - Setup health pre-flight check blocking incomplete activations
  - Multi-site contract atomic activation and synchronization
  - Rate card inheritance and explicit requirement overrides
  - Legacy contract structure migration
  - Safe duplicate normalization
- `custom_addons/security_shift_planner/tests/test_fairness_constraints.py`:
  - Max 1 Sunday hard constraint
  - Max working days limit
  - Day/night rest intervals
- `custom_addons/security_client_onboarding/tests/test_onboarding_wizard.py`:
  - End-to-end creation of client, contract, sites, posts, and shift recipes
