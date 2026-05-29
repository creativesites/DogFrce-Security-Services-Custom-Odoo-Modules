# Current Modules Technical Guide

Date: 2026-05-27

This document explains the current technical state of the custom Odoo Security Suite in the `odoo-security` database.

Installed modules:

- `security_base`
- `security_operations`
- `security_attendance`

## 1. Technical Purpose

The current implementation establishes the first three layers of the reusable security-company architecture:

1. **Identity and qualification layer**
   - `security_base`
2. **Operational planning layer**
   - `security_operations`
3. **Actual attendance comparison layer**
   - `security_attendance`

This matches the intended roadmap for Dogforce and other future security-company deployments.

## 2. Module Responsibilities

### `security_base`

Responsibility:

- define security-domain master data
- extend `hr.employee` with guard-specific operational fields

Main technical outputs:

- new master-data models for grades, certifications, language skills, attributes, and disqualification reasons
- reliability adjustment model
- employee form extension
- security-specific user groups

Files:

- [__manifest__.py](/Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_base/__manifest__.py)
- [hr_employee.py](/Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_base/models/hr_employee.py)
- [security_master_data.py](/Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_base/models/security_master_data.py)

### `security_operations`

Responsibility:

- define security field operations structures
- provide a roster planning base

Main technical outputs:

- post type model
- post model
- shift template model
- site requirement model
- roster slot model
- roster assignment eligibility constraints

Files:

- [__manifest__.py](/Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_operations/__manifest__.py)
- [security_operations.py](/Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_operations/models/security_operations.py)

### `security_attendance`

Responsibility:

- link roster planning to actual recorded attendance
- compute operational attendance metrics

Main technical outputs:

- attendance record model linked to roster slot
- scheduled start and end computation from shift template
- attendance metrics: worked hours, valid hours, late minutes, early departure minutes, missing checkout, status

Files:

- [__manifest__.py](/Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_attendance/__manifest__.py)
- [security_attendance.py](/Users/winstonzulu/Documents/GitHub/DogFrce%20Security%20Services%20Custom%20Odoo%20Modules/custom_addons/security_attendance/models/security_attendance.py)

## 3. Current Data Model

### Base Models

`security.grade`

- grade definition
- sequencing is currently used as a proxy for ordering and minimum-grade checks

`security.certification`

- certification definition
- includes `expiry_required` flag but does not yet implement expiry records per employee

`security.language`

- language or communication skill tag

`security.attribute`

- physical, medical, training, or other operational attribute

`security.disqualification.reason`

- standard reason catalog for blocking assignment

`security.reliability.adjustment`

- tracks manual changes to reliability score

### Employee Extension

`hr.employee` is extended with:

- `security_guard`
- `security_grade_id`
- `security_certification_ids`
- `security_language_ids`
- `security_attribute_ids`
- `security_reliability_score`
- `security_home_location`
- `security_medical_fitness_grade`
- `security_disqualified`
- `security_disqualification_reason_id`
- `security_disqualification_note`
- reliability adjustment relation and total

### Operations Models

`security.post.type`

- abstract post requirement template
- minimum grade
- required certifications

`security.post`

- actual client-facing deployment location
- links to partner, post type, shift template, and required guard count

`security.shift.template`

- generic shift definition
- start and end hour stored as floats
- duration computed, including overnight shifts

`security.site.requirement`

- client requirement by post type
- preferred guards

`security.roster.slot`

- planned work item for one guard on one post on one date
- stores state
- validates employee assignment suitability

### Attendance Model

`security.attendance.record`

- one attendance record per roster slot in current design
- derives schedule from roster slot and shift template
- stores actual timestamps
- computes:
  - `scheduled_hours`
  - `worked_hours`
  - `valid_hours`
  - `late_minutes`
  - `early_departure_minutes`
  - `missing_check_out`
  - `status`

## 4. Current Validation Logic

### Roster Eligibility

In `security.roster.slot`:

- disqualified guards are blocked
- guards without grade are blocked when a minimum grade is required
- guards below the required grade are blocked
- guards missing required certifications are blocked

