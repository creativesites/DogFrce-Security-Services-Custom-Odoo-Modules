FUNCTIONAL SPECIFICATION
Objective
Modify Odoo's Attendance, Payroll, Time Off, Inventory, Contract Management, Accounting, and Banking modules to operate according to Namibian standards and security industry requirements, with full integration between all modules.
SYSTEM-WIDE CONFIGURATION
#
Functional Requirement
S1
All monetary values across the entire system must be in NAD (Namibian Dollar) as the default currency.
S2
All shifts are configured as 12-hour shifts by default. The system must calculate overtime, late arrivals, and early departures based on a 12-hour shift standard.
S3
The system must recognize Namibian public holidays for premium pay calculations.

1. ATTENDANCE & ROSTER FUNCTIONALITY
1.1 Basic Attendance Tracking
#
Functional Requirement
A1
Allow creation of Security Posts (e.g., "Gate 1," "Gate 2 etc 3") as locations. Each Post has its own shift schedule.
A2
All shifts are 12 hours in duration by default (e.g., 06:00-18:00 or 18:00-06:00).
A3
Track actual clock-in/out times against scheduled shift times — not just raw timestamps.
A4
Calculate late minutes (any clock-in after scheduled start time), early departure minutes (any clock-out before scheduled end time), and absent shifts automatically.
A5
Flag any shift where actual worked hours exceed legal daily limits (set at 12 hours max — any overtime beyond 12 hours requires exception approval).
A6
Allow a supervisor to manually override attendance records with reason code (e.g., "Sick or AWOL or change of duty post").
A7
Generate a daily understaffing alert when scheduled guards are fewer than client contract requires.

1.2 Automatic Roster Generation Based on Guard Characteristics & Grading
#
Functional Requirement
A8
Automatically generate weekly/monthly rosters based on the following guard characteristics (no manual scheduling allowed):
A9
Each guard must have a profile containing:
• Grade Level (e.g., A, B, C, D, E1, E2) — determines pay rate, responsibility level, and allowed post types
• Certification Tags (e.g., "Firearm Licensed," "First Aid Certified," "CCTV Trained," "Cash-in-Transit Certified")
• Physical Attributes (e.g., "Height > 1.8m" for certain posts, "Medical Fitness Grade")
• Language Skills (e.g., "English Speaking/Afrikaans," "Local Language")
• Reliability Score (0-100 based on attendance history and behavioral deductions)
• Home Location 
A10
The roster generation system must match guards to posts using these rules:
• Certain posts require minimum Grade Level (e.g., "Cash-in-Transit" requires Grade B1 or higher)
• Certain posts require specific certifications (e.g., "CCTV Room" requires CCTV Certified)
• Certain clients request specific guards (override rule)
• No guard assigned to more than 12 hours in a 24-hour period (standard shift is 12 hours, so no consecutive shifts without 12-hour break)
• No guard assigned to more than 6 consecutive days without a rest day
A11
The roster system must prioritize assignment based on:
Client-specific guard requests
Highest Grade Level available for high-responsibility posts
Highest Reliability Score for sensitive posts
Lowest travel distance (home to post)
 Fair rotation — high-grade guards should not be over-assigned
A12
Allow supervisor to manually override auto-generated roster with approval reason. All overrides logged for audit.
A13
If a guard is disqualified from a post (e.g., certification expired, behavioral flag), system automatically excludes them from consideration for that post type.

2. LEAVE MANAGEMENT & AUTOMATED ACCRUAL
#
Functional Requirement
L1
Automatically calculate leave accrual based on actual attendance hours worked (not scheduled hours). Security guards with 12-hour irregular shifts accrue leave proportionally to hours physically worked.
L2
Configure different leave types with separate accrual rules: Annual leave, Sick leave, Family responsibility leave, Unpaid leave, Compensatory leave (overtime conversion).
L3
For leave types that are "Based on Worked Time", the system must NOT count absence days (leave taken, sick days, public holidays) toward leave accrual. Only actual worked days/hours count.
L4
Define accrual milestones/rules such as: "Employee earns 1.25 days of annual leave per 17 days worked" or "Sick leave accrues at 1 day per 30 days worked, capped at 30 days per year." (12-hour shifts count as 1 day for leave purposes.)
L5
Automatically deduct leave days from employee's available balance when: (a) A time off request is approved, OR (b) The employee is marked absent in attendance with "Absent - No Approval" status.
L6
Prevent attendance from generating leave deduction twice — if a time off request is approved, the corresponding attendance absence must NOT also deduct leave again. System must de-duplicate.
L7
Allow negative leave balance up to a configurable cap (e.g., -5 days) for emergency situations before accrual catches up.
L8
Generate leave balance alerts when employee falls below minimum threshold (e.g., 2 days remaining) or goes into negative balance.



