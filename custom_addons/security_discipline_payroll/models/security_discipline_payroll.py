import logging
from datetime import date, timedelta
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SecurityPayslip(models.Model):
    _inherit = "security.payslip"

    def action_compute_from_sources(self):
        """
        Extends default payslip computation to search for AWOLs/unexcused absences during
        the payroll period and append dynamic penalty deductions to the slips.
        """
        super().action_compute_from_sources()

        for payslip in self:
            if not payslip.employee_id or not payslip.period_id:
                continue

            # Query unexcused absences/AWOLs inside the period
            attendance_records = self.env["security.attendance.record"].search([
                ("employee_id", "=", payslip.employee_id.id),
                ("shift_date", ">=", payslip.period_id.date_from),
                ("shift_date", "<=", payslip.period_id.date_to),
                ("manual_presence", "in", ["absent", "awol"]),
            ])

            if not attendance_records:
                continue

            awol_count = len(attendance_records)
            rate = payslip.hourly_rate or 15.0  # fallback rate
            # Standard penalty: 12.0 hours (1 shift) worth of base wage per unexcused absence
            penalty_hours = awol_count * 12.0
            penalty_amount = penalty_hours * rate

            # Create penalty deduction line
            self.env["security.payslip.deduction.line"].create({
                "payslip_id": payslip.id,
                "name": _("Unexcused Absence Penalty (%s Shifts Missed)") % awol_count,
                "code": "AWOL_PENALTY",
                "quantity": penalty_hours,
                "rate": rate,
                "amount": penalty_amount,
            })

            # Force re-evaluation of net pay totals after appending deductions
            payslip._compute_totals()


class SecurityDisciplinePayrollBridge(models.AbstractModel):
    _name = "security.discipline.payroll.bridge"
    _description = "Security Attendance to Discipline & Payroll Event Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """
        Listens to attendance exceptions and adjusts reliability index,
        deducts safety scores, and triggers automated progressive discipline.
        """
        _logger.info("Discipline/Payroll Bridge | Processing event: %s", event_name)

        if event_name == "attendance.missed" and source_model == "security.attendance.record":
            record = self.env["security.attendance.record"].browse(source_id)
            if not record.exists() or not record.employee_id:
                return

            employee = record.employee_id

            # 1. Update reliability index (AWOL / Absence = -5 points)
            old_score = employee.security_reliability_score
            new_score = max(0, old_score - 5)
            employee.write({"security_reliability_score": new_score})
            _logger.info("Discipline Bridge | Deducted 5 points from Employee %s reliability (New: %s)", employee.name, new_score)

            # 2. Sequential Consecutive AWOL check (3 missed shifts in a row)
            self._check_consecutive_absences(employee, record)

        elif event_name == "attendance.late" and source_model == "security.attendance.record":
            record = self.env["security.attendance.record"].browse(source_id)
            if not record.exists() or not record.employee_id:
                return

            employee = record.employee_id

            # Update reliability index (Late clock-in = -2 points)
            old_score = employee.security_reliability_score
            new_score = max(0, old_score - 2)
            employee.write({"security_reliability_score": new_score})
            _logger.info("Discipline Bridge | Deducted 2 points from Employee %s for late arrival (New: %s)", employee.name, new_score)

    def _check_consecutive_absences(self, employee, current_record):
        """Checks if employee has 3 consecutive missed shifts and issues formal warnings."""
        # Find last 3 shifts of this employee
        recent_records = self.env["security.attendance.record"].search([
            ("employee_id", "=", employee.id),
            ("shift_date", "<=", current_record.shift_date),
        ], order="shift_date desc", limit=3)

        if len(recent_records) < 3:
            return

        # Check if ALL 3 are unexcused/AWOL
        consecutive_missed = all(r.manual_presence in ["absent", "awol"] for r in recent_records)
        if consecutive_missed:
            # Check if warning was already generated in the last 7 days
            duplicate_check = self.env["security.incident"].search_count([
                ("employee_id", "=", employee.id),
                ("incident_date", ">=", str(date.today() - timedelta(days=7))),
                ("note", "like", "Generated automatically for 3 consecutive unexcused absences"),
            ])
            if duplicate_check > 0:
                return

            # Lookup or create a proper consecutive AWOL incident type
            incident_type = self.env["security.incident.type"].search([
                ("name", "like", "Consecutive AWOL"),
            ], limit=1)
            if not incident_type:
                incident_type = self.env["security.incident.type"].create({
                    "name": "Consecutive AWOL / Missed Shifts",
                    "code": "CONSECUTIVE_AWOL",
                    "deduction_amount": 500.0,
                    "reliability_score_delta": 15,
                    "severity": "high",
                })

            # Create approved warning incident
            self.env["security.incident"].create({
                "employee_id": employee.id,
                "incident_type_id": incident_type.id,
                "incident_date": date.today(),
                "state": "approved",
                "note": _("System Alert: Generated automatically for 3 consecutive unexcused absences on the posting sheets."),
            })
            _logger.info("Discipline Bridge | Created high-severity disciplinary incident for Employee %s due to consecutive missed shifts", employee.name)
            # Recheck progressive discipline warning levels
            employee._check_progressive_discipline()
