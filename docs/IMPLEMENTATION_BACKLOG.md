# Dogforce Odoo Implementation Backlog

Date: 2026-05-26

## Priority 0: Decisions Before Coding

- Confirm target Odoo version: Odoo 18 Community vs Odoo 19 Community.
- Confirm whether Dogforce will use Community-only, OCA modules, or paid Enterprise modules.
- Confirm current Dogforce Odoo version and database access method.
- Confirm authoritative Namibia payroll sources for PAYE, SSC, public holidays, VAT, and labor rules.
- Confirm whether live clock-in/out will be done through Odoo Attendances, imported device logs, mobile check-in, or manual supervisor entry.

## Priority 1: Reproducible Development Environment

- Add Docker Compose for Odoo + PostgreSQL.
- Add `custom_addons` directory.
- Add Odoo config with custom addons path.
- Add setup script for a clean local installation.
- Add backup and restore scripts.
- Add README with install, run, update apps, run tests, backup, and restore commands.

Definition of done:

- A clean laptop can clone the repo, run one setup command, start Odoo, and install the first custom module.

## Priority 2: `security_base`

- Scaffold module.
- Add guard profile extension on employee.
- Add grade model.
- Add certification model with expiry support.
- Add language and physical/medical attribute models.
- Add reliability score fields and initial manual adjustment log.
- Add disqualification flags.
- Add security groups and basic access rules.
- Add demo data.

Definition of done:

- A guard profile can be configured with grade, certifications, language, attributes, reliability, and home location.

## Priority 3: `security_operations`

- Scaffold module.
- Add security post and post type models.
- Add client site staffing requirements.
- Add 12-hour shift templates.
- Add roster slot model.
- Add manual roster views.
- Add validation for grade, certification, leave conflict, disqualification, 12-hour rest, and consecutive-day limits.
- Add supervisor override with reason.
- Add daily understaffing alert.

Definition of done:

- A supervisor can create a valid roster manually, and invalid assignments are blocked unless an approved override is recorded.

## Priority 4: `security_attendance`

- Scaffold module.
- Link roster slots to attendance records.
- Calculate scheduled hours, actual hours, valid hours, late minutes, early departure minutes, absence status, and missing checkout.
- Add supervisor correction workflow with reason.
- Add attendance summary model for payroll import.
- Add tests for day shift, night shift, late arrival, early departure, no-show, and missing checkout.

Definition of done:

- Scheduled-vs-actual attendance can produce clean payroll-ready summaries for a pay period.

## Priority 5: `security_l10n_na` Payroll Spike

- Scaffold Namibia localization module.
- Load NAD currency defaults.
- Load configurable Namibia public holiday records.
- Add PAYE bracket model with effective dates.
- Add SSC configuration: employee rate, employer rate, monthly cap.
- Add premium rate configuration: Sunday, public holiday, Saturday, night, overtime.
- Add tests for PAYE, SSC, Sunday premium, public holiday premium, and shift split across midnight.

Definition of done:

- Payroll formulas can be verified independently from the Odoo UI and match manually calculated expected values.

## Priority 6: `security_payroll_core`

- Scaffold module.
- Add payroll period model.
- Add work entry import from attendance summary.
- Add earning line and deduction line models.
- Add payslip model and PDF report.
- Add attendance, leave, loan, and behavioral import hooks.
- Add net pay calculation.
- Add payroll approval workflow.

Definition of done:

- A payroll officer can generate a test payslip from attendance data without manually typing worked hours.

## Priority 7: Leave, Loans, Discipline

- Build worked-time leave accrual rules.
- Deduct approved leave and unapproved absences without double deduction.
- Support negative leave cap.
- Add employee loans, installment schedule, payroll deduction, and loan statement.
- Add behavioral incident types, approval, payroll deduction, employee notification, and reliability score impact.

Definition of done:

- Leave, loan, and behavioral data flow into payroll automatically and are visible on the payslip.

## Priority 8: Billing and Invoicing

- Build Namibian invoice template.
- Add amount in words.
- Add VAT breakdown section.
- Add configurable branding fields.
- Generate invoice lines from contracts, roster, or attendance.
- Add email delivery template with PDF attachment.

Definition of done:

- A client invoice can be generated from service delivery data and printed on A4 with the required Namibia fields.

## Priority 9: Accounting and Banking Controls

- Configure bank journal support.
- Add import templates for bank statements if base/OCA functionality is insufficient.
- Add payment registration guidance/workflow.
- Add reconciliation audit log.
- Add write-off approval threshold.
- Add bank account detail change approval.
- Add report export audit log.
- Add role-based access rules for accountant, accounting manager, and view-only clerk.

Definition of done:

- An accountant can register a payment, import a statement, reconcile the transaction, and produce a bank reconciliation report with audit trail.

## Priority 10: Dogforce Migration

- Export/backup current Dogforce database.
- Create migration mapping workbook or CSV templates.
- Import employees.
- Import clients and contracts.
- Import posts/sites.
- Import opening leave balances.
- Import outstanding loans.
- Import outstanding invoices and accounting opening balances where needed.
- Produce migration validation report.

Definition of done:

- Dogforce signs off migrated master data, leave balances, loans, and opening accounting balances before go-live.

## Priority 11: Training and Go-Live

- Create supervisor training guide.
- Create HR/payroll training guide.
- Create accounting training guide.
- Create daily operations checklist.
- Create month-end payroll checklist.
- Create month-end invoicing and reconciliation checklist.
- Create production backup checklist.

Definition of done:

- Dogforce users can complete daily roster/attendance, payroll, invoice, and payment workflows without developer assistance.

