"""
Excel export wizards for rosters, attendance, billing, and guard hours.
Uses xlsxwriter (bundled with Odoo) to produce multi-sheet formatted .xlsx files.
"""
import base64
import io
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError

_NAVY = "#1B2040"
_AMBER = "#F5A523"
_LIGHT = "#F0F2F7"
_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _make_formats(wb):
    """Return a dict of reusable xlsxwriter Format objects."""
    return {
        "title": wb.add_format({
            "bold": True, "font_color": "white", "bg_color": _NAVY,
            "font_size": 13, "valign": "vcenter",
        }),
        "header": wb.add_format({
            "bold": True, "font_color": "white", "bg_color": _NAVY,
            "border": 1, "align": "center", "valign": "vcenter", "text_wrap": True,
        }),
        "subheader": wb.add_format({
            "bold": True, "font_color": _NAVY, "bg_color": _AMBER,
            "border": 1, "valign": "vcenter",
        }),
        "meta_label": wb.add_format({
            "bold": True, "font_color": _NAVY, "bg_color": _LIGHT,
            "border": 1, "font_size": 10,
        }),
        "meta_val": wb.add_format({
            "font_color": "#333333", "border": 1, "font_size": 10,
        }),
        "row_a": wb.add_format({"border": 1, "font_size": 10, "valign": "vcenter"}),
        "row_b": wb.add_format({
            "bg_color": _LIGHT, "border": 1, "font_size": 10, "valign": "vcenter",
        }),
        "num_a": wb.add_format({
            "border": 1, "font_size": 10, "num_format": "#,##0.00", "valign": "vcenter",
        }),
        "num_b": wb.add_format({
            "bg_color": _LIGHT, "border": 1, "font_size": 10,
            "num_format": "#,##0.00", "valign": "vcenter",
        }),
        "int_a": wb.add_format({"border": 1, "font_size": 10, "num_format": "0"}),
        "int_b": wb.add_format({
            "bg_color": _LIGHT, "border": 1, "font_size": 10, "num_format": "0",
        }),
        "pct_a": wb.add_format({"border": 1, "font_size": 10, "num_format": "0.0%"}),
        "pct_b": wb.add_format({
            "bg_color": _LIGHT, "border": 1, "font_size": 10, "num_format": "0.0%",
        }),
        "total": wb.add_format({
            "bold": True, "font_color": _NAVY, "bg_color": _AMBER,
            "border": 1, "font_size": 10, "num_format": "#,##0.00",
        }),
        "total_int": wb.add_format({
            "bold": True, "font_color": _NAVY, "bg_color": _AMBER,
            "border": 1, "font_size": 10, "num_format": "0",
        }),
        "total_lbl": wb.add_format({
            "bold": True, "font_color": _NAVY, "bg_color": _AMBER,
            "border": 1, "font_size": 10,
        }),
        "status_present": wb.add_format({
            "bg_color": "#DCFCE7", "font_color": "#166534", "border": 1, "font_size": 10,
        }),
        "status_late": wb.add_format({
            "bg_color": "#FEF9C3", "font_color": "#854D0E", "border": 1, "font_size": 10,
        }),
        "status_absent": wb.add_format({
            "bg_color": "#FEE2E2", "font_color": "#991B1B", "border": 1, "font_size": 10,
        }),
        "status_awol": wb.add_format({
            "bg_color": "#F3E8FF", "font_color": "#6B21A8", "border": 1,
            "font_size": 10, "bold": True,
        }),
        "status_incomplete": wb.add_format({
            "bg_color": "#FFF7ED", "font_color": "#9A3412", "border": 1, "font_size": 10,
        }),
        "status_scheduled": wb.add_format({
            "bg_color": "#F8FAFC", "font_color": "#64748B", "border": 1, "font_size": 10,
        }),
        "slot_confirmed": wb.add_format({
            "bg_color": "#DCFCE7", "font_color": "#166534", "border": 1, "font_size": 10,
        }),
        "slot_assigned": wb.add_format({
            "bg_color": "#DBEAFE", "font_color": "#1D4ED8", "border": 1, "font_size": 10,
        }),
        "slot_draft": wb.add_format({
            "bg_color": "#F1F5F9", "font_color": "#64748B", "border": 1, "font_size": 10,
        }),
        "slot_cancelled": wb.add_format({
            "bg_color": "#FEE2E2", "font_color": "#991B1B", "border": 1, "font_size": 10,
        }),
        "approved": wb.add_format({
            "bg_color": "#DCFCE7", "font_color": "#166534", "border": 1, "font_size": 10,
        }),
        "unapproved": wb.add_format({
            "bg_color": "#FEE2E2", "font_color": "#991B1B", "border": 1, "font_size": 10,
        }),
    }


def _att_status_fmt(fmts, status):
    return {
        "present": fmts["status_present"],
        "late": fmts["status_late"],
        "early_leave": fmts["status_late"],
        "absent": fmts["status_absent"],
        "awol": fmts["status_awol"],
        "incomplete": fmts["status_incomplete"],
    }.get(status, fmts["status_scheduled"])


