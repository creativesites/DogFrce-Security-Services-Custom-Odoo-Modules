"""
Owner endpoints — executive KPI dashboard.
"""
import logging
from datetime import date, timedelta

from odoo import http
from odoo.http import request

from .main import GROUP_OWNER, _json_err, _json_ok, require_group

_logger = logging.getLogger(__name__)


class OwnerController(http.Controller):

    @http.route("/api/security/mobile/owner/kpis",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
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
            month_key = mo_start.strftime("%Y-%m")
            cost = 0.0
            if "security.payslip" in env:
                slips = env["security.payslip"].sudo().search([
                    ("period_id.date_from", ">=", mo_start),
                    ("period_id.date_from", "<",
                     date(yr, mo + 1, 1) if mo < 12 else date(yr + 1, 1, 1)),
                    ("state", "in", ["confirmed", "paid"]),
                ])
                cost = sum(p.total_earnings for p in slips)
            monthly_trend.append({"month": label, "month_key": month_key, "cost": cost})

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

    # ── GET /api/security/mobile/owner/calendar ────────────────────────────
    @http.route("/api/security/mobile/owner/calendar",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_OWNER)
    def owner_calendar(self, **kw):
        """
        Per-day attendance stats for the calendar heatmap view.
        Optional: ?month=YYYY-MM (defaults to current month)
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

        if period_start.month == 12:
            period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

        env = request.env
        batches = env["security.attendance.batch"].sudo().search([
            ("attendance_date", ">=", period_start),
            ("attendance_date", "<=", period_end),
        ])

        # Group batches by date
        from collections import defaultdict
        by_date = defaultdict(list)
        for b in batches:
            by_date[str(b.attendance_date)].append(b)

        # Build one entry per calendar day
        days = []
        current = period_start
        while current <= period_end:
            day_str = str(current)
            day_batches = by_date.get(day_str, [])
            if day_batches:
                records = env["security.attendance.record"].sudo().search([
                    ("attendance_batch_id", "in", [b.id for b in day_batches]),
                ])
                total = len(records)
                present = len(records.filtered(lambda r: r.manual_presence == "present"))
                absent = len(records.filtered(lambda r: r.manual_presence == "absent"))
                awol = len(records.filtered(lambda r: r.manual_presence == "awol"))
                days.append({
                    "date": day_str,
                    "has_data": True,
                    "total": total,
                    "present": present,
                    "absent": absent,
                    "awol": awol,
                    "sites": len(day_batches),
                    "rate": round(present / total * 100, 1) if total else 0.0,
                })
            else:
                days.append({
                    "date": day_str,
                    "has_data": False,
                    "total": 0,
                    "present": 0,
                    "absent": 0,
                    "awol": 0,
                    "sites": 0,
                    "rate": 0.0,
                })
            current += timedelta(days=1)

        return _json_ok({
            "month": period_start.strftime("%B %Y"),
            "period_start": str(period_start),
            "period_end": str(period_end),
            "days": days,
        })

    # ── GET /api/security/mobile/owner/sites ──────────────────────────────
    @http.route("/api/security/mobile/owner/sites",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_OWNER)
    def owner_sites(self, **kw):
        """
        All active sites with period attendance stats + today's batch state.
        Optional: ?month=YYYY-MM
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
            return _json_err(f"Invalid month: {month_param}")

        if period_start.month == 12:
            period_end = date(period_start.year + 1, 1, 1) - timedelta(days=1)
        else:
            period_end = date(period_start.year, period_start.month + 1, 1) - timedelta(days=1)

        env = request.env
        sites = env["security.client.site"].sudo().search([("active", "=", True)])

        # Bulk-fetch all records for the period once
        all_records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id.attendance_date", ">=", period_start),
            ("attendance_batch_id.attendance_date", "<=", period_end),
        ])

        # Bulk-fetch billed invoices for the period (revenue data)
        invoice_revenue = {}  # site_id → revenue float
        if "security.billing.invoice" in env:
            invoices = env["security.billing.invoice"].sudo().search([
                ("state", "in", ["sent", "paid"]),
                ("service_date_from", "<=", str(period_end)),
                ("service_date_to", ">=", str(period_start)),
            ])
            for inv in invoices:
                sid = inv.site_id.id if inv.site_id else None
                if sid:
                    invoice_revenue[sid] = invoice_revenue.get(sid, 0.0) + (inv.total_amount or 0.0)

        # Today's batches for batch-state lookup
        today_batches = {
            b.site_id.id: b
            for b in env["security.attendance.batch"].sudo().search([
                ("attendance_date", "=", today)
            ])
        }

        result = []
        for site in sites:
            site_recs = all_records.filtered(
                lambda r, sid=site.id: r.attendance_batch_id.site_id.id == sid
            )
            total = len(site_recs)
            present_recs = site_recs.filtered(lambda r: r.manual_presence == "present")
            present = len(present_recs)
            absent = len(site_recs.filtered(lambda r: r.manual_presence == "absent"))
            awol = len(site_recs.filtered(lambda r: r.manual_presence == "awol"))
            late = sum(1 for r in present_recs if getattr(r, "late_minutes", 0) > 0)

            # Estimated payroll cost for this site in the period
            payroll_cost = sum(
                (r.payable_hours or 0.0) * r.employee_id.security_effective_hourly_rate
                for r in present_recs
            )
            revenue = invoice_revenue.get(site.id, 0.0)
            margin = revenue - payroll_cost
            margin_pct = round(margin / revenue * 100, 1) if revenue else None

            today_batch = today_batches.get(site.id)
            result.append({
                "site_id": site.id,
                "name": site.name,
                "client": site.partner_id.name if site.partner_id else None,
                "supervisor": site.supervisor_id.name if site.supervisor_id else None,
                "today_state": today_batch.state if today_batch else "no_batch",
                "stats": {
                    "total": total,
                    "present": present,
                    "absent": absent,
                    "awol": awol,
                    "late": late,
                    "rate": round(present / total * 100, 1) if total else 0.0,
                },
                "margin": {
                    "revenue": round(revenue, 2),
                    "payroll_cost": round(payroll_cost, 2),
                    "margin": round(margin, 2),
                    "margin_pct": margin_pct,
                },
            })

        result.sort(key=lambda s: s["stats"]["rate"])  # worst first → flags problems
        return _json_ok({
            "period": period_start.strftime("%B %Y"),
            "sites": result,
        })

    # ── GET /api/security/mobile/owner/guards ─────────────────────────────
    @http.route("/api/security/mobile/owner/guards",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_OWNER)
    def owner_guards(self, **kw):
        """
        Guard performance overview for the past N days.
        Optional: ?days=30 (default 30)
        """
        try:
            lookback = max(7, min(int(kw.get("days", 30)), 365))
        except (ValueError, TypeError):
            lookback = 30

        today = date.today()
        period_start = today - timedelta(days=lookback - 1)

        env = request.env
        guards = env["hr.employee"].sudo().search([
            ("security_guard", "=", True),
            ("active", "=", True),
        ])

        all_records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id.attendance_date", ">=", period_start),
            ("attendance_batch_id.attendance_date", "<=", today),
        ])

        # Index records by employee
        from collections import defaultdict
        rec_by_emp = defaultdict(list)
        for r in all_records:
            rec_by_emp[r.employee_id.id].append(r)

        result = []
        for g in guards:
            recs = rec_by_emp.get(g.id, [])
            total = len(recs)
            present = sum(1 for r in recs if r.manual_presence == "present")
            absent = sum(1 for r in recs if r.manual_presence == "absent")
            awol = sum(1 for r in recs if r.manual_presence == "awol")
            late = sum(1 for r in recs
                       if r.manual_presence == "present"
                       and getattr(r, "late_minutes", 0) > 0)

            # Most recent shift date
            dates = [r.attendance_batch_id.attendance_date for r in recs
                     if r.attendance_batch_id and r.attendance_batch_id.attendance_date]
            last_shift = str(max(dates)) if dates else None

            result.append({
                "id": g.id,
                "name": g.name,
                "grade": g.security_grade_id.name if g.security_grade_id else None,
                "reliability_score": getattr(g, "reliability_score", None),
                "last_shift": last_shift,
                "stats": {
                    "total": total,
                    "present": present,
                    "absent": absent,
                    "awol": awol,
                    "late": late,
                    "rate": round(present / total * 100, 1) if total else 0.0,
                },
            })

        result.sort(key=lambda g: g["stats"]["rate"])  # worst performers first
        return _json_ok({
            "period_days": lookback,
            "period_start": str(period_start),
            "guards": result,
        })

    # ── GET /api/security/mobile/owner/site/<id> ───────────────────────────
    @http.route("/api/security/mobile/owner/site/<int:site_id>",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_OWNER)
    def owner_site_detail(self, site_id, **kw):
        """
        Full site deep-dive for the owner.
        Returns today's live roster, month stats, 30-day trend, and invoice aging.
        """
        from collections import defaultdict

        today = date.today()
        env = request.env

        site = env["security.client.site"].sudo().browse(site_id)
        if not site.exists():
            return _json_err(f"Site {site_id} not found.", status=404)

        # ── Site & contacts ────────────────────────────────────────────────
        client = site.partner_id
        sup = site.supervisor_id

        site_data = {
            "id": site.id,
            "name": site.name,
            "code": site.code or None,
            "location": site.location or None,
            "note": site.note or None,
            "client": {
                "id": client.id,
                "name": client.name,
                "phone": getattr(client, 'phone', None) or None,
                "mobile": getattr(client, 'mobile', None) or None,
                "email": getattr(client, 'email', None) or None,
                "street": getattr(client, 'street', None) or None,
                "city": getattr(client, 'city', None) or None,
            } if client else None,
            "supervisor": {
                "id": sup.id,
                "name": sup.name,
                "phone": sup.work_phone or None,
                "mobile": sup.mobile_phone or None,
                "email": sup.work_email or None,
            } if sup else None,
        }

        # ── Today's live roster ────────────────────────────────────────────
        today_batch = env["security.attendance.batch"].sudo().search(
            [("site_id", "=", site_id), ("attendance_date", "=", today)], limit=1
        )
        if today_batch:
            today_records = env["security.attendance.record"].sudo().search(
                [("attendance_batch_id", "=", today_batch.id)]
            )
            total_today = len(today_records)
            present_t = len(today_records.filtered(lambda r: r.manual_presence == "present"))
            absent_t = len(today_records.filtered(lambda r: r.manual_presence == "absent"))
            awol_t = len(today_records.filtered(lambda r: r.manual_presence == "awol"))
            not_marked_t = total_today - present_t - absent_t - awol_t
            roster = []
            for r in today_records:
                slot = r.roster_slot_id
                emp = r.employee_id
                check_in_str = None
                if r.check_in:
                    try:
                        check_in_str = r.check_in.strftime("%H:%M")
                    except Exception:
                        check_in_str = str(r.check_in)
                roster.append({
                    "guard_id": emp.id,
                    "guard_name": emp.name,
                    "grade": emp.security_grade_id.name if emp.security_grade_id else None,
                    "post": slot.post_id.name if slot else None,
                    "shift": slot.shift_template_id.name if slot else None,
                    "presence": r.manual_presence or "not_marked",
                    "check_in": check_in_str,
                    "late_minutes": getattr(r, "late_minutes", 0),
                })
            today_data = {
                "batch_id": today_batch.id,
                "batch_state": today_batch.state,
                "total": total_today,
                "present": present_t,
                "absent": absent_t,
                "awol": awol_t,
                "not_marked": not_marked_t,
                "rate": round(present_t / total_today * 100, 1) if total_today else 0.0,
                "roster": roster,
            }
        else:
            # No batch today — fall back to roster slots
            slots = env["security.roster.slot"].sudo().search([
                ("site_id", "=", site_id),
                ("shift_date", "=", today),
                ("state", "!=", "cancelled"),
            ])
            roster = [{
                "guard_id": s.employee_id.id if s.employee_id else None,
                "guard_name": s.employee_id.name if s.employee_id else "Unassigned",
                "grade": s.employee_id.security_grade_id.name
                         if s.employee_id and s.employee_id.security_grade_id else None,
                "post": s.post_id.name if s.post_id else None,
                "shift": s.shift_template_id.name if s.shift_template_id else None,
                "presence": "not_marked",
                "check_in": None,
                "late_minutes": 0,
            } for s in slots]
            today_data = {
                "batch_id": None,
                "batch_state": "no_batch",
                "total": len(slots),
                "present": 0, "absent": 0, "awol": 0,
                "not_marked": len(slots),
                "rate": 0.0,
                "roster": roster,
            }

        # ── Current-month stats ────────────────────────────────────────────
        month_start = date(today.year, today.month, 1)
        month_records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id.site_id", "=", site_id),
            ("attendance_batch_id.attendance_date", ">=", month_start),
            ("attendance_batch_id.attendance_date", "<=", today),
        ])
        mo_total = len(month_records)
        mo_present = len(month_records.filtered(lambda r: r.manual_presence == "present"))
        mo_absent = len(month_records.filtered(lambda r: r.manual_presence == "absent"))
        mo_awol = len(month_records.filtered(lambda r: r.manual_presence == "awol"))
        month_stats = {
            "period": month_start.strftime("%B %Y"),
            "total": mo_total,
            "present": mo_present,
            "absent": mo_absent,
            "awol": mo_awol,
            "rate": round(mo_present / mo_total * 100, 1) if mo_total else 0.0,
        }

        # ── 30-day daily trend ─────────────────────────────────────────────
        trend_start = today - timedelta(days=29)
        trend_records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id.site_id", "=", site_id),
            ("attendance_batch_id.attendance_date", ">=", trend_start),
            ("attendance_batch_id.attendance_date", "<=", today),
        ])
        by_date_trend = defaultdict(list)
        for r in trend_records:
            d_key = str(r.attendance_batch_id.attendance_date)
            by_date_trend[d_key].append(r)

        trend = []
        cur = trend_start
        while cur <= today:
            dk = str(cur)
            recs = by_date_trend.get(dk, [])
            t = len(recs)
            p = sum(1 for r in recs if r.manual_presence == "present")
            trend.append({
                "date": dk,
                "total": t,
                "present": p,
                "rate": round(p / t * 100, 1) if t else 0.0,
                "has_data": t > 0,
            })
            cur += timedelta(days=1)

        # ── Invoice / financial aging ──────────────────────────────────────
        financials = {"invoices_outstanding": 0.0, "invoices_count": 0,
                      "aging": {"current": 0.0, "days_30": 0.0, "days_60": 0.0, "days_90_plus": 0.0},
                      "margin": None}
        if "security.billing.invoice" in env:
            invoices = env["security.billing.invoice"].sudo().search([
                ("site_id", "=", site_id),
                ("state", "not in", ["paid", "cancelled"]),
            ])
            for inv in invoices:
                amt = inv.total_amount or 0.0
                financials["invoices_outstanding"] += amt
                financials["invoices_count"] += 1
                due = inv.due_date
                if not due:
                    financials["aging"]["current"] += amt
                else:
                    overdue_days = (today - due).days
                    if overdue_days <= 0:
                        financials["aging"]["current"] += amt
                    elif overdue_days <= 30:
                        financials["aging"]["days_30"] += amt
                    elif overdue_days <= 60:
                        financials["aging"]["days_60"] += amt
                    else:
                        financials["aging"]["days_90_plus"] += amt

            # Month margin: revenue (sent+paid this month) vs payroll cost
            month_invoices = env["security.billing.invoice"].sudo().search([
                ("site_id", "=", site_id),
                ("state", "in", ["sent", "paid"]),
                ("service_date_from", "<=", str(today)),
                ("service_date_from", ">=", str(month_start)),
            ])
            revenue = sum(inv.total_amount or 0.0 for inv in month_invoices)
            present_recs = month_records.filtered(lambda r: r.manual_presence == "present")
            payroll_cost = sum(
                (r.payable_hours or 0.0) * r.employee_id.security_effective_hourly_rate
                for r in present_recs
            )
            margin = revenue - payroll_cost
            margin_pct = round(margin / revenue * 100, 1) if revenue else None
            financials["margin"] = {
                "revenue": round(revenue, 2),
                "payroll_cost": round(payroll_cost, 2),
                "margin": round(margin, 2),
                "margin_pct": margin_pct,
            }

        return _json_ok({
            "site": site_data,
            "today": today_data,
            "month_stats": month_stats,
            "trend": trend,
            "financials": financials,
        })

    # ── GET /api/security/mobile/owner/guard/<id> ─────────────────────────
    @http.route("/api/security/mobile/owner/guard/<int:guard_id>",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_OWNER)
    def owner_guard_detail(self, guard_id, **kw):
        """Guard profile deep-dive: certifications, reliability, recent history."""
        today = date.today()
        env = request.env

        guard = env["hr.employee"].sudo().browse(guard_id)
        if not guard.exists():
            return _json_err(f"Guard {guard_id} not found.", status=404)

        # ── Certifications ─────────────────────────────────────────────────
        certs = []
        for cert in guard.security_certification_detail_ids:
            is_expired = getattr(cert, "is_expired", False)
            days_to_expiry = None
            if cert.expiry_date:
                days_to_expiry = (cert.expiry_date - today).days
            certs.append({
                "name": cert.certification_id.name if cert.certification_id else None,
                "ref": cert.document_ref or None,
                "issue_date": str(cert.issue_date) if cert.issue_date else None,
                "expiry_date": str(cert.expiry_date) if cert.expiry_date else None,
                "days_to_expiry": days_to_expiry,
                "verified": cert.verified,
                "is_expired": is_expired,
                "expiring_soon": days_to_expiry is not None and 0 <= days_to_expiry <= 30,
            })

        # ── Today's assignment ────────────────────────────────────────────
        today_record = env["security.attendance.record"].sudo().search([
            ("employee_id", "=", guard_id),
            ("attendance_batch_id.attendance_date", "=", today),
        ], limit=1)
        today_assignment = None
        if today_record:
            batch = today_record.attendance_batch_id
            slot = today_record.roster_slot_id
            today_assignment = {
                "site_id": batch.site_id.id if batch.site_id else None,
                "site_name": batch.site_id.name if batch.site_id else None,
                "post": slot.post_id.name if slot else None,
                "shift": slot.shift_template_id.name if slot else None,
                "presence": today_record.manual_presence or "not_marked",
                "check_in": today_record.check_in.strftime("%H:%M") if today_record.check_in else None,
            }

        # ── 30-day stats ──────────────────────────────────────────────────
        lookback_start = today - timedelta(days=29)
        recent_records = env["security.attendance.record"].sudo().search([
            ("employee_id", "=", guard_id),
            ("attendance_batch_id.attendance_date", ">=", lookback_start),
            ("attendance_batch_id.attendance_date", "<=", today),
        ])
        r_total = len(recent_records)
        r_present = sum(1 for r in recent_records if r.manual_presence == "present")
        r_absent = sum(1 for r in recent_records if r.manual_presence == "absent")
        r_awol = sum(1 for r in recent_records if r.manual_presence == "awol")
        r_late = sum(1 for r in recent_records
                     if r.manual_presence == "present" and getattr(r, "late_minutes", 0) > 0)

        # ── Recent shift history (last 10) ───────────────────────────────
        history_records = env["security.attendance.record"].sudo().search([
            ("employee_id", "=", guard_id),
        ], order="id desc", limit=10)
        history = []
        for r in history_records:
            batch = r.attendance_batch_id
            slot = r.roster_slot_id
            history.append({
                "date": str(batch.attendance_date) if batch and batch.attendance_date else None,
                "site": batch.site_id.name if batch and batch.site_id else None,
                "post": slot.post_id.name if slot else None,
                "shift": slot.shift_template_id.name if slot else None,
                "presence": r.manual_presence or "not_marked",
                "late_minutes": getattr(r, "late_minutes", 0),
            })

        return _json_ok({
            "guard": {
                "id": guard.id,
                "name": guard.name,
                "grade": guard.security_grade_id.name if guard.security_grade_id else None,
                "reliability_score": guard.security_reliability_score,
                "mobile_phone": guard.mobile_phone or None,
                "work_phone": guard.work_phone or None,
                "work_email": guard.work_email or None,
                "disqualified": guard.security_disqualified,
                "certifications": certs,
                "expiring_cert_count": guard.security_expiring_certification_count,
                "attributes": [a.name for a in guard.security_attribute_ids],
            },
            "today_assignment": today_assignment,
            "stats_30d": {
                "total": r_total,
                "present": r_present,
                "absent": r_absent,
                "awol": r_awol,
                "late": r_late,
                "rate": round(r_present / r_total * 100, 1) if r_total else 0.0,
            },
            "history": history,
        })

    # ── GET /api/security/mobile/owner/live ───────────────────────────────
    @http.route("/api/security/mobile/owner/live",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_OWNER)
    def owner_live_timeline(self, **kw):
        """
        Real-time view of today's attendance across every active site.
        Sorted by problem severity (AWOL > absent > not_marked).
        """
        today = date.today()
        env = request.env

        batches = env["security.attendance.batch"].sudo().search([
            ("attendance_date", "=", today),
        ])

        sites = []
        for batch in batches:
            records = env["security.attendance.record"].sudo().search([
                ("attendance_batch_id", "=", batch.id)
            ])
            total = len(records)
            present_recs = records.filtered(lambda r: r.manual_presence == "present")
            absent_recs = records.filtered(lambda r: r.manual_presence == "absent")
            awol_recs = records.filtered(lambda r: r.manual_presence == "awol")
            not_marked = total - len(present_recs) - len(absent_recs) - len(awol_recs)

            guards = []
            for r in records:
                guards.append({
                    "id": r.employee_id.id,
                    "name": r.employee_id.name,
                    "grade": r.employee_id.security_grade_id.name
                              if r.employee_id.security_grade_id else None,
                    "presence": r.manual_presence or "not_marked",
                    "check_in": r.check_in.strftime("%H:%M") if r.check_in else None,
                    "late_minutes": getattr(r, "late_minutes", 0),
                    "post": r.post_id.name if r.post_id else None,
                })

            site = batch.site_id
            sup = site.supervisor_id if site else None
            sites.append({
                "site_id": site.id if site else None,
                "site_name": site.name if site else "Unknown",
                "batch_id": batch.id,
                "batch_state": batch.state,
                "supervisor": sup.name if sup else None,
                "total": total,
                "present": len(present_recs),
                "absent": len(absent_recs),
                "awol": len(awol_recs),
                "not_marked": not_marked,
                "rate": round(len(present_recs) / total * 100, 1) if total else 0.0,
                "guards": guards,
            })

        # Sort: most critical first (AWOL heaviest, then absent, then not_marked)
        sites.sort(
            key=lambda s: (s["awol"] * 3 + s["absent"] * 2 + s["not_marked"]),
            reverse=True,
        )

        t_guards = sum(s["total"] for s in sites)
        t_present = sum(s["present"] for s in sites)
        t_absent = sum(s["absent"] for s in sites)
        t_awol = sum(s["awol"] for s in sites)
        t_nm = sum(s["not_marked"] for s in sites)

        return _json_ok({
            "date": str(today),
            "as_of": str(date.today()),
            "summary": {
                "total_sites": len(sites),
                "sites_submitted": len([s for s in sites if s["batch_state"] in ("reviewed", "locked")]),
                "sites_in_progress": len([s for s in sites if s["batch_state"] in ("draft", "captured")]),
                "total_guards": t_guards,
                "total_present": t_present,
                "total_absent": t_absent,
                "total_awol": t_awol,
                "total_not_marked": t_nm,
                "overall_rate": round(t_present / t_guards * 100, 1) if t_guards else 0.0,
            },
            "sites": sites,
        })
