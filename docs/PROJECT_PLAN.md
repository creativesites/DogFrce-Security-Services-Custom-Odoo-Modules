# Dogforce Security Services Odoo Customization Plan

Date: 2026-05-26

## 1. Project Positioning

The project should be treated as two related but separate outcomes:

1. **Dogforce implementation**: a working Odoo system for Dogforce Security Services in Namibia, delivered against their functional specification.
2. **Reusable Security Suite**: a clean set of configurable Odoo modules that can later be adapted for Zambia and other countries.

The Dogforce engagement should not become a one-off hardcoded system. Anything specific to Namibia belongs in a Namibia localization module. Anything specific to Dogforce belongs in a Dogforce migration/configuration module. The core security operations logic should remain country-neutral.

## 2. Recommended Platform Decision

Use **Odoo Community Edition**, but do not assume Odoo Community already contains everything required by the specification.

Official Odoo documentation currently lists Odoo 19.0 as a supported version released in September 2025 with planned support until September 2028, and Odoo 18.0 with planned support until September 2027. The practical recommendation is:

- Use **Odoo 18 Community** if available OCA/community modules for payroll, accounting, reports, or deployments are materially more mature for the 4-week Dogforce delivery.
- Use **Odoo 19 Community** if you are building most custom logic yourself and want the longer support window.
- Do a short technical spike before committing: install both Odoo 18 and Odoo 19 locally, check required OCA module availability, and choose one version before writing business modules.

Do not depend on proprietary Enterprise modules unless Dogforce explicitly agrees to Enterprise licensing. In particular, payroll, planning, advanced accounting/reconciliation, approvals, and some accounting controls may need either custom Community modules, OCA modules, or Enterprise licensing.

Reference: https://www.odoo.com/documentation/19.0/administration/supported_versions.html

## 3. Main Scope From Dogforce Documents

The functional specification covers:

- System defaults: NAD currency, 12-hour shifts, Namibian public holidays.
- Guard operations: security posts, site requirements, automated rostering, grade/certification/attribute matching, supervisor overrides, understaffing alerts.
- Attendance: scheduled-vs-actual comparison, late/early/absent calculation, missing checkout handling, exception approval.
- Leave: accrual based on actual worked time, automatic deductions, negative balance caps, de-duplication between approved leave and attendance absence.
- Payroll: PAYE, SSC, Sunday/public holiday/night/Saturday/overtime premiums, shift splitting across midnight/holiday boundaries, loans, behavioral deductions, allowances, payslip summaries, compliance reports.
- Invoicing: Namibian invoice format, VAT breakdown, amount in words, branding, auto-invoicing from contracts/timesheets, email delivery.
- Banking: journals, statement import, payment registration, reconciliation, partial/overpayments, write-offs, roles, audit logs, 2FA for accounting roles, bank account change approval.
- Reports: SSC, PAYE, behavioral deductions, loan statements, bank reconciliation, aged receivables, daily cash position.
- Migration: existing Odoo data must be backed up, mapped, migrated, verified, and signed off.

## 4. Architecture Principles

1. **Country-neutral core, country-specific packs**: roster, attendance, leave, and base guard profiles should work in any country. Namibia-specific PAYE, SSC, VAT, public holidays, and invoice wording belong in `security_l10n_na`.
2. **Configuration over code**: grades, certifications, leave accrual rules, premium rates, behavioral deduction types, trust-post exclusions, tax brackets, SSC rates, public holidays, invoice branding, and approval thresholds must be records/settings.
3. **Dogforce-specific data stays isolated**: migrations, default Dogforce settings, and client-specific imports belong in `security_dogforce_migration`, not the reusable modules.
4. **MVP before automation**: build manual/controlled workflows first, then automate. A correct manual roster with validations is more valuable than a fragile auto-roster.
5. **Auditability is a product feature**: attendance overrides, roster overrides, payroll deductions, write-offs, bank account changes, and exported reports need audit records.
6. **Payroll calculations must be test-driven**: every tax, SSC, premium, shift split, leave deduction, loan deduction, and behavioral deduction rule needs automated tests.

## 5. Proposed Repository Structure

