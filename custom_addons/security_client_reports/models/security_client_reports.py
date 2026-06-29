import base64
import csv
import io

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


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

    def action_export_attendance_excel(self):
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(
                "xlsxwriter is not installed. "
                "Ask your system administrator to install it: pip install xlsxwriter"
            )
        from .security_export_wizards import _make_formats, _att_status_fmt, _row_fmts, _attach_and_download

        records = self.attendance_record_ids.sorted("shift_date")
        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        fmts = _make_formats(wb)

        # Summary sheet
        ws1 = wb.add_worksheet("Summary")
        ws1.set_column(0, 0, 30)
        ws1.set_column(1, 1, 18)
        ws1.set_row(0, 28)
        ws1.merge_range(0, 0, 0, 1, f"Service Report — {self.name or ''}", fmts["title"])
        meta = [
            ("Client", self.partner_id.name or ""),
            ("Site", self.site_id.name or "All Sites"),
            ("Period", f"{self.date_from} to {self.date_to}"),
            ("Prepared By", self.prepared_by_id.name if self.prepared_by_id else ""),
        ]
        for ri, (lbl, val) in enumerate(meta, 1):
            ws1.write(ri, 0, lbl, fmts["meta_label"])
            ws1.write(ri, 1, val, fmts["meta_val"])

        ws1.write(6, 0, "Summary", fmts["subheader"])
        ws1.write(6, 1, "", fmts["subheader"])
        stats = [
            ("Scheduled Shifts", self.scheduled_shift_count),
            ("Attended Shifts", self.attended_shift_count),
            ("Absent Shifts", self.absent_shift_count),
            ("AWOL Count", self.awol_count),
            ("Total Scheduled Hours", self.total_scheduled_hours),
            ("Total Payable Hours", self.total_payable_hours),
            ("Total Unpaid Hours", self.total_unpaid_hours),
        ]
        for si, (lbl, val) in enumerate(stats):
            tf, nf, if1, _ = _row_fmts(fmts, si)
            ws1.write(7 + si, 0, lbl, tf)
            ws1.write(7 + si, 1, val, nf if isinstance(val, float) else if1)

        # Detail sheet
        ws2 = wb.add_worksheet("Attendance Detail")
        ws2.freeze_panes(2, 0)
        col_defs = [
            ("Date", 12), ("Guard", 22), ("Site", 18), ("Post", 18), ("Shift", 16),
            ("Check-In", 16), ("Check-Out", 16), ("Status", 12),
            ("Late (min)", 10), ("Early Dep (min)", 12),
            ("Sched h", 9), ("Worked h", 10), ("Payable h", 10),
        ]
        for c, (_, w) in enumerate(col_defs):
            ws2.set_column(c, c, w)
        ws2.set_row(0, 20)
        ws2.set_row(1, 18)
        ws2.merge_range(0, 0, 0, len(col_defs) - 1, "Attendance Detail", fmts["title"])
        for c, (h, _) in enumerate(col_defs):
            ws2.write(1, c, h, fmts["header"])

        for i, rec in enumerate(records):
            r = 2 + i
            tf, nf, if1, _ = _row_fmts(fmts, i)
            sf = _att_status_fmt(fmts, rec.status)
            ci_s = rec.check_in.strftime("%Y-%m-%d %H:%M") if rec.check_in else ""
            co_s = rec.check_out.strftime("%Y-%m-%d %H:%M") if rec.check_out else ""
            row_data = [
                (str(rec.shift_date) if rec.shift_date else "", tf),
                (rec.employee_id.name if rec.employee_id else "", tf),
                (rec.site_id.name if rec.site_id else "", tf),
                (rec.post_id.name if rec.post_id else "", tf),
                (rec.shift_template_id.name if rec.shift_template_id else "", tf),
                (ci_s, tf), (co_s, tf),
                (rec.status or "", sf),
                (rec.late_minutes or 0, if1),
                (rec.early_departure_minutes or 0, if1),
                (rec.scheduled_hours or 0.0, nf),
                (rec.worked_hours or 0.0, nf),
                (rec.payable_hours or 0.0, nf),
            ]
            for c, (val, fmt) in enumerate(row_data):
                ws2.write(r, c, val, fmt)

        ws2.autofilter(1, 0, 1 + len(records), len(col_defs) - 1)
        tr = 2 + len(records)
        ws2.write(tr, 0, "TOTAL", fmts["total_lbl"])
        ws2.write(tr, 10, sum(records.mapped("scheduled_hours")), fmts["total"])
        ws2.write(tr, 11, sum(records.mapped("worked_hours")), fmts["total"])
        ws2.write(tr, 12, sum(records.mapped("payable_hours")), fmts["total"])

        wb.close()
        fname = f"ServiceReport_{(self.name or 'report').replace('/', '-').replace(' ', '_')[:40]}.xlsx"
        return _attach_and_download(self.env, self._name, self.id, fname, output.getvalue())
