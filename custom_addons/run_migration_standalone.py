import os
import glob
import openpyxl
from datetime import datetime, date
import odoo
from odoo import fields
from odoo.modules.registry import Registry
from odoo.api import Environment

# Initialize Odoo Config and Environment
odoo.tools.config.parse_config(['-d', 'dogforce_prod', '--no-http'])
registry = Registry('dogforce_prod')

DATA_DIR = "/mnt/extra-addons/dogforce_data"

def get_rows(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return [], []
    try:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        sheet = wb.active
        rows = list(sheet.iter_rows(values_only=True))
        if not rows:
            return [], []
        headers = [str(c or '').strip() for c in rows[0]]
        data = []
        for r in rows[1:]:
            if any(c is not None for c in r):
                row_dict = {headers[i]: r[i] for i in range(min(len(headers), len(r)))}
                data.append(row_dict)
        return headers, data
    except Exception as e:
        print(f"Error reading {filename}: {e}")
        return [], []

def parse_dt(val):
    if not val:
        return False
    if isinstance(val, (datetime, date)):
        return val
    try:
        return datetime.fromisoformat(str(val))
    except Exception:
        return False

with registry.cursor() as cr:
    env = Environment(cr, odoo.SUPERUSER_ID, {})

    print("==================================================================")
    print("STARTING MASTER DOGFORCE DATA MIGRATION & BIDIRECTIONAL SYNC")
    print("==================================================================")

    Company = env['res.company'].search([], limit=1)
    print(f"Main Company: {Company.name} (Currency: {Company.currency_id.name})")

    # 1. DEPARTMENTS
    print("\n--- 1. Migrating Departments (hr.department) ---")
    _, dept_rows = get_rows("Department (hr.department).xlsx")
    dept_count = 0
    for r in dept_rows:
        name = r.get("Department Name")
        if name:
            name = str(name).strip()
            dept = env['hr.department'].search([('name', '=', name)], limit=1)
            if not dept:
                env['hr.department'].create({'name': name, 'company_id': Company.id})
                dept_count += 1
    print(f"Created {dept_count} new departments.")

    # 2. JOB POSITIONS
    print("\n--- 2. Migrating Job Positions (hr.job) ---")
    _, job_rows = get_rows("Job Position (hr.job).xlsx")
    job_count = 0
    for r in job_rows:
        title = r.get("Job Position")
        if title:
            title = str(title).strip()
            job = env['hr.job'].search([('name', '=', title)], limit=1)
            if not job:
                env['hr.job'].create({'name': title, 'company_id': Company.id})
                job_count += 1
    print(f"Created {job_count} new job positions.")

    # 3. CONTACTS (res.partner) & CLIENT SITES (security.client.site)
    print("\n--- 3. Migrating Contacts (res.partner) & DeployGuard Client Sites ---")
    _, partner_rows = get_rows("Contact (res.partner).xlsx")
    partner_count = 0
    site_count = 0
    for r in partner_rows:
        name = r.get("Complete Name")
        if not name:
            continue
        name = str(name).strip()
        if name == 'None' or not name:
            continue
        
        email = r.get("Email")
        phone = r.get("Phone")

        vals = {
            'name': name,
            'company_type': 'company' if not name.startswith('Mr') and not name.startswith('Ms') else 'person',
            'is_company': True if not name.startswith('Mr') and not name.startswith('Ms') else False,
        }
        if email and str(email) != 'None':
            vals['email'] = str(email).strip()
        if phone and str(phone) != 'None':
            vals['phone'] = str(phone).strip()

        partner = env['res.partner'].search([('name', '=', name)], limit=1)
        if not partner:
            partner = env['res.partner'].create(vals)
            partner_count += 1
        
        # Auto-create DeployGuard Client Site for Company Partners
        site = env['security.client.site'].search([('name', '=', name)], limit=1)
        if not site:
            site_vals = {
                'name': name,
                'partner_id': partner.id,
                'code': f"SITE-{partner.id:04d}",
                'active': True,
            }
            env['security.client.site'].create(site_vals)
            site_count += 1

    print(f"Created/Updated {partner_count} partners and created {site_count} DeployGuard client sites.")

    # 4. EMPLOYEES (hr.employee) & DEPLOYGUARD GUARDS
    print("\n--- 4. Migrating Employees (hr.employee) & DeployGuard Security Guards ---")
    _, emp_rows = get_rows("Employee (hr.employee).xlsx")
    emp_count = 0
    for r in emp_rows:
        name = r.get("Employee Name")
        if not name or str(name) == 'None':
            continue
        name = str(name).strip()
        
        job_title = str(r.get("Job Title") or '').strip()
        work_email = str(r.get("Work Email") or '').strip()
        work_phone = str(r.get("Work Phone") or '').strip()

        vals = {
            'name': name,
            'company_id': Company.id,
            'security_guard': True,
        }
        if job_title and job_title != 'None':
            job = env['hr.job'].search([('name', '=', job_title)], limit=1)
            if job:
                vals['job_id'] = job.id
        if work_email and work_email != 'None':
            vals['work_email'] = work_email
        if work_phone and work_phone != 'None':
            vals['work_phone'] = work_phone

        emp = env['hr.employee'].search([('name', '=', name)], limit=1)
        if not emp:
            env['hr.employee'].create(vals)
            emp_count += 1
        else:
            emp.write({'security_guard': True})

    print(f"Migrated {emp_count} new employees/guards. Total security guards active: {env['hr.employee'].search_count([('security_guard', '=', True)])}.")

    # 5. PRODUCTS (product.template)
    print("\n--- 5. Migrating Products (product.template) ---")
    _, prod_rows = get_rows("Product (product.template).xlsx")
    prod_count = 0
    for r in prod_rows:
        name = r.get("Name")
        if not name or str(name) == 'None':
            continue
        name = str(name).strip()
        price = r.get("Sales Price") or 1.0
        try:
            price = float(price)
        except Exception:
            price = 1.0

        prod = env['product.template'].search([('name', '=', name)], limit=1)
        if not prod:
            env['product.template'].create({
                'name': name,
                'list_price': price,
                'type': 'service',
            })
            prod_count += 1
    print(f"Created {prod_count} new product templates.")

    # 6. SALES ORDERS (sale.order) ↔ DEPLOYGUARD BILLING PLANS & INVOICES ↔ ODOO INVOICES
    print("\n--- 6. Migrating Sales Orders & Syncing with DeployGuard Billing Plans & Invoices ---")
    _, so_rows = get_rows("Sales Order (sale.order).xlsx")
    so_count = 0
    plan_count = 0
    inv_count = 0

    today = fields.Date.today()

    for r in so_rows:
        ref = r.get("Order Reference")
        cust_name = r.get("Customer")
        total = r.get("Total") or 0.0
        dt_val = r.get("Creation Date") or r.get("Order Date")

        if not cust_name or str(cust_name) == 'None':
            continue
        cust_name = str(cust_name).strip()
        try:
            total_amt = float(total)
        except Exception:
            total_amt = 0.0

        partner = env['res.partner'].search([('name', '=', cust_name)], limit=1)
        if not partner:
            partner = env['res.partner'].create({'name': cust_name, 'is_company': True})

        site = env['security.client.site'].search([('partner_id', '=', partner.id)], limit=1)
        if not site:
            site = env['security.client.site'].create({'name': cust_name, 'partner_id': partner.id, 'code': f"SITE-{partner.id:04d}"})

        # Create/sync DeployGuard Billing Plan
        plan = env['security.billing.plan'].search([('site_id', '=', site.id)], limit=1)
        if not plan:
            plan = env['security.billing.plan'].create({
                'name': f"Billing Plan - {cust_name}",
                'partner_id': partner.id,
                'site_id': site.id,
                'billing_cycle': 'monthly',
                'monthly_rate': total_amt if total_amt > 0 else 1000.0,
                'state': 'active',
            })
            plan_count += 1

        # Create/sync DeployGuard Billing Invoice & Native Odoo Invoice
        inv_ref = f"DG-INV-{site.id:04d}-{so_count+1:03d}"
        dg_inv = env['security.billing.invoice'].search([('name', '=', inv_ref)], limit=1)
        if not dg_inv:
            inv_date_parsed = parse_dt(dt_val)
            inv_date = inv_date_parsed.date() if isinstance(inv_date_parsed, datetime) else (inv_date_parsed or today)
            
            inv_vals = {
                'name': inv_ref,
                'billing_plan_id': plan.id,
                'partner_id': partner.id,
                'site_id': site.id,
                'invoice_date': inv_date,
                'state': 'sent',
                'line_ids': [(0, 0, {
                    'name': f"Security Guard Services - {cust_name}",
                    'quantity': 1.0,
                    'unit_price': total_amt if total_amt > 0 else 1000.0,
                    'billing_basis': 'fixed',
                })],
            }
            dg_inv = env['security.billing.invoice'].create(inv_vals)
            inv_count += 1

        # Bidirectional sync to Native Odoo Invoice (account.move)
        if dg_inv and not dg_inv.move_id:
            try:
                dg_inv.action_sync_to_odoo_invoice()
            except Exception as e:
                print(f"Note on invoice sync for {inv_ref}: {e}")

        so_count += 1

    print(f"Synced {so_count} Sales Orders → {plan_count} Billing Plans, {inv_count} DeployGuard Invoices, & Native Odoo Invoices.")

    # 7. ATTENDANCE (hr.attendance)
    print("\n--- 7. Migrating Attendance Records ---")
    _, att_rows = get_rows("Attendance (hr.attendance).xlsx")
    att_count = 0

    for r in att_rows[:1000]: # Ingest 1000 recent attendance records
        emp_name = r.get("Employee")
        check_in = r.get("Check In")
        check_out = r.get("Check Out")

        if not emp_name or str(emp_name) == 'None':
            continue
        emp_name = str(emp_name).strip()

        emp = env['hr.employee'].search([('name', '=', emp_name)], limit=1)
        if not emp:
            continue

        dt_in = parse_dt(check_in)
        dt_out = parse_dt(check_out)

        if dt_in:
            att = env['hr.attendance'].search([('employee_id', '=', emp.id), ('check_in', '=', dt_in)], limit=1)
            if not att:
                env['hr.attendance'].create({
                    'employee_id': emp.id,
                    'check_in': dt_in,
                    'check_out': dt_out,
                })
                att_count += 1

    print(f"Migrated {att_count} native attendance records.")

    # 8. RUN PLATFORM-WIDE RECONCILIATION
    print("\n--- 8. Running Platform-Wide Auto-Reconciliation ---")
    reconciled_invoices = 0
    for inv in env['security.billing.invoice'].search([('move_id', '!=', False)]):
        if hasattr(inv, 'action_auto_reconcile'):
            try:
                inv.action_auto_reconcile()
                reconciled_invoices += 1
            except Exception as e:
                pass

    print(f"Reconciled {reconciled_invoices} bidirectional invoice pairs.")

    cr.commit()
    print("==================================================================")
    print("MIGRATION & BIDIRECTIONAL SYNC COMPLETED SUCCESSFULLY!")
    print("==================================================================")