```text
.
├── custom_addons/
│   ├── security_base/
│   ├── security_operations/
│   ├── security_attendance/
│   ├── security_leave/
│   ├── security_payroll_core/
│   ├── security_l10n_na/
│   ├── security_loans/
│   ├── security_discipline/
│   ├── security_billing/
│   ├── security_accounting_controls/
│   └── security_dogforce_migration/
├── deploy/
│   ├── docker-compose.yml
│   ├── odoo.conf
│   ├── requirements.txt
│   └── setup.sh
├── docs/
│   ├── PROJECT_PLAN.md
│   ├── IMPLEMENTATION_BACKLOG.md
│   ├── DEPLOYMENT_MANUAL.md
│   └── USER_TRAINING_GUIDE.md
└── tests/
    └── test_scenarios.md
```

## 6. Module Design

### `security_base`

Reusable foundation for security companies.

- Extends employees with guard profile fields.
- Models grade levels, certifications, language skills, physical/medical attributes, reliability score, and home location.
- Tracks certification expiry and disqualification flags.
- Adds security user groups: Security Supervisor, HR/Payroll Officer, Accountant, Accounting Manager, View Only Clerk, System Auditor.

### `security_operations`

Reusable operations layer.

- Models security posts, post types, client site requirements, contract staffing requirements, 12-hour shift templates, and roster slots.
- Supports manual roster creation with validation rules.
- Adds audit logs for roster overrides.
- Generates understaffing alerts by comparing rostered guards to contract requirements.

### `security_attendance`

Reusable attendance comparison layer.

- Links scheduled roster slots to actual check-in/check-out records.
- Calculates late minutes, early departure minutes, absence status, missing checkout, worked hours, and valid scheduled hours.
- Requires supervisor reason codes for manual corrections.
- Produces attendance summaries for payroll.

### `security_leave`

Reusable leave accrual and deduction layer.

- Adds worked-time-based accrual rules.
- Prevents double deduction when approved leave already covers an absence.
- Supports negative leave caps and low-balance alerts.
- Blocks rostering during approved leave periods.

### `security_payroll_core`

Reusable payroll computation engine for Community Edition.

- Defines payroll periods, work entries, earnings, deductions, allowances, payslip lines, and calculation summaries.
- Imports attendance, leave, loans, and approved incidents.
- Produces payslip PDFs and exportable payroll reports.

If Odoo Enterprise payroll is used later, this module should become an adapter rather than duplicating Enterprise functionality.

### `security_l10n_na`

Namibia localization pack.

- Sets NAD as default currency.
- Loads Namibian public holidays.
- Stores Namibia PAYE brackets with effective dates.
- Stores SSC rates and cap.
- Stores Namibia VAT defaults and invoice legal text.
- Adds Namibian payroll reports: PAYE summary and SSC submission.

### `security_loans`

Reusable employee loan module.

- Tracks loan amount, interest, repayment schedule, payroll deductions, remaining balance, and loan statements.
- Supports final payslip settlement and debt notice generation.

### `security_discipline`

Reusable behavioral incident and trust scoring module.

- Configurable incident types, deduction amounts, approval workflow, evidence attachments, and score impact.
- Sends employee notifications after approval.
- Flags employees with repeated incidents and excludes them from high-trust posts.

### `security_billing`

Reusable contract-to-invoice module.

- Converts client contract staffing, roster, or attendance data into invoice lines.
- Supports recurring monthly billing, ad-hoc services, and per-shift billing.
- Provides amount-in-words support and invoice service summaries.

### `security_accounting_controls`

Accounting and banking controls.

- Configures bank journals and statement import templates where Community functionality is insufficient.
- Adds audit logging around reconciliation, write-offs, report exports, and bank detail changes.
- Adds approval workflow for bank account detail changes.
- Enforces group-based access rules. If full 2FA enforcement by role cannot be implemented safely in Community, document it as a deployment/security policy or use an Enterprise/OCA-supported approach.

### `security_dogforce_migration`

Dogforce-only migration and configuration.

- Imports old Odoo data or CSV exports.
- Maps existing employees, clients, contracts, posts, balances, loans, and accounting records.
- Seeds Dogforce-specific settings.
- Provides migration logs and reconciliation reports.

## 7. Delivery Strategy

### Phase 0: Discovery and Technical Spike

