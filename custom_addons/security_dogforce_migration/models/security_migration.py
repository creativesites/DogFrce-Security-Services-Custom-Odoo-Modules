import base64
import csv
import io
import re
from datetime import date, datetime

from odoo import api, fields, models
from odoo.exceptions import UserError


# ── helpers ──────────────────────────────────────────────────────────────────

def _parse_bank(raw):
    """Parse 'FNB-62104036133-SAV' → ('FNB', '62104036133').
    Handles spaces, branch suffixes, and account-type tags."""
    if not raw:
        return "", ""
    s = str(raw).strip()
    parts = s.split("-", 1)
    bank = parts[0].strip()
    if len(parts) < 2:
        return bank, ""
    rest = parts[1].strip()
    # Account number is the first segment; ignore anything after a second dash or space-alpha suffix
    acct_raw = rest.split("-")[0].strip()
    # Strip trailing non-digit branch codes (e.g. "8025388571 CHK" → "8025388571")
    acct = re.sub(r"\s+[A-Za-z]+$", "", acct_raw).replace(" ", "")
    return bank, acct


def _parse_date(raw):
    """Normalise dates from datetime objects or DD/MM/YYYY / YYYY-MM-DD strings → date."""
    if not raw:
        return None
    if isinstance(raw, (date, datetime)):
        return raw.date() if isinstance(raw, datetime) else raw
    s = str(raw).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _normalise_phone(raw):
    """Turn integer or string Namibian phone numbers into '0XXXXXXXX' strings."""
    if not raw:
        return ""
    s = str(raw).strip().replace(" ", "").replace("+264", "0").replace("264", "")
    if s and not s.startswith("0"):
        s = "0" + s
    return s


