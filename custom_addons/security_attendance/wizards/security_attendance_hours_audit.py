from odoo import api, fields, models

# How far a guard's hours can sit from the team average before the audit
# calls it out. 20% is a starting point, not a policy -- HR can watch the
# report for a while and this can move once there is a real number to
# anchor it to. Documented here rather than buried in a domain string.
OUTLIER_BAND = 0.20


class SecurityAttendanceHoursAudit(models.TransientModel):
    """HR hours audit: who worked how many hours in a period, and how far
    that sits from the team average.

    docs/ROSTERING_SIMPLIFICATION_PLAN.md §3/A7b: "HR hours audit — sharing
    of hours and balancing, equity." This does not decide anything or change
    a roster; it is a read-only lens onto security.attendance.record so HR
    can see who is being over- or under-rostered before it becomes a
    grievance.
    """

    _name = "security.attendance.hours.audit"
    _description = "HR Hours Equity Audit"

    date_from = fields.Date(
        required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    date_to = fields.Date(required=True, default=fields.Date.today)
    site_id = fields.Many2one(
        "security.client.site",
        string="Site (optional)",
        help="Leave empty to audit hours across all sites.",
    )
    line_ids = fields.One2many(
        "security.attendance.hours.audit.line", "audit_id", string="Lines"
    )
    average_payable_hours = fields.Float(readonly=True)
    over_count = fields.Integer(readonly=True, string="Over the band")
    under_count = fields.Integer(readonly=True, string="Under the band")

    def action_run(self):
        self.ensure_one()
        self.line_ids.unlink()

        domain = [
            ("shift_date", ">=", self.date_from),
            ("shift_date", "<=", self.date_to),
            ("employee_id", "!=", False),
        ]
        if self.site_id:
            domain.append(("site_id", "=", self.site_id.id))

        Record = self.env["security.attendance.record"]
        grouped = Record._read_group(
            domain, groupby=["employee_id"], aggregates=["payable_hours:sum"]
        )
        rows = [(employee, hours or 0.0) for employee, hours in grouped]

        if not rows:
            self.average_payable_hours = 0.0
            self.over_count = 0
            self.under_count = 0
            return self._reopen()

        total = sum(hours for _employee, hours in rows)
        average = total / len(rows)
        lower = average * (1 - OUTLIER_BAND)
        upper = average * (1 + OUTLIER_BAND)

        over = under = 0
        Line = self.env["security.attendance.hours.audit.line"]
        for employee, hours in rows:
            if hours > upper:
                flag = "over"
                over += 1
            elif hours < lower:
                flag = "under"
                under += 1
            else:
                flag = "normal"
            variance_pct = ((hours - average) / average * 100) if average else 0.0
            Line.create({
                "audit_id": self.id,
                "employee_id": employee.id,
                "payable_hours": hours,
                "variance_pct": variance_pct,
                "flag": flag,
            })

        self.average_payable_hours = average
        self.over_count = over
        self.under_count = under
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.attendance.hours.audit",
            "res_id": self.id,
            "views": [[False, "form"]],
            "target": "new",
        }


class SecurityAttendanceHoursAuditLine(models.TransientModel):
    _name = "security.attendance.hours.audit.line"
    _description = "HR Hours Equity Audit Line"
    _order = "payable_hours desc"

    audit_id = fields.Many2one(
        "security.attendance.hours.audit", required=True, ondelete="cascade"
    )
    employee_id = fields.Many2one("hr.employee", required=True)
    payable_hours = fields.Float()
    variance_pct = fields.Float(string="Variance vs. average (%)")
    flag = fields.Selection(
        [
            ("over", "Over the band"),
            ("under", "Under the band"),
            ("normal", "Within band"),
        ],
        required=True,
    )