Duration: 2-3 days.

Deliverables:

- Confirm Dogforce's current Odoo version, hosting method, database size, installed apps, customizations, and data quality.
- Confirm whether they accept Community-only custom build, OCA modules, or Enterprise licensing.
- Install chosen Odoo version locally with reproducible Docker setup.
- Create sample database with Dogforce-like demo data.
- Finalize module dependency strategy.

Exit criteria:

- Version chosen.
- Deployment method chosen.
- Data migration source confirmed.
- No hidden Enterprise dependency in the agreed MVP.

### Phase 1: Dogforce MVP

Target: first usable operational system.

Deliverables:

- NAD currency and 12-hour shifts configured.
- Security posts, guards, grades, certifications, client requirements.
- Manual roster with validation and override logs.
- Attendance comparison against scheduled shifts.
- Late/early/absent calculations.
- Basic leave deduction rules.
- Basic payslip calculation with attendance import.
- Basic Namibia invoice template with VAT and amount in words.

Exit criteria:

- One test site can be rostered.
- Guards can clock in/out or have attendance imported.
- Attendance summary flows to payroll.
- One invoice can be produced for a client.

### Phase 2: Payroll, Leave, Loans, Discipline

Deliverables:

- Namibia PAYE and SSC calculation tables.
- Sunday, public holiday, Saturday, night, and overtime premiums.
- Shift splitting across midnight and public holiday boundaries.
- Leave accrual based on actual worked time.
- Loan deductions and loan statements.
- Approved behavioral incidents feeding payroll and reliability score.
- Payslip PDF with required breakdown.

Exit criteria:

- Payroll test run matches manual calculations to N$0.01.
- Payslip shows attendance, leave, loans, behavioral deductions, PAYE, SSC, and net pay.
- Repeated incidents affect roster eligibility.

### Phase 3: Auto-Rostering

Deliverables:

- Candidate filtering by grade, certification, expiry, leave, disqualification, rest rules, and maximum consecutive days.
- Scoring by client requests, grade suitability, reliability, distance, and fair rotation.
- Supervisor override with reason.
- Understaffing alerts.

Exit criteria:

- A site requiring Grade B1 + Firearm Certified only receives eligible guards.
- No guard is assigned more than 12 hours in 24 hours.
- No guard exceeds configured consecutive-day limits without exception.

### Phase 4: Billing, Banking, Reconciliation, Reports

Deliverables:

- Auto-invoice from contracts, roster, or attendance.
- Email delivery of PDF invoices.
- Payment registration workflow.
- Bank statement import and matching support.
- Partial payment, overpayment, and write-off handling.
- Bank reconciliation, aged receivables, daily cash position, behavioral, loan, PAYE, and SSC reports.
- Audit trail for reconciliation and exports.

Exit criteria:

- Imported bank statement can be matched to an invoice payment.
- Partial and overpayment scenarios are handled.
- Month-end report pack can be exported to PDF/Excel.

### Phase 5: Migration, Training, Go-Live

Deliverables:

- Full backup of old system.
- Migration mapping and trial migration.
- Data validation sign-off.
- User training for supervisors, HR/payroll, and accounting.
- Production deployment.
- 30-day support process.

Exit criteria:

- Dogforce signs off migrated master data and balances.
- Users can complete daily attendance, roster, payroll, invoicing, and payment workflows.
- Production backup and restore process is documented and tested.

## 8. Four-Week On-Site Plan

The current proposal promises a very broad scope in 4 weeks. Treat 4 weeks as an **on-site MVP and rollout window**, not the full reusable productization timeline.

### Week 1: Foundation and MVP Operations

- Confirm version, backup existing database, and set up local/dev environment.
- Build or install foundation modules.
- Configure employees, posts, grades, certifications, shift templates, and client requirements.
- Deliver manual roster and scheduled-vs-actual attendance comparison.

### Week 2: Payroll MVP and Leave

- Implement attendance-to-payroll import.
- Implement core Namibia payroll calculations: basic pay, PAYE, SSC, Sunday/public holiday/Saturday/night/overtime premiums.
- Implement basic leave deductions and leave balances.
- Produce first payroll test run.

### Week 3: Loans, Discipline, Invoicing, Auto-Roster