class SecurityMigrationJob(models.Model):
    _name = "security.migration.job"
    _description = "DogForce Data Migration Job"
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, string="Job Name")
    migration_type = fields.Selection(
        [
            ("employees", "Guards/Employees"),
            ("clients", "Clients & Sites"),
            ("leave_balances", "Leave Balances"),
            ("loans", "Loan Schedules"),
        ],
        string="Migration Type",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("running", "Running"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
        string="State",
    )
    csv_file = fields.Binary(string="CSV File", attachment=True)
    csv_filename = fields.Char(string="Filename")
    line_count = fields.Integer(string="Total Rows", compute="_compute_line_count", store=False)
    imported_count = fields.Integer(string="Imported", default=0)
    error_count = fields.Integer(string="Errors", default=0)
    log_text = fields.Text(string="Import Log", readonly=True)
    error_detail = fields.Text(string="Error Detail", readonly=True)

    @api.depends("imported_count", "error_count")
    def _compute_line_count(self):
        for job in self:
            job.line_count = job.imported_count + job.error_count

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------

    def action_run_import(self):
        self.ensure_one()
        if not self.csv_file:
            raise UserError("Please upload a CSV file before running the import.")
        self.write({"state": "running", "log_text": False, "error_detail": False,
                    "imported_count": 0, "error_count": 0})
        dispatch = {
            "employees": self._import_employees,
            "clients": self._import_clients,
            "leave_balances": self._import_leave_balances,
            "loans": self._import_loans,
        }
        handler = dispatch.get(self.migration_type)
        if not handler:
            raise UserError("Unknown migration type: %s" % self.migration_type)
        handler()

    def action_reset_to_draft(self):
        self.write({
            "state": "draft",
            "imported_count": 0,
            "error_count": 0,
            "log_text": False,
            "error_detail": False,
        })

    # ------------------------------------------------------------------
    # Helper: decode CSV bytes from binary field
    # ------------------------------------------------------------------

    def _get_csv_reader(self):
        """Decode base64 binary, strip BOM, return csv.DictReader."""
        raw = base64.b64decode(self.csv_file)
        # Strip UTF-8 BOM if present
        text = raw.decode("utf-8-sig").strip()
        return csv.DictReader(io.StringIO(text))

    # ------------------------------------------------------------------
    # Helper: find employee by name or work_email
    # ------------------------------------------------------------------

    def _find_employee(self, name_or_email):
        employee_model = self.env["hr.employee"]
        employee = employee_model.search(
            ["|", ("name", "=", name_or_email), ("work_email", "=", name_or_email)],
            limit=1,
        )
        if not employee:
            raise UserError("Employee not found: %s" % name_or_email)
        return employee

    # ------------------------------------------------------------------
    # Importer: Guards / Employees
    #
    # Required columns:
    #   name
    #
    # Optional columns (all formats accepted):
    #   employment_number   — DFSS-style ID, stored on security_employment_number
    #   work_email          — unique match key on re-imports
    #   mobile_phone        — accepts integers; Namibian prefix added automatically
    #   grade_code          — must match a security.grade code
    #   ssc_number          — SSC / NAPSA number
    #   tax_number          — PAYE / income tax number
    #   national_id         — national identity document number
    #   employment_date     — DD/MM/YYYY or YYYY-MM-DD; stored as date_start
    #   position            — job title string
    #   bank_name + bank_account_number  — explicit separate columns
    #   bank_raw            — combined e.g. "FNB-62104036133-SAV"; auto-parsed
    # ------------------------------------------------------------------

    def _import_employees(self):
        reader = self._get_csv_reader()
        logs = []
        errors = []
        imported = 0
        error_count = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                name = (row.get("name") or "").strip()
                if not name:
                    raise ValueError("Column 'name' is required and must not be empty.")

                employment_number = (row.get("employment_number") or "").strip()
                work_email = (row.get("work_email") or "").strip()
                mobile_phone = _normalise_phone(row.get("mobile_phone") or "")
                grade_code = (row.get("grade_code") or "").strip()
                ssc_number = (row.get("ssc_number") or "").strip()
                tax_number = (row.get("tax_number") or "").strip()
                national_id = (row.get("national_id") or "").strip()
                position = (row.get("position") or "").strip()

                # Employment date
                emp_date = _parse_date(row.get("employment_date") or "")

                # Bank: accept either pre-split or raw combined column
                bank_raw = (row.get("bank_raw") or "").strip()
                if bank_raw:
                    bank_name, bank_account_number = _parse_bank(bank_raw)
                else:
                    bank_name = (row.get("bank_name") or "").strip()
                    bank_account_number = (row.get("bank_account_number") or "").strip()

                vals = {"name": name, "security_guard": True}
                if employment_number:
                    vals["security_employment_number"] = employment_number
                if work_email:
                    vals["work_email"] = work_email
                if mobile_phone:
                    vals["mobile_phone"] = mobile_phone
                if ssc_number:
                    vals["security_ssc_number"] = ssc_number
                if tax_number:
                    vals["security_tax_number"] = tax_number
                if national_id:
                    vals["identification_id"] = national_id
                if position:
                    vals["job_title"] = position
                if emp_date:
                    vals["date_start"] = emp_date
                if bank_name:
                    vals["security_bank_name"] = bank_name
                if bank_account_number:
                    vals["security_bank_account_number"] = bank_account_number

                if grade_code:
                    grade = self.env["security.grade"].search(
                        [("code", "=", grade_code)], limit=1
                    )
                    if grade:
                        vals["security_grade_id"] = grade.id
                    else:
                        logs.append(
                            "Row %d: Grade code '%s' not found — skipped grade mapping."
                            % (row_num, grade_code)
                        )

                # Match priority: employment_number → work_email → name
                existing = False
                if employment_number:
                    existing = self.env["hr.employee"].search(
                        [("security_employment_number", "=", employment_number)], limit=1
                    )
                if not existing and work_email:
                    existing = self.env["hr.employee"].search(
                        [("work_email", "=", work_email)], limit=1
                    )
                if not existing:
                    existing = self.env["hr.employee"].search(
                        [("name", "=", name)], limit=1
                    )

                if existing:
                    existing.write(vals)
                    logs.append("Row %d: Updated '%s' (%s)." % (row_num, name, employment_number or "no emp#"))
                else:
                    self.env["hr.employee"].create(vals)
                    logs.append("Row %d: Created '%s' (%s)." % (row_num, name, employment_number or "no emp#"))

                imported += 1

            except Exception as exc:
                error_count += 1
                errors.append("Row %d: %s" % (row_num, str(exc)))

        self._finalise(imported, error_count, logs, errors)

    # ------------------------------------------------------------------
    # Importer: Clients & Sites
    # Expected columns: client_name, client_email, site_name, site_code,
    #                   site_location
    # ------------------------------------------------------------------

    def _import_clients(self):
        reader = self._get_csv_reader()
        logs = []
        errors = []
        imported = 0
        error_count = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                client_name = (row.get("client_name") or "").strip()
                if not client_name:
                    raise ValueError("Column 'client_name' is required and must not be empty.")

                client_email = (row.get("client_email") or "").strip()
                site_name = (row.get("site_name") or "").strip()
                site_code = (row.get("site_code") or "").strip()
                site_location = (row.get("site_location") or "").strip()

                # Create or find the res.partner (client company)
                partner = self.env["res.partner"].search(
                    [("name", "=", client_name), ("is_company", "=", True)], limit=1
                )
                if not partner:
                    partner_vals = {
                        "name": client_name,
                        "is_company": True,
                        "company_type": "company",
                    }
                    if client_email:
                        partner_vals["email"] = client_email
                    partner = self.env["res.partner"].create(partner_vals)
                    logs.append("Row %d: Created client partner '%s'." % (row_num, client_name))
                else:
                    logs.append("Row %d: Found existing client partner '%s'." % (row_num, client_name))

                # Create or find the security.client.site
                if site_name:
                    site_domain = [("name", "=", site_name), ("partner_id", "=", partner.id)]
                    site = self.env["security.client.site"].search(site_domain, limit=1)
                    if not site:
                        site_vals = {
                            "name": site_name,
                            "partner_id": partner.id,
                        }
                        if site_code:
                            site_vals["code"] = site_code
                        if site_location:
                            site_vals["location"] = site_location
                        self.env["security.client.site"].create(site_vals)
                        logs.append("Row %d: Created site '%s' for client '%s'." % (row_num, site_name, client_name))
                    else:
                        logs.append("Row %d: Site '%s' already exists — skipped." % (row_num, site_name))

                imported += 1

            except Exception as exc:
                error_count += 1
                errors.append("Row %d: %s" % (row_num, str(exc)))

        self._finalise(imported, error_count, logs, errors)

    # ------------------------------------------------------------------
    # Importer: Leave Balances
    # Expected columns: employee_name_or_email, leave_type_name,
    #                   balance_days, year
    # ------------------------------------------------------------------

    def _import_leave_balances(self):
        reader = self._get_csv_reader()
        logs = []
        errors = []
        imported = 0
        error_count = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                employee_ref = (row.get("employee_name_or_email") or "").strip()
                leave_type_name = (row.get("leave_type_name") or "").strip()
                balance_days_str = (row.get("balance_days") or "0").strip()
                year_str = (row.get("year") or "").strip()

                if not employee_ref:
                    raise ValueError("Column 'employee_name_or_email' is required.")
                if not leave_type_name:
                    raise ValueError("Column 'leave_type_name' is required.")

                employee = self._find_employee(employee_ref)

                leave_type = self.env["security.leave.type"].search(
                    [("name", "=", leave_type_name)], limit=1
                )
                if not leave_type:
                    raise UserError("Leave type not found: %s" % leave_type_name)

                try:
                    balance_days = float(balance_days_str)
                except ValueError:
                    raise ValueError("Invalid balance_days value: '%s'" % balance_days_str)

                # Create or update the leave balance record
                balance = self.env["security.leave.balance"].search(
                    [
                        ("employee_id", "=", employee.id),
                        ("leave_type_id", "=", leave_type.id),
                    ],
                    limit=1,
                )
                note_parts = []
                if year_str:
                    note_parts.append("Migrated for year: %s" % year_str)

                if balance:
                    balance.write({"balance_days": balance_days})
                    logs.append(
                        "Row %d: Updated leave balance for '%s' / '%s' → %.2f days."
                        % (row_num, employee.name, leave_type_name, balance_days)
                    )
                else:
                    create_vals = {
                        "employee_id": employee.id,
                        "leave_type_id": leave_type.id,
                        "balance_days": balance_days,
                    }
                    if note_parts:
                        create_vals["note"] = " | ".join(note_parts)
                    self.env["security.leave.balance"].create(create_vals)
                    logs.append(
                        "Row %d: Created leave balance for '%s' / '%s' → %.2f days."
                        % (row_num, employee.name, leave_type_name, balance_days)
                    )

                imported += 1

            except Exception as exc:
                error_count += 1
                errors.append("Row %d: %s" % (row_num, str(exc)))

        self._finalise(imported, error_count, logs, errors)

    # ------------------------------------------------------------------
    # Importer: Loan Schedules
    # Expected columns: employee_name_or_email, principal_amount,
    #                   repayment_months, start_date, note
    # ------------------------------------------------------------------

    def _import_loans(self):
        reader = self._get_csv_reader()
        logs = []
        errors = []
        imported = 0
        error_count = 0

        for row_num, row in enumerate(reader, start=2):
            try:
                employee_ref = (row.get("employee_name_or_email") or "").strip()
                principal_str = (row.get("principal_amount") or "0").strip()
                months_str = (row.get("repayment_months") or "1").strip()
                start_date_str = (row.get("start_date") or "").strip()
                note = (row.get("note") or "").strip()

                if not employee_ref:
                    raise ValueError("Column 'employee_name_or_email' is required.")
                if not start_date_str:
                    raise ValueError("Column 'start_date' is required.")

                employee = self._find_employee(employee_ref)

                try:
                    principal_amount = float(principal_str)
                except ValueError:
                    raise ValueError("Invalid principal_amount: '%s'" % principal_str)

                try:
                    repayment_months = int(months_str)
                except ValueError:
                    raise ValueError("Invalid repayment_months: '%s'" % months_str)

                # Parse start_date — accept YYYY-MM-DD format
                try:
                    parsed_date = date.fromisoformat(start_date_str)
                except ValueError:
                    raise ValueError(
                        "Invalid start_date format '%s'. Use YYYY-MM-DD." % start_date_str
                    )

                loan_vals = {
                    "employee_id": employee.id,
                    "principal_amount": principal_amount,
                    "repayment_months": repayment_months,
                    "start_date": fields.Date.to_string(parsed_date),
                    "currency_id": self.env.company.currency_id.id,
                }
                if note:
                    loan_vals["note"] = note

                self.env["security.employee.loan"].create(loan_vals)
                logs.append(
                    "Row %d: Created loan for '%s' — principal %.2f over %d months."
                    % (row_num, employee.name, principal_amount, repayment_months)
                )
                imported += 1

            except Exception as exc:
                error_count += 1
                errors.append("Row %d: %s" % (row_num, str(exc)))

        self._finalise(imported, error_count, logs, errors)

    # ------------------------------------------------------------------
    # Internal: finalise job state
    # ------------------------------------------------------------------

    def _finalise(self, imported, error_count, logs, errors):
        all_log_lines = logs + (["--- ERRORS ---"] + errors if errors else [])
        new_state = "done"
        if error_count > 0 and imported == 0:
            new_state = "error"

        self.write({
            "imported_count": imported,
            "error_count": error_count,
            "log_text": "\n".join(all_log_lines) if all_log_lines else False,
            "error_detail": "\n".join(errors) if errors else False,
            "state": new_state,
        })
