# Dogforce Feedback Implementation Plan

## Summary Of Confirmed Requirements

Dogforce confirmed that the system must support flexible client structures, monthly rostering, mixed billing, hourly guard pay, deductions, payroll reports, and management dashboards.

Key confirmed points:

- One client can have multiple sites.
- Work should focus strictly on guarding for now.
- Billing is a mixture of per guard, per shift, and monthly totals.
- VAT and invoice wording are standard across sites.
- Standard shifts are 06:00-18:00 and 18:00-06:00.
- Some sites are Monday-Friday or business-hours only.
- Rosters are prepared monthly.
- Grades run from A to E, with Grade A highest.
- Higher-grade guards can qualify for lower-grade posts.
- Firearm certification matters for assignment.
- English is the main language requirement; Afrikaans is secondary.
- Some guards must occasionally be excluded from specific clients or sites.
- Sunday and public holiday work pays 1.5x.
- Overtime is currently paid at normal rate, separate from Sunday/public holiday premium.
- Operations Manager approves overtime before payroll.
- Roster creators currently decide night shifts.
- The system must warn when one guard gets too many high-paying shifts.
- Attendance is currently manual through posting sheets at parade.
- GPS and checkpoint devices are not required for phase one.
- Guards are paid hourly under a no-work-no-pay system.
- Payroll is paid on the 16th of each month.
- Guard rates are currently standard, except supervisors and drivers.
- Common deductions include loans, uniforms, damages, absences, lateness, and disciplinary deductions.
- Printed payslips must show earning breakdowns.
- Management needs payroll expenditure, deductions total, loan deductions, hours worked, headcount, AWOLs, holidays, Sundays, and total payroll bill.
- Reports are needed by client, site, supervisor, guard, and period.
- Clients should receive attendance or service reports.
- Reports must export to Excel and PDF.

## Implementation Impact By Module

### `security_operations`

Already refactored to support:

- Clients with multiple client sites.
- Security posts under sites.
- Shift requirements under posts.
- Day-of-week scheduling.
- Per-shift guard count.
- Billing and pay rates on shift requirements.
- Fairness weight for high-paying shifts.
- Overtime allowed flag.
- Required certifications, languages, attributes, and reliability scores.

Next improvements:

- Add monthly roster generation wizard.
- Add site-specific guard exclusion rules.
- Add supervisor/roster creator tracking.
- Add fairness score warnings for night, Sunday, and public holiday allocations.
- Add standard day and night shift demo templates.

### `security_attendance`

Current module supports scheduled versus actual attendance.

Next improvements:

- Add manual posting-sheet batch entry workflow.
- Add absent/AWOL classification.
- Add no-work-no-pay hours summary.
- Add Sunday and public holiday detection.
- Add approved overtime hours, even though overtime is currently paid at normal rate.
- Add supervisor review state before payroll.

### `security_payroll_core`

Current module supports payroll periods, payslips, earnings, deductions, attendance, and leave links.

Next improvements:

- Generate payslip lines from attendance hours.
- Calculate hourly pay from grade or employee rate.
- Apply Sunday/public holiday 1.5x premium.
- Track normal hours, Sunday hours, public holiday hours, absent hours, and deductions separately.
- Support payroll cutoff/payment date rules for payment on the 16th.
- Add supervisor and driver rate exception handling.
- Add management payroll summary reports.

### `security_l10n_na`

Current module stores Namibia payroll rule sets, VAT, tax brackets, and public holidays.

Next improvements:

- Confirm Namibia public holiday list for the working year.
- Store Sunday/public holiday multiplier as 1.5.
- Store overtime multiplier as 1.0 for Dogforce for now.
- Keep overtime configurable so future clients can use double rate if required.

### `security_billing`

Current module supports billing plans, invoice lines, VAT, and billing analysis.

Next improvements:

- Generate monthly invoices from shift requirements and roster/attendance data.
- Support per guard/per shift billing automatically.
- Add invoice lines grouped by client site and post.
- Add client attendance/service report attachment basis.
- Keep VAT wording standard across all sites.

### `security_reporting`

Current module provides pivot/graph views for operations, attendance, payroll, incidents, billing, payments, and ageing.

Next improvements:

- Add dashboards for management KPIs.
- Add payroll expenditure dashboard.
- Add deduction and loan deduction dashboard.
- Add hours worked by guard report.
- Add AWOL/absence report.
- Add Sunday/public holiday hours report.
- Add reports by client, site, supervisor, guard, and period.
- Add export-ready list views for Excel/PDF.

### `security_documents`

Current module supports guard documents, expiry tracking, verification, and attachments.

Next improvements:

- Add firearm certificate tracking as a first-class document type.
- Link document requirements to assignment eligibility.
- Add missing-document warnings before roster assignment.

### Future `security_equipment`

Needed because Dogforce confirmed uniform, damage, and equipment-related deductions.

Planned scope:

- Uniform issue and return.
- Equipment issue and return.
- Damage/loss records.
- Deduction linkage to payroll.
- Firearm/radio/device issue tracking if required.

### Future `security_client_reports`

Needed because Dogforce confirmed clients should receive attendance or service reports.

Planned scope:

- Client attendance report.
- Client site service report.
- Monthly guarding summary.
- Export to PDF and Excel.
- Later integration with portal access.

## Recommended Next Build Order

1. Improve `security_operations` with monthly roster generation and site exclusions.
2. Improve `security_attendance` with manual posting-sheet batch entry and AWOL handling.
3. Improve `security_payroll_core` with hourly pay, Sunday/public holiday premium, and attendance-driven payslip generation.
4. Improve `security_billing` with monthly invoice generation from rosters/attendance.
5. Build `security_equipment`.
6. Build `security_client_reports`.
7. Build `security_portal`.
8. Build `security_mobile` last, after desktop workflows are stable.

## Immediate Dogforce Clarifications Still Needed

1. Confirm whether Sunday and public holiday premium applies to all guards or only specific contracts.
2. Confirm whether night shift has no extra premium.
3. Confirm whether overtime should be tracked separately even when paid at normal rate.
4. Confirm whether supervisor and driver rates are fixed amounts or separate grades.
5. Confirm the payroll period dates that lead to payment on the 16th.
6. Confirm whether AWOL means full unpaid shift, disciplinary incident, or both.
7. Confirm whether printed payslips should use Dogforce branding and signatures.
8. Confirm who should receive client service reports and how often.