3. LINK BETWEEN ROSTER, ATTENDANCE, AND LEAVE
#
Functional Requirement
Data Flow
L9
The roster determines which employees are scheduled to work on which 12-hour shifts.
Roster → Attendance
L10
The attendance module captures actual clock-in/out. Compare roster vs attendance to identify: Present, Late, Early Leave, Absent (No Show), Absent (Approved Leave).
Attendance → Comparison
L11
When employee is marked "Absent (No Show)" in attendance with no approved time off request, the system automatically: (a) Deduct 1 day from annual leave balance (if available), OR (b) Deduct from unpaid leave (if annual leave exhausted).
Attendance → Leave Deduction
L12
When employee submits and gets approval for time off request, the system automatically: (a) Blocks the employee from being rostered during those dates, (b) Marks attendance as "Excused Absence", (c) Deducts leave balance by number of days/hours requested.
Time Off → Roster + Attendance + Leave
L13
The payroll module must receive from attendance: Total hours worked (based on 12-hour shifts), Overtime hours, Late deductions, Absence deductions.
Attendance → Payroll
L14
The payroll module must receive from leave module: Leave days taken, leave balance remaining, Any unpaid leave deductions.
Leave → Payroll
L15
The payslip must display a consolidated summary showing: Days worked (12-hour shifts), Days absent (approved leave), Days absent (unapproved = unpaid deduction), Leave balance after this period.
Payroll → Payslip

4. PAYROLL & PAYSLIP FUNCTIONALITY
4.1 Basic Payroll Calculation
#
Functional Requirement
P1
All monetary values in payroll are in NAD (Namibian Dollar) .
P2
Calculate PAYE using official Namibian tax brackets (updateable annually via configuration, not code).
P3
Calculate Social Security Commission (SSC) contribution — 0.9% employee, 0.9% employer, capped at N$7,100 monthly salary.

4.2 Overtime & Premium Pay
#
Functional Requirement
P4
Automatically calculate overtime and premium pay at these rates:
• Sunday work — 1.5× normal hourly rate (automatic, no approval needed)
• Public Holiday work — 1.5× normal hourly rate (automatic, no approval needed)
• Weekday Night Shift (20:00 - 06:00) — 1.25× normal hourly rate
• Saturday work — 1.25× normal hourly rate
• Overtime beyond 12 hours in a shift — 1.5× for any additional hours (since standard shift is 12 hours)
P5
The system must detect Sundays and Public Holidays from a configurable calendar (Namibian public holidays list pre-loaded). No manual flagging required per shift.
P6
If a 12-hour shift spans both a normal day and a public holiday (e.g., 18:00 to 06:00 crossing midnight into a holiday), the system must split the shift and apply the correct rate to each portion.

4.3 Loan Deductions
#
Functional Requirement
P7
Allow creation of employee loans with: Loan amount (NAD), Interest rate (if applicable), Repayment period (months), Start date, Deduction amount per payroll cycle.
P8
During each payroll run, automatically deduct the loan installment from employee's net pay if the loan is active.
P9
Track remaining loan balance after each deduction. When balance reaches zero, stop deductions automatically.
P10
Allow multiple active loans per employee. Deduct all installment amounts in same payroll run.
P11
Generate a loan statement for employee showing: Original amount, Each deduction made, Remaining balance.
P12
If an employee resigns with an outstanding loan balance, system must: (a) Deduct full remaining balance from final payslip (if sufficient funds), OR (b) Generate a debt collection notice to HR.

