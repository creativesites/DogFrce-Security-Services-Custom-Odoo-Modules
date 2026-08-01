# -*- coding: utf-8 -*-
"""
DeployGuard Operational Damage Audit Script
Usage:
    docker exec -i dogforce-demo-odoo-1 odoo shell -d dogforce-demo --no-http --workers=0 < scripts/damage_audit.py
"""

print("\n" + "="*80)
print("DEPLOYGUARD OPERATIONAL DAMAGE AUDIT".center(80))
print("="*80)

# ==============================================================================
# AUDIT 1: Leave Balance Destruction Audit
# ==============================================================================
print("\n[1] AUDITING LEAVE BALANCES FOR HISTORICAL RESTORATION FAILURE...")
print("-" * 80)

# We want to find leave requests that are in draft or refused state
# but historically transitioned from 'approved' (meaning their days were decremented but never returned)
refused_draft_leaves = env['security.leave.request'].search([
    ('state', 'in', ('refused', 'draft'))
])

damaged_leaves_found = []
for leave in refused_draft_leaves:
    # Query mail.message for tracking changes of this leave request record
    messages = env['mail.message'].search([
        ('model', '=', 'security.leave.request'),
        ('res_id', '=', leave.id)
    ])
    
    was_approved = False
    for msg in messages:
        # Check tracking value logs for state changing from approved ('Approved')
        if msg.tracking_value_ids:
            for track in msg.tracking_value_ids:
                if track.field_id.name == 'state' and track.old_value_char == 'Approved':
                    was_approved = True
                    break
        # Also check fallback text if tracking details are summarized in text
        if 'approved' in (msg.body or '').lower() and ('refuse' in (msg.body or '').lower() or 'draft' in (msg.body or '').lower()):
            was_approved = True
            
        if was_approved:
            break
            
    if was_approved:
        damaged_leaves_found.append(leave)

if damaged_leaves_found:
    print(f"{'Guard Name':<30} | {'Leave Dates':<25} | {'Days lost':<10} | {'Current State':<10}")
    print("-" * 80)
    total_lost_days = 0.0
    for leave in damaged_leaves_found:
        dates_str = f"{leave.date_from} to {leave.date_to}"
        print(f"{leave.employee_id.name:<30} | {dates_str:<25} | {leave.requested_days:<10.1f} | {leave.state:<10}")
        total_lost_days += leave.requested_days
    print("-" * 80)
    print(f"TOTAL LOST LEAVE DAYS ACROSS ALL GUARDS: {total_lost_days:.1f}")
else:
    print("NO LEAVE BALANCE DESTRUCTION DETECTED (0 damaged leave records).")


# ==============================================================================
# AUDIT 2: Inflated Customer Debt Audit
# ==============================================================================
print("\n[2] AUDITING CUSTOMER DEBT FOR PARTIALLY-PAID INFLATED OUTSTANDING TOTALS...")
print("-" * 80)

# Find all billing invoices that are unpaid or partially paid
unpaid_invoices = env['security.billing.invoice'].search([
    ('state', 'not in', ('paid', 'cancelled'))
])

partially_paid_invoices = []
for inv in unpaid_invoices:
    # If the invoice has posted payments and the balance is less than total
    posted_payments = inv.payment_ids.filtered(lambda p: p.state == 'posted')
    if posted_payments:
        partially_paid_invoices.append((inv, posted_payments))

if partially_paid_invoices:
    print(f"{'Customer / Client Name':<28} | {'Invoice Ref':<15} | {'Gross Total':<11} | {'Actual Debt':<11} | {'Discrepancy':<11}")
    print("-" * 80)
    total_discrepancy = 0.0
    for inv, payments in partially_paid_invoices:
        gross = inv.total_amount
        actual = inv.balance_amount
        discrepancy = gross - actual
        total_discrepancy += discrepancy
        print(f"{inv.partner_id.name[:28]:<28} | {inv.name:<15} | {gross:<11.2f} | {actual:<11.2f} | {discrepancy:<11.2f}")
    print("-" * 80)
    print(f"TOTAL INFLATED OVER-REPORTED CUSTOMER DEBT: {total_discrepancy:.2f} NAD")
else:
    print("NO DEBT DISCREPANCIES DETECTED (0 partially paid invoices with inflated outstanding reports).")

print("="*80)
print("AUDIT COMPLETE".center(80))
print("="*80 + "\n")
