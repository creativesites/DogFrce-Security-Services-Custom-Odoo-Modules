"""
Owner endpoints — executive KPI dashboard.
"""
import logging
from datetime import date

from odoo import http
from odoo.http import request

from .main import GROUP_OWNER, _json_err, _json_ok, require_group

_logger = logging.getLogger(__name__)


class OwnerController(http.Controller):

    @http.route("/api/security/mobile/owner/kpis",
                auth="user", methods=["GET"], type="http", csrf=False)
    @require_group(GROUP_OWNER)
    def owner_kpis(self, **kw):
        """
        Executive KPI dashboard for the owner.

        Optional query params:
          ?month=YYYY-MM   (defaults to current month)
        """
        month_param = kw.get("month")
        today = date.today()
        try:
            if month_param:
                year, mon = [int(x) for x in month_param.split("-")]
                period_start = date(year, mon, 1)
            else:
                period_start = date(today.year, today.month, 1)
        except (ValueError, TypeError):
            return _json_err(f"Invalid month format: {month_param}. Use YYYY-MM.")

        # Calculate period end (last day of chosen month)
        if period_start.month == 12:
            period_end = date(period_start.year + 1, 1, 1)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1)
        # Shift one day back
        from datetime import timedelta
        period_end = period_end - timedelta(days=1)

        period_label = period_start.strftime("%B %Y")
        env = request.env

        # ── Attendance KPIs ────────────────────────────────────────────────
        all_records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id.attendance_date", ">=", period_start),
            ("attendance_batch_id.attendance_date", "<=", period_end),
        ])
        total_records  = len(all_records)
        present_count  = len(all_records.filtered(lambda r: r.manual_presence == "present"))
        absent_count   = len(all_records.filtered(lambda r: r.manual_presence == "absent"))
        awol_count     = len(all_records.filtered(lambda r: r.manual_presence == "awol"))
        late_count     = sum(1 for r in all_records
                             if r.manual_presence == "present"
                             and getattr(r, "late_minutes", 0) > 0)

        attendance_rate = round(present_count / total_records * 100, 1) if total_records else 0.0

        # ── Active guard count ─────────────────────────────────────────────
        guard_count = env["hr.employee"].sudo().search_count([
            ("security_guard", "=", True),
            ("active", "=", True),
        ])

        # ── Active sites ───────────────────────────────────────────────────
        sites_active = env["security.client.site"].sudo().search_count([("active", "=", True)])

        # ── Open incidents (security.incident if module present) ───────────
        open_incidents = 0
        if "security.incident" in env:
            open_incidents = env["security.incident"].sudo().search_count([
                ("state", "=", "draft"),
            ])

        # ── Payroll cost YTD ───────────────────────────────────────────────
        payroll_cost_ytd = 0.0
        ytd_start = date(today.year, 1, 1)
        if "security.payslip" in env:
            payslips = env["security.payslip"].sudo().search([
                ("period_id.date_from", ">=", ytd_start),
                ("state", "in", ["confirmed", "paid"]),
            ])
            payroll_cost_ytd = sum(p.total_earnings for p in payslips)

        # ── Outstanding invoices ───────────────────────────────────────────
        outstanding_invoices = 0.0
        if "security.billing.invoice" in env:
            invoices = env["security.billing.invoice"].sudo().search([
                ("state", "not in", ["paid", "cancelled"]),
            ])
            outstanding_invoices = sum(inv.total_amount for inv in invoices)

        # ── Monthly payroll trend (last 6 months) ─────────────────────────
        monthly_trend = []
        for i in range(5, -1, -1):
            mo = today.month - i
            yr = today.year
            while mo <= 0:
                mo += 12
                yr -= 1
            mo_start = date(yr, mo, 1)
            label = mo_start.strftime("%b %Y")
            cost = 0.0
            if "security.payslip" in env:
                slips = env["security.payslip"].sudo().search([
                    ("period_id.date_from", ">=", mo_start),
                    ("period_id.date_from", "<",
                     date(yr, mo + 1, 1) if mo < 12 else date(yr + 1, 1, 1)),
                    ("state", "in", ["confirmed", "paid"]),
                ])
                cost = sum(p.total_earnings for p in slips)
            monthly_trend.append({"month": label, "cost": cost})

        # ── Top 5 sites by attendance rate ─────────────────────────────────
        sites = env["security.client.site"].sudo().search([("active", "=", True)])
        site_rates = []
        for site in sites:
            site_recs = all_records.filtered(lambda r: r.attendance_batch_id.site_id.id == site.id)
            s_total   = len(site_recs)
            s_present = len(site_recs.filtered(lambda r: r.manual_presence == "present"))
            site_rates.append({
                "site_id": site.id,
                "site_name": site.name,
                "client": site.partner_id.name,
                "total_records": s_total,
                "present": s_present,
                "attendance_rate": round(s_present / s_total * 100, 1) if s_total else 0,
            })
        top_sites = sorted(site_rates, key=lambda x: x["attendance_rate"], reverse=True)[:5]

        return _json_ok({
            "period": period_label,
            "period_start": str(period_start),
            "period_end": str(period_end),
            "attendance": {
                "rate_percent": attendance_rate,
                "total_records": total_records,
                "present": present_count,
                "absent": absent_count,
                "awol": awol_count,
                "late": late_count,
            },
            "total_guards": guard_count,
            "sites_active": sites_active,
            "open_incidents": open_incidents,
            "payroll_cost_ytd": payroll_cost_ytd,
            "outstanding_invoices": outstanding_invoices,
            "monthly_payroll_trend": monthly_trend,
            "top_sites_by_attendance": top_sites,
        })