- Add loans and behavioral deductions into payroll.
- Build branded Namibian invoice template.
- Start auto-roster candidate filtering and scoring.
- Run end-to-end scenario: roster -> attendance -> leave/payroll -> payslip -> invoice.

### Week 4: Migration, Banking, Reports, Training

- Perform trial and final migration.
- Configure accounting journals and payment registration.
- Implement/report around bank reconciliation as far as Community/OCA stack allows.
- Train users and collect sign-off.

Remote buffer after return: at least 1-2 weeks for fixes, hardening, and productization cleanup.

## 9. First Build Backlog

### Sprint 1: Reproducible Environment

- Create Docker Compose for Odoo + PostgreSQL.
- Add `custom_addons` path.
- Add setup script and README.
- Add demo database creation notes.
- Add backup/restore commands.

### Sprint 2: Base Data Model

- Create `security_base`.
- Add guard profile fields to employees.
- Create grade, certification, language, attribute, and disqualification models.
- Add security groups and record rules.
- Add demo guards.

### Sprint 3: Posts and Roster MVP

- Create `security_operations`.
- Add posts, post types, client staffing requirements, shift templates, roster slots.
- Add roster validation rules.
- Add supervisor override reason logging.

### Sprint 4: Attendance Comparison

- Create `security_attendance`.
- Link roster slots to attendance.
- Calculate late, early, absent, missing checkout, worked hours, valid hours.
- Add daily understaffing alert.

### Sprint 5: Namibia Payroll Spike

- Create `security_payroll_core` and `security_l10n_na`.
- Implement PAYE/SSC config tables.
- Implement shift premium calculation and split-by-midnight/holiday tests.
- Generate a simple payslip summary.

## 10. Acceptance Test Scenarios

Build these as demo data plus automated tests where possible:

- Grade/certification roster matching: Grade B1 + Firearm post excludes unqualified guards.
- Rest rule: no guard can be assigned consecutive 12-hour shifts without configured rest.
- Leave block: approved leave prevents rostering and avoids duplicate attendance deduction.
- Sunday premium: 12-hour Sunday shift pays 12 x 1.5.
- Holiday split: shift crossing into a public holiday splits pay rates correctly.
- Loan deduction: active loan deducts installment and updates balance.
- Behavioral deduction: approved incident appears on next payslip and reduces reliability.
- Payroll integration: attendance, leave, loans, and incidents import without manual entry.
- Invoice: VAT, amount in words, service period, guard count, shift details, and bank details render correctly.
- Payment/reconciliation: payment can be registered and matched to an imported statement line.

## 11. Major Risks

- **Scope risk**: The functional specification is larger than a typical 4-week build. Control it with MVP sign-off and a remote hardening phase.
- **Community Edition gaps**: Payroll, planning, approvals, advanced reconciliation, and 2FA enforcement may require custom code, OCA modules, or Enterprise licensing.
- **Compliance risk**: PAYE, SSC, labor rules, public holidays, and VAT must be verified against official/current Namibian sources before production payroll.
- **Migration risk**: The old Odoo system may contain inconsistent employee, contract, leave, accounting, or payroll data. Budget time for data cleanup.
- **Auto-roster complexity**: Optimization can become open-ended. Start with deterministic rule filtering and scoring before advanced optimization.
- **Legal/payroll liability**: Payroll calculations should be signed off by Dogforce finance/HR using manual comparison before go-live.

## 12. Commercial Recommendation

For Dogforce, present the current 4-week engagement as:

- On-site implementation and MVP rollout.
- Full migration and training.
- 30-day bug-fix support.
- Separate optional maintenance contract for tax table updates, new country localizations, feature enhancements, hosting support, and annual upgrades.

For the reusable product, package modules into tiers only after Dogforce has validated the core workflow:

- Basic: guard profiles, posts, manual roster, attendance, basic leave, basic payroll.
- Pro: auto-roster, loans, behavioral deductions, invoices, richer reports.
- Enterprise-style: accounting controls, bank reconciliation enhancements, audit exports, multi-country localization, advanced dashboards.

Avoid promising country expansion until Namibia is cleanly isolated into `security_l10n_na`. Zambia should be implemented later as `security_l10n_zm`, not by editing Namibia code.

