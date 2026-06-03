import base64
import csv
import io

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityClientServiceReport(models.Model):
    _name = "security.client.service.report"
    _description = "Security Client Service Report"
    _order = "date_from desc, partner_id"

    name = fields.Char(compute="_compute_name", store=True)
    partner_id = fields.Many2one("res.partner", required=True, string="Client")
    site_id = fields.Many2one("security.client.site", string="Client Site")
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    prepared_by_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user.id,
        string="Prepared By",
    )
    attendance_record_ids = fields.Many2many(
        "security.attendance.record",
        "security_client_report_attendance_rel",
        "report_id",
        "attendance_id",
        string="Attendance Records",
    )
    roster_slot_ids = fields.Many2many(
        "security.roster.slot",
        "security_client_report_roster_rel",
        "report_id",
        "roster_slot_id",
        string="Roster Slots",
    )
    scheduled_shift_count = fields.Integer(compute="_compute_totals", store=True)
    attended_shift_count = fields.Integer(compute="_compute_totals", store=True)
    absent_shift_count = fields.Integer(compute="_compute_totals", store=True)
    awol_count = fields.Integer(compute="_compute_totals", store=True)
    total_scheduled_hours = fields.Float(compute="_compute_totals", store=True)
    total_payable_hours = fields.Float(compute="_compute_totals", store=True)
    total_unpaid_hours = fields.Float(compute="_compute_totals", store=True)
    include_guard_names = fields.Boolean(default=True, string="Include Guard Names in Report")
    incident_count = fields.Integer(compute="_compute_incident_count", string="Incidents This Period")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("generated", "Generated"),
            ("sent", "Sent"),
        ],
        default="draft",
        required=True,
    )
    note = fields.Text()

    @api.depends("partner_id", "site_id", "date_from", "date_to")
    def _compute_name(self):
        for report in self:
            scope = report.site_id.name or report.partner_id.name or "Client"
            if report.date_from and report.date_to:
                report.name = f"{scope}: {report.date_from} to {report.date_to}"
            else:
                report.name = scope

    @api.depends(
        "attendance_record_ids.status",
        "attendance_record_ids.absence_type",
        "attendance_record_ids.scheduled_hours",
        "attendance_record_ids.payable_hours",
        "attendance_record_ids.unpaid_hours",
        "roster_slot_ids",
    )
    def _compute_totals(self):
        for report in self:
            attendance = report.attendance_record_ids
            report.scheduled_shift_count = len(report.roster_slot_ids)
            report.attended_shift_count = len(
                attendance.filtered(lambda record: record.status in ("present", "late", "early_leave"))
            )
            report.absent_shift_count = len(attendance.filtered(lambda record: record.status == "absent"))
            report.awol_count = len(attendance.filtered(lambda record: record.absence_type == "awol"))
            report.total_scheduled_hours = sum(attendance.mapped("scheduled_hours"))
            report.total_payable_hours = sum(attendance.mapped("payable_hours"))
            report.total_unpaid_hours = sum(attendance.mapped("unpaid_hours"))

    def _compute_incident_count(self):
        incident_model = self.env.get("security.incident")
        for report in self:
            if incident_model is not None and report.site_id:
                report.incident_count = 0  # placeholder — real query when security.incident exists
            else:
                report.incident_count = 0

    @api.onchange("site_id")
    def _onchange_site_id(self):
        for report in self:
            if report.site_id:
                report.partner_id = report.site_id.partner_id

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for report in self:
            if report.date_to < report.date_from:
                raise ValidationError("Report end date cannot be earlier than start date.")

    def action_generate(self):
        attendance_model = self.env["security.attendance.record"]
        roster_model = self.env["security.roster.slot"]
        for report in self:
            domain = [
                ("shift_date", ">=", report.date_from),
                ("shift_date", "<=", report.date_to),
                ("partner_id", "=", report.partner_id.id),
            ]
            if report.site_id:
                domain.append(("site_id", "=", report.site_id.id))
            attendance = attendance_model.search(domain)
            roster = roster_model.search(domain + [("state", "!=", "cancelled")])
            report.attendance_record_ids = [(6, 0, attendance.ids)]
            report.roster_slot_ids = [(6, 0, roster.ids)]
            report.state = "generated"

    def action_mark_sent(self):
        for report in self:
            report.state = "sent"

    def action_reset_to_draft(self):
        for report in self:
            report.state = "draft"

    def action_export_csv(self):
        self.ensure_one()
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Date", "Guard Name", "Post", "Shift Template",
            "Check In", "Check Out", "Status", "Hours",
        ])
        for rec in self.attendance_record_ids.sorted("shift_date"):
            writer.writerow([
                str(rec.shift_date),
                rec.employee_id.name if rec.employee_id else "",
                rec.post_id.name if rec.post_id else "",
                rec.shift_template_id.name if hasattr(rec, "shift_template_id") and rec.shift_template_id else "",
                str(rec.check_in) if rec.check_in else "",
                str(rec.check_out) if rec.check_out else "",
                rec.status or "",
                round(rec.worked_hours, 2) if hasattr(rec, "worked_hours") else 0,
            ])
        csv_bytes = base64.b64encode(output.getvalue().encode("utf-8"))
        attachment = self.env["ir.attachment"].create({
            "name": f"Attendance_{self.name.replace('/', '_')}.csv",
            "type": "binary",
            "datas": csv_bytes,
            "res_model": "security.client.service.report",
            "res_id": self.id,
        })
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
        }