def _slot_state_fmt(fmts, state):
    return {
        "confirmed": fmts["slot_confirmed"],
        "assigned": fmts["slot_assigned"],
        "draft": fmts["slot_draft"],
        "cancelled": fmts["slot_cancelled"],
    }.get(state, fmts["slot_draft"])


def _row_fmts(fmts, i):
    """Return (text_fmt, num_fmt, int_fmt, pct_fmt) for alternating rows."""
    even = i % 2 == 0
    return (
        fmts["row_a"] if even else fmts["row_b"],
        fmts["num_a"] if even else fmts["num_b"],
        fmts["int_a"] if even else fmts["int_b"],
        fmts["pct_a"] if even else fmts["pct_b"],
    )


def _attach_and_download(env, model_name, record_id, filename, xlsx_bytes):
    attachment = env["ir.attachment"].create({
        "name": filename,
        "type": "binary",
        "datas": base64.b64encode(xlsx_bytes),
        "res_model": model_name,
        "res_id": record_id,
    })
    return {
        "type": "ir.actions.act_url",
        "url": f"/web/content/{attachment.id}?download=true",
        "target": "self",
    }


def _require_xlsxwriter():
    try:
        import xlsxwriter
        return xlsxwriter
    except ImportError:
        raise UserError(
            "xlsxwriter is not installed. "
            "Ask your system administrator to install it: pip install xlsxwriter"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Roster Export Wizard
# ─────────────────────────────────────────────────────────────────────────────

class SecurityRosterExportWizard(models.TransientModel):
    _name = "security.roster.export.wizard"
    _description = "Export Roster Batch to Excel"

    batch_id = fields.Many2one("security.roster.batch", required=True, string="Roster Batch")
    include_financials = fields.Boolean(default=True, string="Include Planned Revenue")

    def action_export_excel(self):
        self.ensure_one()
        xlsxwriter = _require_xlsxwriter()

        batch = self.batch_id
        slots = batch.slot_ids.sorted(
            lambda s: (s.shift_date or "", s.site_id.name or "", s.post_id.name or "")
        )

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        fmts = _make_formats(wb)

        # ── Sheet 1: Slot List ──────────────────────────────────────────────
        ws = wb.add_worksheet("Slot List")
        ws.freeze_panes(5, 0)
        col_widths = [12, 8, 20, 20, 18, 7, 7, 24, 14, 12]
        if self.include_financials:
            col_widths += [10, 10]
        for c, w in enumerate(col_widths):
            ws.set_column(c, c, w)

        ws.set_row(0, 28)
        ncols = len(col_widths)
        ws.merge_range(0, 0, 0, ncols - 1, f"Roster Schedule — {batch.name or ''}", fmts["title"])

        meta = [
            ("Client", batch.partner_id.name or "—", "Period",
             f"{batch.date_from} to {batch.date_to}"),
            ("Site", batch.site_id.name or "All Sites", "Status",
             dict(batch._fields["state"].selection).get(batch.state, "")),
        ]
        for ri, (l1, v1, l2, v2) in enumerate(meta, 1):
            ws.write(ri, 0, l1, fmts["meta_label"])
            ws.write(ri, 1, v1, fmts["meta_val"])
            ws.write(ri, 4, l2, fmts["meta_label"])
            ws.write(ri, 5, v2, fmts["meta_val"])

        headers = ["Date", "Day", "Post", "Site", "Shift", "Start", "End",
                   "Guard", "Grade", "State"]
        if self.include_financials:
            headers += ["Dur (h)", "Notes"]
        ws.set_row(4, 20)
        for c, h in enumerate(headers):
            ws.write(4, c, h, fmts["header"])

        for i, slot in enumerate(slots):
            r = 5 + i
            tf, nf, _, _ = _row_fmts(fmts, i)
            sf = _slot_state_fmt(fmts, slot.state)

            d = slot.shift_date
            day = _DAY_NAMES[d.weekday()] if d else ""
            tmpl = slot.shift_template_id
            sh = int(tmpl.start_hour) if tmpl else 0
            sm = int(round((tmpl.start_hour - sh) * 60)) if tmpl else 0
            eh = int(tmpl.end_hour) if tmpl else 0
            em = int(round((tmpl.end_hour - eh) * 60)) if tmpl else 0
            start_s = f"{sh:02d}:{sm:02d}" if tmpl else ""
            end_s = f"{eh:02d}:{em:02d}" if tmpl else ""

            dur = 0.0
            if tmpl:
                dur = tmpl.end_hour - tmpl.start_hour
                if dur <= 0:
                    dur += 24.0

            guard_name = slot.employee_id.name if slot.employee_id else "(Vacant)"
            grade_name = ""
            if slot.employee_id and slot.employee_id.security_grade_id:
                grade_name = slot.employee_id.security_grade_id.name

            ws.write(r, 0, str(d) if d else "", tf)
            ws.write(r, 1, day, tf)
            ws.write(r, 2, slot.post_id.name or "", tf)
            ws.write(r, 3, slot.site_id.name or "", tf)
            ws.write(r, 4, tmpl.name if tmpl else "", tf)
            ws.write(r, 5, start_s, tf)
            ws.write(r, 6, end_s, tf)
            ws.write(r, 7, guard_name, tf)
            ws.write(r, 8, grade_name, tf)
            ws.write(r, 9, slot.state or "", sf)
            if self.include_financials:
                ws.write(r, 10, dur if dur else 0.0, nf)
                ws.write(r, 11, slot.note or "", tf)

        ws.autofilter(4, 0, 4 + len(slots), ncols - 1)

        # Totals row
        tr = 5 + len(slots)
        ws.write(tr, 7, "TOTAL SLOTS", fmts["total_lbl"])
        ws.write(tr, 8, len(slots), fmts["total_int"])
        assigned = sum(1 for s in slots if s.state in ("assigned", "confirmed"))
        ws.write(tr, 9, f"{assigned}/{len(slots)} filled", fmts["total_lbl"])

        # ── Sheet 2: By Guard ───────────────────────────────────────────────
        ws2 = wb.add_worksheet("By Guard")
        ws2.set_row(0, 28)
        ws2.set_column(0, 0, 26)
        ws2.set_column(1, 1, 14)
        ws2.set_column(2, 6, 12)
        ws2.set_column(7, 7, 24)

        ws2.merge_range(0, 0, 0, 7, "Guard Summary", fmts["title"])
        gh = ["Guard", "Total Shifts", "Draft", "Assigned", "Confirmed", "Cancelled", "Vacant Slots", "Sites"]
        for c, h in enumerate(gh):
            ws2.write(1, c, h, fmts["header"])

        gd = defaultdict(lambda: {"draft": 0, "assigned": 0, "confirmed": 0, "cancelled": 0, "sites": set()})
        vacant = 0
        for slot in batch.slot_ids:
            if slot.employee_id:
                d2 = gd[slot.employee_id.name]
                d2[slot.state] = d2.get(slot.state, 0) + 1
                if slot.site_id:
                    d2["sites"].add(slot.site_id.name)
            else:
                vacant += 1

        r2 = 2
        for gname, d2 in sorted(gd.items()):
            tf2, _, if2, _ = _row_fmts(fmts, r2 - 2)
            total = d2["draft"] + d2["assigned"] + d2["confirmed"] + d2["cancelled"]
            ws2.write(r2, 0, gname, tf2)
            ws2.write(r2, 1, total, if2)
            ws2.write(r2, 2, d2["draft"], if2)
            ws2.write(r2, 3, d2["assigned"], if2)
            ws2.write(r2, 4, d2["confirmed"], if2)
            ws2.write(r2, 5, d2["cancelled"], if2)
            ws2.write(r2, 6, 0, if2)
            ws2.write(r2, 7, ", ".join(sorted(d2["sites"])), tf2)
            r2 += 1

        # Totals
        ws2.write(r2, 0, "TOTALS / VACANT", fmts["total_lbl"])
        ws2.write(r2, 1, len(batch.slot_ids), fmts["total_int"])
        ws2.write(r2, 6, vacant, fmts["total_int"])

        wb.close()
        fname = f"Roster_{(batch.name or 'batch').replace('/', '-').replace(' ', '_')[:40]}.xlsx"
        return _attach_and_download(self.env, self._name, self.id, fname, output.getvalue())


# ─────────────────────────────────────────────────────────────────────────────
# Attendance Export Wizard
# ─────────────────────────────────────────────────────────────────────────────

class SecurityAttendanceExportWizard(models.TransientModel):
    _name = "security.attendance.export.wizard"
    _description = "Export Attendance Records to Excel"

    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    partner_id = fields.Many2one("res.partner", string="Client", domain=[("is_company", "=", True)])
    site_id = fields.Many2one("security.client.site", string="Site", domain="[('partner_id','=',partner_id)]")
    include_billing = fields.Boolean(default=True, string="Include Billing Amounts")

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.site_id and self.site_id.partner_id != self.partner_id:
            self.site_id = False

    def action_export_excel(self):
        self.ensure_one()
        xlsxwriter = _require_xlsxwriter()

        domain = [
            ("shift_date", ">=", self.date_from),
            ("shift_date", "<=", self.date_to),
        ]
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        if self.site_id:
            domain.append(("site_id", "=", self.site_id.id))

        records = self.env["security.attendance.record"].search(
            domain, order="shift_date, employee_id"
        )

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        fmts = _make_formats(wb)

        # Pre-collect billing amounts if needed (triggers compute once per record)
        billing_by_id = {}
        if self.include_billing:
            for rec in records:
                billing_by_id[rec.id] = rec.billing_amount or 0.0

        # ── Sheet 1: Summary ────────────────────────────────────────────────
        ws1 = wb.add_worksheet("Summary")
        ws1.set_column(0, 0, 28)
        ws1.set_column(1, 1, 18)
        ws1.set_row(0, 30)

        scope = self.site_id.name or self.partner_id.name or "All Sites"
        ws1.merge_range(0, 0, 0, 1, f"Attendance Report — {scope}", fmts["title"])
        ws1.write(1, 0, "Period", fmts["meta_label"])
        ws1.write(1, 1, f"{self.date_from} to {self.date_to}", fmts["meta_val"])

        present = records.filtered(lambda r: r.status == "present")
        late = records.filtered(lambda r: r.status == "late")
        early = records.filtered(lambda r: r.status == "early_leave")
        absent = records.filtered(lambda r: r.status == "absent")
        awol = records.filtered(lambda r: r.absence_type == "awol" or r.manual_presence == "awol")
        incomplete = records.filtered(lambda r: r.status == "incomplete")
        exceptions = records.filtered(lambda r: r.has_billing_exception)
        approved = records.filtered(lambda r: r.billing_approved)

        attended = len(present) + len(late) + len(early)
        att_rate = attended / len(records) if records else 0.0

        summary_rows = [
            ("Total Records", len(records)),
            ("Present", len(present)),
            ("Late", len(late)),
            ("Early Leave", len(early)),
            ("Absent", len(absent)),
            ("AWOL", len(awol)),
            ("Incomplete (missing check-out)", len(incomplete)),
            ("Attendance Rate", att_rate),
        ]
        ws1.write(3, 0, "Attendance", fmts["subheader"])
        ws1.write(3, 1, "", fmts["subheader"])
        for si, (lbl, val) in enumerate(summary_rows):
            tf, _, if1, pf = _row_fmts(fmts, si)
            ws1.write(4 + si, 0, lbl, tf)
            if isinstance(val, float) and "Rate" in lbl:
                ws1.write(4 + si, 1, val, pf)
            else:
                ws1.write(4 + si, 1, val, if1)

        offset = 4 + len(summary_rows) + 1
        ws1.write(offset, 0, "Hours", fmts["subheader"])
        ws1.write(offset, 1, "", fmts["subheader"])
        hour_rows = [
            ("Total Scheduled Hours", sum(records.mapped("scheduled_hours"))),
            ("Total Worked Hours", sum(records.mapped("worked_hours"))),
            ("Total Normal Hours", sum(records.mapped("normal_hours"))),
            ("Total Night Hours", sum(records.mapped("night_hours"))),
            ("Total Saturday Hours", sum(records.mapped("saturday_hours"))),
            ("Total Sunday Hours", sum(records.mapped("sunday_hours"))),
            ("Total Public Holiday Hours", sum(records.mapped("public_holiday_hours"))),
            ("Total Overtime Hours (Approved)", sum(records.mapped("overtime_hours"))),
        ]
        for hi, (lbl, val) in enumerate(hour_rows):
            tf, nf, _, _ = _row_fmts(fmts, hi)
            ws1.write(offset + 1 + hi, 0, lbl, tf)
            ws1.write(offset + 1 + hi, 1, val, nf)

        if self.include_billing:
            total_billing = sum(billing_by_id.values())
            b_offset = offset + 1 + len(hour_rows) + 1
            ws1.write(b_offset, 0, "Billing", fmts["subheader"])
            ws1.write(b_offset, 1, "", fmts["subheader"])
            ws1.write(b_offset + 1, 0, "Total Billing Amount", fmts["row_a"])
            ws1.write(b_offset + 1, 1, total_billing, fmts["num_a"])
            ws1.write(b_offset + 2, 0, "Billing Exceptions (total)", fmts["row_b"])
            ws1.write(b_offset + 2, 1, len(exceptions), fmts["int_b"])
            ws1.write(b_offset + 3, 0, "Exceptions Approved", fmts["row_a"])
            ws1.write(b_offset + 3, 1, len(approved), fmts["int_a"])

        # ── Sheet 2: All Records ────────────────────────────────────────────
        self._write_attendance_sheet(wb, fmts, records, billing_by_id, "All Records")

        # ── Sheet 3: Exceptions ─────────────────────────────────────────────
        exc_records = records.filtered(lambda r: r.has_billing_exception)
        self._write_attendance_sheet(wb, fmts, exc_records, billing_by_id, "Exceptions", exceptions_only=True)

        wb.close()
        scope_safe = scope.replace("/", "-").replace(" ", "_")[:30]
        fname = f"Attendance_{scope_safe}_{self.date_from}_to_{self.date_to}.xlsx"
        return _attach_and_download(self.env, self._name, self.id, fname, output.getvalue())

    def _write_attendance_sheet(self, wb, fmts, records, billing_by_id, sheet_name, exceptions_only=False):
        ws = wb.add_worksheet(sheet_name)
        ws.freeze_panes(2, 0)

        col_defs = [
            ("Date", 12), ("Guard", 22), ("Site", 18), ("Post", 18), ("Shift", 16),
            ("Check-In", 16), ("Check-Out", 16), ("Status", 12),
            ("Late (min)", 10), ("Early Dep (min)", 12),
            ("Normal h", 10), ("Night h", 10), ("Sat h", 10), ("Sun h", 10), ("PH h", 10),
            ("OT h", 9), ("Worked h", 10),
        ]
        if self.include_billing:
            col_defs.append(("Billing Amt", 13))
        if exceptions_only:
            col_defs += [("Exception Reason", 30), ("Approved", 10), ("Approved By", 20)]

        for c, (_, w) in enumerate(col_defs):
            ws.set_column(c, c, w)
        ws.set_row(0, 20)
        ws.set_row(1, 18)

        ws.merge_range(0, 0, 0, len(col_defs) - 1, sheet_name, fmts["title"])
        for c, (h, _) in enumerate(col_defs):
            ws.write(1, c, h, fmts["header"])

        for i, rec in enumerate(records.sorted("shift_date")):
            r = 2 + i
            tf, nf, if1, _ = _row_fmts(fmts, i)
            sf = _att_status_fmt(fmts, rec.status)

            ci_str = rec.check_in.strftime("%Y-%m-%d %H:%M") if rec.check_in else ""
            co_str = rec.check_out.strftime("%Y-%m-%d %H:%M") if rec.check_out else ""

            row_data = [
                (str(rec.shift_date) if rec.shift_date else "", tf),
                (rec.employee_id.name if rec.employee_id else "", tf),
                (rec.site_id.name if rec.site_id else "", tf),
                (rec.post_id.name if rec.post_id else "", tf),
                (rec.shift_template_id.name if rec.shift_template_id else "", tf),
                (ci_str, tf),
                (co_str, tf),
                (rec.status or "", sf),
                (rec.late_minutes or 0, if1),
                (rec.early_departure_minutes or 0, if1),
                (rec.normal_hours or 0.0, nf),
                (rec.night_hours or 0.0, nf),
                (rec.saturday_hours or 0.0, nf),
                (rec.sunday_hours or 0.0, nf),
                (rec.public_holiday_hours or 0.0, nf),
                (rec.overtime_hours or 0.0, nf),
                (rec.worked_hours or 0.0, nf),
            ]
            if self.include_billing:
                row_data.append((billing_by_id.get(rec.id, 0.0), nf))
            if exceptions_only:
                approved_fmt = fmts["approved"] if rec.billing_approved else fmts["unapproved"]
                row_data += [
                    (rec.billing_exception_reason or "", tf),
                    ("Yes" if rec.billing_approved else "No", approved_fmt),
                    (rec.billing_approved_by_id.name if rec.billing_approved_by_id else "", tf),
                ]

            for c, (val, fmt) in enumerate(row_data):
                ws.write(r, c, val, fmt)

        ws.autofilter(1, 0, 1 + len(records), len(col_defs) - 1)

        # Totals row
        tr = 2 + len(records)
        ws.write(tr, 0, "TOTAL", fmts["total_lbl"])
        hour_cols = {10: "normal_hours", 11: "night_hours", 12: "saturday_hours",
                     13: "sunday_hours", 14: "public_holiday_hours",
                     15: "overtime_hours", 16: "worked_hours"}
        for c, field in hour_cols.items():
            ws.write(tr, c, sum(records.mapped(field)), fmts["total"])
        if self.include_billing:
            ws.write(tr, 17, sum(billing_by_id.get(r.id, 0.0) for r in records), fmts["total"])


# ─────────────────────────────────────────────────────────────────────────────
# Billing Export Wizard
# ─────────────────────────────────────────────────────────────────────────────

class SecurityBillingExportWizard(models.TransientModel):
    _name = "security.billing.export.wizard"
    _description = "Export Billing Data to Excel"

    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    partner_id = fields.Many2one("res.partner", string="Client", domain=[("is_company", "=", True)])
    include_exceptions = fields.Boolean(default=True, string="Include Exception Queue Sheet")

    def action_export_excel(self):
        self.ensure_one()
        xlsxwriter = _require_xlsxwriter()

        inv_domain = [
            ("invoice_date", ">=", self.date_from),
            ("invoice_date", "<=", self.date_to),
            ("state", "!=", "cancelled"),
        ]
        if self.partner_id:
            inv_domain.append(("partner_id", "=", self.partner_id.id))

        invoices = self.env["security.billing.invoice"].search(inv_domain, order="invoice_date, name")

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        fmts = _make_formats(wb)

        inv_state_fmts = {
            "draft": fmts["slot_draft"],
            "sent": fmts["slot_assigned"],
            "paid": fmts["slot_confirmed"],
            "cancelled": fmts["slot_cancelled"],
        }

        # ── Sheet 1: Invoices ───────────────────────────────────────────────
        ws1 = wb.add_worksheet("Invoices")
        ws1.freeze_panes(2, 0)
        col_defs = [
            ("Invoice #", 16), ("Client", 22), ("Site", 18), ("Contract", 20),
            ("Period From", 12), ("Period To", 12), ("Invoice Date", 12),
            ("Due Date", 12), ("State", 12),
            ("Subtotal", 14), ("VAT", 12), ("Total", 14),
        ]
        for c, (_, w) in enumerate(col_defs):
            ws1.set_column(c, c, w)
        ws1.set_row(0, 26)
        ws1.merge_range(0, 0, 0, len(col_defs) - 1,
                        f"Billing Invoices — {self.date_from} to {self.date_to}", fmts["title"])
        for c, (h, _) in enumerate(col_defs):
            ws1.write(1, c, h, fmts["header"])

        for i, inv in enumerate(invoices):
            r = 2 + i
            tf, nf, _, _ = _row_fmts(fmts, i)
            sf = inv_state_fmts.get(inv.state, tf)
            ws1.write(r, 0, inv.name or "", tf)
            ws1.write(r, 1, inv.partner_id.name if inv.partner_id else "", tf)
            ws1.write(r, 2, inv.site_id.name if inv.site_id else "", tf)
            ws1.write(r, 3, inv.contract_id.name if inv.contract_id else "", tf)
            ws1.write(r, 4, str(inv.service_date_from) if inv.service_date_from else "", tf)
            ws1.write(r, 5, str(inv.service_date_to) if inv.service_date_to else "", tf)
            ws1.write(r, 6, str(inv.invoice_date) if inv.invoice_date else "", tf)
            ws1.write(r, 7, str(inv.due_date) if inv.due_date else "", tf)
            ws1.write(r, 8, inv.state or "", sf)
            ws1.write(r, 9, inv.subtotal_amount or 0.0, nf)
            ws1.write(r, 10, inv.vat_amount or 0.0, nf)
            ws1.write(r, 11, inv.total_amount or 0.0, nf)

        tr = 2 + len(invoices)
        ws1.write(tr, 8, "TOTAL", fmts["total_lbl"])
        ws1.write(tr, 9, sum(invoices.mapped("subtotal_amount")), fmts["total"])
        ws1.write(tr, 10, sum(invoices.mapped("vat_amount")), fmts["total"])
        ws1.write(tr, 11, sum(invoices.mapped("total_amount")), fmts["total"])
        ws1.autofilter(1, 0, 1 + len(invoices), len(col_defs) - 1)

        # ── Sheet 2: Invoice Lines ──────────────────────────────────────────
        ws2 = wb.add_worksheet("Invoice Lines")
        ws2.freeze_panes(2, 0)
        lcol_defs = [
            ("Invoice #", 16), ("Client", 22), ("Description", 32), ("Site", 18),
            ("Period From", 12), ("Period To", 12),
            ("Qty (h)", 10), ("Unit Price", 12), ("Subtotal", 14),
        ]
        for c, (_, w) in enumerate(lcol_defs):
            ws2.set_column(c, c, w)
        ws2.set_row(0, 26)
        ws2.merge_range(0, 0, 0, len(lcol_defs) - 1, "Invoice Line Detail", fmts["title"])
        for c, (h, _) in enumerate(lcol_defs):
            ws2.write(1, c, h, fmts["header"])

        row2 = 2
        all_lines = invoices.mapped("line_ids")
        for i, line in enumerate(all_lines):
            tf, nf, _, _ = _row_fmts(fmts, i)
            inv2 = line.invoice_id
            ws2.write(row2, 0, inv2.name if inv2 else "", tf)
            ws2.write(row2, 1, inv2.partner_id.name if inv2 and inv2.partner_id else "", tf)
            ws2.write(row2, 2, line.name or "", tf)
            ws2.write(row2, 3, line.site_id.name if line.site_id else "", tf)
            ws2.write(row2, 4, str(line.service_date_from) if line.service_date_from else "", tf)
            ws2.write(row2, 5, str(line.service_date_to) if line.service_date_to else "", tf)
            ws2.write(row2, 6, line.quantity or 0.0, nf)
            ws2.write(row2, 7, line.unit_price or 0.0, nf)
            ws2.write(row2, 8, line.subtotal or 0.0, nf)
            row2 += 1

        tr2 = row2
        ws2.write(tr2, 7, "TOTAL", fmts["total_lbl"])
        ws2.write(tr2, 8, sum(all_lines.mapped("subtotal")), fmts["total"])

        # ── Sheet 3: Exception Queue ────────────────────────────────────────
        if self.include_exceptions:
            att_model = self.env.get("security.attendance.record")
            if att_model:
                exc_domain = [("has_billing_exception", "=", True)]
                if self.partner_id:
                    exc_domain.append(("partner_id", "=", self.partner_id.id))
                exc_records = att_model.search(exc_domain, order="shift_date, employee_id")

                ws3 = wb.add_worksheet("Exception Queue")
                ws3.freeze_panes(2, 0)
                ecol_defs = [
                    ("Date", 12), ("Guard", 22), ("Site", 18), ("Post", 18),
                    ("Status", 12), ("Exception Reason", 30),
                    ("Billing Amount", 14), ("Approved", 10), ("Approved By", 22),
                ]
                for c, (_, w) in enumerate(ecol_defs):
                    ws3.set_column(c, c, w)
                ws3.set_row(0, 26)
                ws3.merge_range(0, 0, 0, len(ecol_defs) - 1, "Billing Exception Queue", fmts["title"])
                for c, (h, _) in enumerate(ecol_defs):
                    ws3.write(1, c, h, fmts["header"])

                for i, rec in enumerate(exc_records):
                    r3 = 2 + i
                    tf, nf, _, _ = _row_fmts(fmts, i)
                    appr_fmt = fmts["approved"] if rec.billing_approved else fmts["unapproved"]
                    ws3.write(r3, 0, str(rec.shift_date) if rec.shift_date else "", tf)
                    ws3.write(r3, 1, rec.employee_id.name if rec.employee_id else "", tf)
                    ws3.write(r3, 2, rec.site_id.name if rec.site_id else "", tf)
                    ws3.write(r3, 3, rec.post_id.name if rec.post_id else "", tf)
                    ws3.write(r3, 4, rec.status or "", _att_status_fmt(fmts, rec.status))
                    ws3.write(r3, 5, rec.billing_exception_reason or "", tf)
                    ws3.write(r3, 6, rec.billing_amount or 0.0, nf)
                    ws3.write(r3, 7, "Yes" if rec.billing_approved else "No", appr_fmt)
                    ws3.write(r3, 8, rec.billing_approved_by_id.name if rec.billing_approved_by_id else "", tf)

                ws3.autofilter(1, 0, 1 + len(exc_records), len(ecol_defs) - 1)

        wb.close()
        partner_s = (self.partner_id.name or "All").replace(" ", "_")[:20]
        fname = f"Billing_{partner_s}_{self.date_from}_to_{self.date_to}.xlsx"
        return _attach_and_download(self.env, self._name, self.id, fname, output.getvalue())


# ─────────────────────────────────────────────────────────────────────────────
# Guard Hours Export Wizard
# ─────────────────────────────────────────────────────────────────────────────

class SecurityGuardHoursExportWizard(models.TransientModel):
    _name = "security.guard.hours.export.wizard"
    _description = "Export Guard Hours Summary to Excel"

    date_from = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    date_to = fields.Date(required=True, default=lambda self: fields.Date.context_today(self))
    partner_id = fields.Many2one("res.partner", string="Client", domain=[("is_company", "=", True)])
    site_id = fields.Many2one("security.client.site", string="Site", domain="[('partner_id','=',partner_id)]")
    include_billing = fields.Boolean(default=True, string="Include Billing Amounts")

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.site_id and self.site_id.partner_id != self.partner_id:
            self.site_id = False

    def action_export_excel(self):
        self.ensure_one()
        xlsxwriter = _require_xlsxwriter()

        domain = [
            ("shift_date", ">=", self.date_from),
            ("shift_date", "<=", self.date_to),
            ("status", "in", ("present", "late", "early_leave")),
        ]
        if self.partner_id:
            domain.append(("partner_id", "=", self.partner_id.id))
        if self.site_id:
            domain.append(("site_id", "=", self.site_id.id))

        records = self.env["security.attendance.record"].search(domain, order="employee_id, shift_date")

        billing_by_id = {}
        if self.include_billing:
            for rec in records:
                billing_by_id[rec.id] = rec.billing_amount or 0.0

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {"in_memory": True})
        fmts = _make_formats(wb)

        # ── Sheet 1: By Guard ───────────────────────────────────────────────
        ws1 = wb.add_worksheet("By Guard")
        ws1.freeze_panes(2, 0)

        col_defs = [
            ("Guard", 24), ("Grade", 14), ("Shifts", 8),
            ("Normal h", 10), ("Night h", 10), ("Sat h", 10), ("Sun h", 10), ("PH h", 10),
            ("OT h (Approved)", 14), ("Total Hours", 12),
        ]
        if self.include_billing:
            col_defs.append(("Billing Amount", 15))

        for c, (_, w) in enumerate(col_defs):
            ws1.set_column(c, c, w)
        ws1.set_row(0, 26)
        scope = self.site_id.name or self.partner_id.name or "All Sites"
        ws1.merge_range(0, 0, 0, len(col_defs) - 1,
                        f"Guard Hours Summary — {scope} ({self.date_from} to {self.date_to})",
                        fmts["title"])
        for c, (h, _) in enumerate(col_defs):
            ws1.write(1, c, h, fmts["header"])

        # Aggregate by guard
        guard_buckets = defaultdict(lambda: {
            "grade": "", "shifts": 0, "normal": 0.0, "night": 0.0,
            "saturday": 0.0, "sunday": 0.0, "public_holiday": 0.0,
            "overtime": 0.0, "billing": 0.0,
        })
        for rec in records:
            name = rec.employee_id.name if rec.employee_id else "Unknown"
            gb = guard_buckets[name]
            if rec.employee_id and rec.employee_id.security_grade_id:
                gb["grade"] = rec.employee_id.security_grade_id.name
            gb["shifts"] += 1
            gb["normal"] += rec.normal_hours or 0.0
            gb["night"] += rec.night_hours or 0.0
            gb["saturday"] += rec.saturday_hours or 0.0
            gb["sunday"] += rec.sunday_hours or 0.0
            gb["public_holiday"] += rec.public_holiday_hours or 0.0
            gb["overtime"] += rec.overtime_hours or 0.0
            gb["billing"] += billing_by_id.get(rec.id, 0.0)

        for i, (gname, gb) in enumerate(sorted(guard_buckets.items())):
            r = 2 + i
            tf, nf, if1, _ = _row_fmts(fmts, i)
            total_h = gb["normal"] + gb["night"] + gb["saturday"] + gb["sunday"] + gb["public_holiday"]
            ws1.write(r, 0, gname, tf)
            ws1.write(r, 1, gb["grade"], tf)
            ws1.write(r, 2, gb["shifts"], if1)
            ws1.write(r, 3, gb["normal"], nf)
            ws1.write(r, 4, gb["night"], nf)
            ws1.write(r, 5, gb["saturday"], nf)
            ws1.write(r, 6, gb["sunday"], nf)
            ws1.write(r, 7, gb["public_holiday"], nf)
            ws1.write(r, 8, gb["overtime"], nf)
            ws1.write(r, 9, total_h, nf)
            if self.include_billing:
                ws1.write(r, 10, gb["billing"], nf)

        # Totals row
        tr = 2 + len(guard_buckets)
        all_gb = list(guard_buckets.values())
        ws1.write(tr, 0, "TOTAL", fmts["total_lbl"])
        ws1.write(tr, 2, sum(g["shifts"] for g in all_gb), fmts["total_int"])
        ws1.write(tr, 3, sum(g["normal"] for g in all_gb), fmts["total"])
        ws1.write(tr, 4, sum(g["night"] for g in all_gb), fmts["total"])
        ws1.write(tr, 5, sum(g["saturday"] for g in all_gb), fmts["total"])
        ws1.write(tr, 6, sum(g["sunday"] for g in all_gb), fmts["total"])
        ws1.write(tr, 7, sum(g["public_holiday"] for g in all_gb), fmts["total"])
        ws1.write(tr, 8, sum(g["overtime"] for g in all_gb), fmts["total"])
        total_all_h = sum(
            g["normal"] + g["night"] + g["saturday"] + g["sunday"] + g["public_holiday"]
            for g in all_gb
        )
        ws1.write(tr, 9, total_all_h, fmts["total"])
        if self.include_billing:
            ws1.write(tr, 10, sum(g["billing"] for g in all_gb), fmts["total"])

        # ── Sheet 2: Daily Detail ───────────────────────────────────────────
        ws2 = wb.add_worksheet("Daily Detail")
        ws2.freeze_panes(2, 0)
        dcol_defs = [
            ("Date", 12), ("Guard", 24), ("Site", 18), ("Post", 18),
            ("Status", 12), ("Normal h", 10), ("Night h", 10),
            ("Sat h", 10), ("Sun h", 10), ("PH h", 10), ("OT h", 9), ("Total h", 10),
        ]
        if self.include_billing:
            dcol_defs.append(("Billing Amt", 14))

        for c, (_, w) in enumerate(dcol_defs):
            ws2.set_column(c, c, w)
        ws2.set_row(0, 26)
        ws2.merge_range(0, 0, 0, len(dcol_defs) - 1, "Daily Hours Detail", fmts["title"])
        for c, (h, _) in enumerate(dcol_defs):
            ws2.write(1, c, h, fmts["header"])

        for i, rec in enumerate(records):
            r2 = 2 + i
            tf, nf, _, _ = _row_fmts(fmts, i)
            sf = _att_status_fmt(fmts, rec.status)
            total_h = (
                (rec.normal_hours or 0.0) + (rec.night_hours or 0.0) +
                (rec.saturday_hours or 0.0) + (rec.sunday_hours or 0.0) +
                (rec.public_holiday_hours or 0.0)
            )
            ws2.write(r2, 0, str(rec.shift_date) if rec.shift_date else "", tf)
            ws2.write(r2, 1, rec.employee_id.name if rec.employee_id else "", tf)
            ws2.write(r2, 2, rec.site_id.name if rec.site_id else "", tf)
            ws2.write(r2, 3, rec.post_id.name if rec.post_id else "", tf)
            ws2.write(r2, 4, rec.status or "", sf)
            ws2.write(r2, 5, rec.normal_hours or 0.0, nf)
            ws2.write(r2, 6, rec.night_hours or 0.0, nf)
            ws2.write(r2, 7, rec.saturday_hours or 0.0, nf)
            ws2.write(r2, 8, rec.sunday_hours or 0.0, nf)
            ws2.write(r2, 9, rec.public_holiday_hours or 0.0, nf)
            ws2.write(r2, 10, rec.overtime_hours or 0.0, nf)
            ws2.write(r2, 11, total_h, nf)
            if self.include_billing:
                ws2.write(r2, 12, billing_by_id.get(rec.id, 0.0), nf)

        ws2.autofilter(1, 0, 1 + len(records), len(dcol_defs) - 1)

        wb.close()
        scope_safe = scope.replace("/", "-").replace(" ", "_")[:25]
        fname = f"GuardHours_{scope_safe}_{self.date_from}_to_{self.date_to}.xlsx"
        return _attach_and_download(self.env, self._name, self.id, fname, output.getvalue())