4.4 Behavioral Deductions
#
Functional Requirement
P13
Allow creation of behavioral deduction types with configurable amounts (NAD):
Late coming (e.g., NAD 500 per-occurrence)
Early departure without approval (e.g.,NAD 50 per-occurrence after)
Early departure without approval (e.g.,NAD 100 per occurrence)
Uniform violation (e.g., NAD200peroccurrence)
Sleeping on duty (e.g., NAD200per-occurrence)
Sleeping on duty (e.g., NAD500 per occurrence)
Using phone on post (e.g., NAD100peroccurrence)
Absent without notice (e.g., 1 day's pay deduction)



P14
Allow supervisor to log a behavioral incident against an employee with: Incident date, Incident type, Amount to deduct, Supporting notes/evidence, Approval by manager.
P15
Once an incident is approved, the system automatically: (a) Adds deduction line to next payroll run for that employee, (b) Reduces employee's Reliability Score (used in roster auto-assignment), (c) Sends email notification to employee.
P16
If an employee accumulates 3 behavioral deductions in 30 days, system automatically flags them for supervisor review and temporarily excludes them from high-trust posts (e.g., Cash-in-Transit, Control Room).
P17
Generate a behavioral deduction report monthly showing per employee: Number of incidents, Total deducted amount (NAD), Impact on Reliability Score.

4.5 Security Allowances
#
Functional Requirement
P18
Include these security-specific allowances as line items (in NAD): Uniform allowance, Firearm retention allowance, Travel to remote post allowance, Standby/On-call allowance.

4.6 Payroll Data Integration
#
Functional Requirement
P19
Automatically import attendance data into payroll work entries for the pay period, including: Total attendance hours, Valid attendance hours (matching schedule), Late coming hours, Early leave hours, Number of missing check-outs, Sunday hours worked, Public Holiday hours worked.
P20
Automatically import leave data into payroll, including: Annual leave taken (paid), Sick leave taken (paid), Unpaid leave taken (deduction), Leave balance remaining.
P21
Automatically import loan data into payroll: Active loan installment amounts.
P22
Automatically import behavioral data into payroll: Approved incident deductions for the period.

4.7 Payslip Output
#
Functional Requirement
P23
Generate a payslip PDF in NAD showing:
• Basic pay
• Sunday hours worked × 1.5 rate (separate line)
• Public Holiday hours worked × 1.5 rate (separate line)
• Other overtime breakdown (hours × rate)
• Allowances (each listed separately)
• Attendance summary (12-hour shifts worked, late occurrences, early departures)
• Leave summary (days taken this period, balance remaining)
• Loan deductions (each loan listed separately with remaining balance)
• Behavioral deductions (each incident listed with description and amount)
• Total deductions (PAYE + SSC + loans + behavioral)
• Net pay (NAD)


 

4.8 Compliance Reports
#
Functional Requirement
P25
Generate a monthly SSC submission report in format acceptable to Namibian Social Security Commission.
P26
Generate a monthly PAYE summary for Namibia tax authority filing.

5. INVOICE TEMPLATE 
#
Functional Requirement
INV1
The system must have a custom invoice template that complies with Namibian tax and business standards.
INV2
The invoice must display the following mandatory Namibian fields:
• Supplier Information: Company name, Physical address (Namibia), VAT registration number (if applicable), Tax Compliance Certificate number (if applicable)
• Customer Information: Client name, Physical address, Client VAT number (if applicable)
• Invoice Details: Invoice number (sequential), Invoice date, Due date, Purchase Order number (if applicable)
• Service Details: Description of security services provided, Dates of service (start to end), Number of guards deployed, Shift details (12-hour shifts), Rate per guard per shift (NAD)
• Financial Breakdown: Subtotal per service line, VAT amount (if applicable — 15% standard rate in Namibia), Total amount due (NAD)
• Banking Details: Bank name, Account name, Account number, Branch code, SWIFT/BIC code (for international clients)
• Legal Text: "This invoice must be paid within 30 days of invoice date. Late payments may incur interest at the prescribed rate under the Namibian Labour Act."
INV3
The invoice must include a VAT breakdown section showing: VAT rate applied (15% for standard supplies, 0% for exempt supplies, or no VAT for non-VAT registered entities), VAT amount per line, Total VAT amount, Reason for zero-rating if applicable (e.g., exported services).
INV4
The invoice must include an "Amount in Words" field showing the total due in words (e.g., "Five Thousand Namibian Dollars Only"). This is standard practice for Namibian invoices.
INV5
The invoice template must be brandable — the company logo, company colors, and footer text must be configurable without modifying code.
INV6
Invoices must be generated automatically from:
• Client contracts (monthly recurring billing)
• Ad-hoc services (manual creation)
• Timesheet/attendance data (per shift billing)
INV7
The system must support electronic invoice delivery — PDF invoices auto-attached to email and sent to client's billing contact.
INV8
The invoice template must be printable on A4 paper with proper margins for Namibian postal requirements.

6. BANKING & RECONCILIATION SYSTEM
6.1 Bank Integration Setup
#
Functional Requirement
B1
The system must allow configuration of multiple bank accounts (e.g., Operations Account, Payroll Account, Client Deposits Account).
B2
Each bank account must have a Bank Journal in Odoo with the following configured: Bank name, Account number, Branch code, SWIFT code, Suspense account (for imported transactions). 
B3
The system must support bank statement import via: CSV file upload, OFX/QIF file upload, Manual entry (for cash payments or non-electronic banks). 



6.2 Payment Processing
#
Functional Requirement
B4
When the accounting department receives payment from a client (via EFT, cash, or cheque), a user with "Accounting" role must be able to:
Locate the outstanding invoice
Click "Register Payment" on the invoice
Enter payment amount, date, payment method, and reference number (EFT transaction ID or cheque number)
 Click "Validate" — the system marks invoice as "Paid" and creates corresponding journal entries. 
B5
When a payment is registered against an invoice, the system must automatically create a draft bank statement line in the Outstanding Receipts account (or automatically reconcile if statement has been imported). 

6.3 Bank Reconciliation Process
#
Functional Requirement
B6
The system must support a two-step reconciliation process:
Step 1 — Import Bank Statement:
- Accounting staff imports bank statement (CSV/OFX/manual entry)
- System posts all transactions to a Suspense Account 
- Each transaction appears in the "Transactions" column on the reconciliation screen

Step 2 — Reconcile:
- Staff clicks "Reconcile # Items" on the Bank Journal dashboard 
- System automatically matches transactions to existing invoices/payments based on: 
Customer name,
Amount,
Reference number 
- Staff manually matches any unmatched transactions
- Staff clicks "Validate" to complete reconciliation 
B7
The reconciliation screen must display:
• Left panel (Transactions): Bank statement lines awaiting reconciliation — each showing 
date,
description,
debit/credit amount (NAD)
• Right panel (Counterparts): Matching invoices, payments, or journal entries available to match against 
B8
For partial payments (client pays less than invoice amount due to dispute or deduction), the system must:
Allow reconciliation of the partial amount against the invoice
 Leave the remaining balance as outstanding
Allow a write-off for small discrepancies (e.g., bank fees)
 Flag the invoice for follow-up if the remaining balance exceeds configurable threshold 
B9
For overpayments (client pays more than invoice amount), the system must:
1. Reconcile the payment against the invoice
2. Leave the excess amount as a customer credit note
3. Allow the credit to be applied to future invoices
4. Generate a refund if requested 

6.4 Roles & Permissions
#
Functional Requirement
B10
The "Accountant" role must have full access to: Register payments, Import bank statements, Reconcile transactions, Generate financial reports.
B11
The "Accounting Manager" role must have the same access as Accountant, plus: Review and approve write-offs, Reconcile Suspense Account balances, Access audit logs of all reconciliation actions.
B12
The "Accounting Clerk (View Only)" role must be able to: View invoices, View payment status, View reconciled transactions, But NOT register payments, reconcile, or modify any data.
B13
All reconciliation actions must be logged with: User who performed action, Timestamp, Transaction IDs before/after change, Any override reasons.

6.5 Financial Reports
#
Functional Requirement
B14
The system must generate a Bank Reconciliation Report showing: Starting balance, Total deposits reconciled, Total payments reconciled, Ending balance, Any unreconciled transactions (with aging — 30, 60, 90+ days).
B15
The system must generate an Aged Receivables Report showing per client: Outstanding invoices, Due date, Days overdue, Total amount (NAD).
B16
The system must generate a Daily Cash Position Report showing: Opening bank balance (NAD), Total payments received today, Total payments made today, Closing balance (NAD).
B17
All reports must be exportable to Excel and PDF.

6.6 Security Considerations
#
Functional Requirement
B18
The system must enforce two-factor authentication (2FA) for all users with Accounting roles accessing banking and reconciliation functions.
B19
Changes to bank account details (account number, branch code) must require manager approval before being updated in the system.
B20
The system must log all exported reports (who exported, when, what data range) for audit trail purposes.



7. DATA FLOW DIAGRAM — INVOICE TO RECONCILIATION
CLIENT CONTRACT / SERVICE DELIVERY
         │
         ▼
    INVOICE GENERATED
    (Namibian Standard Template)
         │
         ▼
    INVOICE SENT TO CLIENT
         │
         ▼
CLIENT MAKES PAYMENT (EFT/Cash/Cheque)
         │
         ▼
ACCOUNTING DEPARTMENT:
"Register Payment" on Invoice
         │
         ├─────────────────────────────────────┐
         │                                     │
         ▼                                     ▼
  INVOICE MARKED "PAID"                PAYMENT RECORDED IN
  (Outstanding Receipts)               BANK JOURNAL
                                              │
                                              ▼
                                    BANK STATEMENT IMPORTED
                                    (CSV/OFX/Manual)
                                              │
                                              ▼
                                    RECONCILIATION SCREEN
                                    (Match Payments to Bank)
                                              │
                                              ▼
                                    CLICK "VALIDATE"
                                              │
                                              ▼
                                    TRANSACTION RECONCILED
                                    (Outstanding cleared to Bank)
                                              │
                                              ▼
                                    BANK RECONCILIATION REPORT
                                    (For audit & month-end)


8. DELIVERABLES CHECKLIST
Category
Deliverable
Status
SYSTEM CONFIG
NAD as default currency
☐


12-hour shift configuration
☐


Namibian public holidays pre-loaded
☐
ROSTER
Auto-generate from guard characteristics (grade, certs, reliability)
☐


Grade/cert matching rules
☐


Supervisor override with audit log
☐
ATTENDANCE
Scheduled vs actual time
☐


Late/early/absent detection (12-hour shift basis)
☐
LEAVE
Accrual based on actual attendance hours
☐


Deduct leave on approval
☐


Unapproved absence deducts leave
☐
PAYROLL
Sunday work @ 1.5× automatic
☐


Public Holiday work @ 1.5× automatic
☐


Shift splitting across midnight/holiday
☐


Loan deductions per payroll
☐


Behavioral deductions per payroll
☐


PAYE (Namibian brackets)
☐


SSC (0.9%/0.9% capped at N$7,100)
☐
PAYSLIP
Shows Sunday/Public Holiday premium lines
☐


Shows loan deductions (per loan)
☐


Shows behavioral deductions (per incident)
☐


Shows attendance/leave summary
☐
INVOICING
Namibian standard invoice template
☐


VAT breakdown (15%)
☐


Amount in words (NAD)
☐


Brandable logo/colors
☐


Auto-invoice from contracts/timesheets
☐
BANKING
Bank journals configured
☐


Bank statement import (CSV/OFX)
☐


"Register Payment" on invoice
☐


Reconcile payments to bank statements
☐


Partial/overpayment handling
☐


Write-off for small discrepancies
☐
PERMISSIONS
Accountant role (full access)
☐


Accounting Manager role (with approval)
☐


Clerk role (view only)
☐


Audit logging for all actions
☐
REPORTS
Monthly SSC submission report
☐


Behavioral deduction report
☐


Loan summary report
☐


Bank reconciliation report
☐


Aged receivables report
☐


Daily cash position report
☐
ALERTS
Daily understaffing alert
☐


Leave balance low alert
☐


Unpaid overdue invoice alert
☐

9. ACCEPTANCE CRITERIA
The customization is complete and acceptable when:
#
Criteria
1
Roster: A new contract for a site requiring "Grade B1 + Firearm Certified" automatically selects only guards matching those criteria and schedules them in 12-hour shifts.
2
Sunday/Holiday Pay: A guard working a 12-hour shift on a Sunday gets paid 18 hours equivalent (12 × 1.5) automatically.
3
Loan Deduction: An employee with a NAD5,00 loan over 1months has (N5,000loanover5monthshasN1,000 deducted automatically each payroll).
4
Behavioral Deduction: A supervisor logs "Sleeping on duty - N$500" against a guard, and the next pays lip shows that deduction.
5
Invoice: A generated invoice includes all Namibian mandatory fields, VAT at 15%, amount in words (NAD), and can be printed on A4.
6
Payment: An accountant can locate an invoice, click "Register Payment," enter client EFT details, and mark the invoice as paid.
7
Reconciliation: After importing a bank statement showing that payment, the system suggests the match, the accountant clicks "Validate," and the transaction is reconciled.
8
Reporting: A bank reconciliation report is generated showing starting balance, reconciled deposits, reconciled payments, ending balance.
9
Integration: A test payroll run pulls attendance (including Sunday hours), leave, loans, and behavioral deductions — no manual entry required.
10
Compliance: A test payroll run matches manual calculation using Namibian tax tables to within N$0.01.

 