Implementation note:

The minimum-grade comparison currently relies on the `sequence` field on `security.grade`. This is acceptable for an initial build, but later it should be hardened with an explicit ranking strategy to avoid ambiguity.

### Attendance Computation

In `security.attendance.record`:

- scheduled start and end are derived from the roster slot date and shift template
- overnight shifts are handled by rolling end time to the next day
- absence is inferred when both `check_in` and `check_out` are missing
- incomplete attendance is inferred when `check_in` exists but `check_out` does not
- valid hours are computed as overlap between scheduled and actual time

## 5. Odoo 19 Compatibility Lessons Already Found

Two Odoo 19 issues were discovered and corrected during installation:

1. `res.groups` classification changed
   - `category_id` could not be used
   - `privilege_id` had to be used instead

2. XML menu parent references must use the correct module XML ID prefix
   - `security_operations.menu_security_posts` is the valid parent reference

This is important because it confirms the code is being exercised against real Odoo 19 behavior, not just written statically.

## 6. Current User Interface Structure

### Top-Level Menu

- `Security`

### Configuration Area

Provided by `security_base`:

- Grades
- Certifications
- Language Skills
- Attributes
- Disqualification Reasons

### Operations Area

Provided by `security_operations` and `security_attendance`:

- Post Types
- Shift Templates
- Security Posts
- Site Requirements
- Roster Slots
- Attendance Records

## 7. How This Maps To Dogforce Requirements

### Already Addressed Directly

From Dogforce’s functional specification, the current implementation already begins to cover:

- security posts as locations
- guard grading
- certifications
- language skills
- physical and medical attributes
- reliability score
- home location
- roster structure
- scheduled shift basis
- actual clock-in and clock-out comparison
- late and early departure calculation
- missing checkout tracking

### Partially Addressed

- 12-hour shifts
  - supported through shift templates
  - not yet locked as a company-wide default rule

- attendance linked to planned shifts
  - supported through roster slot linkage
  - not yet linked to leave or payroll

### Not Yet Addressed

- leave accrual and deduction
- automatic absence deduction rules
- payroll integration
- Sunday and public holiday premiums
- loans
- behavioral deductions
- auto-rostering
- invoicing
- banking and reconciliation
- Namibia localization

## 8. How This Fits Real Security-Company Operations

Security operations generally follow this order:

1. define qualifications
2. define sites and post types
3. assign guards to posts
4. record actual attendance
5. compute leave and payroll outcomes
6. invoice clients based on service delivery

The current suite already supports the first four steps at a foundational level.

That makes it useful not only for Dogforce, but also as the reusable starting product for other security companies.

## 9. Known Gaps and Design Risks

### Grade Ordering

Risk:

- `sequence` is being used as grade ranking

Future improvement:

- explicit numeric rank or policy-based rank comparison

### Certification Expiry

Risk:

- certification records exist, but employee-level expiry dates are not yet modeled

Future improvement:

- employee certification relation model with issue date, expiry date, and status

### Attendance Integrity

Risk:

- current attendance allows manual entry without approval flow

Future improvement:

- supervisor override workflow with reason codes and audit trail

### Roster Constraints

Risk:

- current roster logic does not yet enforce:
  - 12-hour rest between shifts
  - maximum consecutive days
  - client-specific preferred guard scoring

Future improvement:

- extend `security.roster.slot` validation and later add auto-assignment logic

## 10. Recommended Next Module

The next module should be:

- `security_leave`

Reason:

- Dogforce’s business flow requires attendance and leave to interact directly
- leave is the missing operational bridge before payroll
- payroll should not be built before leave and absence rules are correctly modeled

## 11. Recommended Near-Term Technical Work

After `security_leave`, the next practical sequence should be:

1. `security_leave`
2. add attendance summary and supervisor override refinement
3. `security_l10n_na`
4. `security_payroll_core`

That order preserves business correctness and keeps Namibia-specific logic separate from generic security operations.

