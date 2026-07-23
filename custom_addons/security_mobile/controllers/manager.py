"""
Manager endpoints — multi-site dashboard & overtime approval.
"""
import logging
from datetime import date

from odoo import http
from odoo.http import request

from .main import (
    GROUP_MANAGER,
    GROUP_OWNER,
    _json_err,
    _json_ok,
    _parse_body,
    require_group,
)

_logger = logging.getLogger(__name__)


def _site_summary(site, today):
    env = request.env
    batch = env["security.attendance.batch"].sudo().search(
        [("site_id", "=", site.id), ("attendance_date", "=", today)], limit=1
    )
    if batch:
        records = env["security.attendance.record"].sudo().search([("attendance_batch_id", "=", batch.id)])
        total      = len(records)
        present    = len(records.filtered(lambda r: r.manual_presence == "present"))
        absent     = len(records.filtered(lambda r: r.manual_presence == "absent"))
        awol       = len(records.filtered(lambda r: r.manual_presence == "awol"))
        not_marked = total - present - absent - awol
        late = sum(1 for r in records if r.manual_presence == "present"
                   and hasattr(r, "late_minutes") and r.late_minutes > 0)
        batch_state = batch.state
    else:
        slots = env["security.roster.slot"].sudo().search(
            [("site_id", "=", site.id), ("shift_date", "=", today), ("state", "!=", "cancelled")]
        )
        total = len(slots)
        present = absent = awol = late = not_marked = 0
        batch_state = "no_batch"

    return {
        "site_id": site.id,
        "site_name": site.name,
        "client": site.partner_id.name,
        "supervisor": site.supervisor_id.name if site.supervisor_id else None,
        "total_slots": total,
        "present": present,
        "absent": absent,
        "awol": awol,
        "late": late,
        "not_marked": not_marked,
        "attendance_rate": round(present / total * 100, 1) if total else 0,
        "batch_state": batch_state,
        "batch_id": batch.id if batch else None,
    }


def _serialize_rec(rec):
    slot = rec.roster_slot_id
    emp  = rec.employee_id
    return {
        "record_id": rec.id,
        "guard": {"id": emp.id, "name": emp.name,
                  "grade": emp.security_grade_id.name if emp.security_grade_id else None},
        "post": slot.post_id.name if slot else None,
        "shift": slot.shift_template_id.name if slot else None,
        "manual_presence": rec.manual_presence or "not_marked",
        "check_in": rec.check_in.isoformat() if rec.check_in else None,
        "check_out": rec.check_out.isoformat() if rec.check_out else None,
        "late_minutes": getattr(rec, "late_minutes", 0),
        "overtime_hours": getattr(rec, "overtime_hours", 0),
        "overtime_approved": getattr(rec, "overtime_approved", False),
    }


class ManagerController(http.Controller):

    @http.route("/api/security/mobile/manager/dashboard",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_dashboard(self, **kw):
        """Multi-site attendance summary. ?date=YYYY-MM-DD defaults to today."""
        try:
            target_date = date.fromisoformat(kw["date"]) if "date" in kw else date.today()
        except ValueError:
            return _json_err(f"Invalid date: {kw.get('date')}")

        sites = request.env["security.client.site"].sudo().search([("active", "=", True)])
        summaries = [_site_summary(s, target_date) for s in sites]

        total_slots   = sum(s["total_slots"] for s in summaries)
        total_present = sum(s["present"] for s in summaries)

        return _json_ok({
            "date": str(target_date),
            "overall": {
                "total_slots": total_slots,
                "present": total_present,
                "absent": sum(s["absent"] for s in summaries),
                "awol": sum(s["awol"] for s in summaries),
                "late": sum(s["late"] for s in summaries),
                "attendance_rate": round(total_present / total_slots * 100, 1) if total_slots else 0,
            },
            "sites": summaries,
        })

    @http.route("/api/security/mobile/manager/site/<int:site_id>",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_site_detail(self, site_id, **kw):
        """Detailed roster for one site. ?date=YYYY-MM-DD"""
        try:
            target_date = date.fromisoformat(kw["date"]) if "date" in kw else date.today()
        except ValueError:
            return _json_err(f"Invalid date: {kw.get('date')}")

        env  = request.env
        site = env["security.client.site"].sudo().browse(site_id)
        if not site.exists():
            return _json_err(f"Site {site_id} not found.", status=404)

        batch = env["security.attendance.batch"].sudo().search(
            [("site_id", "=", site_id), ("attendance_date", "=", target_date)], limit=1
        )

        if batch:
            records = env["security.attendance.record"].sudo().search(
                [("attendance_batch_id", "=", batch.id)], order="employee_id asc"
            )
            roster = [_serialize_rec(r) for r in records]
            overtime_pending = [_serialize_rec(r) for r in records
                                if getattr(r, "overtime_hours", 0) > 0
                                and not getattr(r, "overtime_approved", False)]
        else:
            slots = env["security.roster.slot"].sudo().search(
                [("site_id", "=", site_id), ("shift_date", "=", target_date),
                 ("state", "!=", "cancelled")], order="shift_template_id, post_id"
            )
            roster = [{"slot_id": s.id, "record_id": None,
                       "guard": {"id": s.employee_id.id if s.employee_id else None,
                                 "name": s.employee_id.name if s.employee_id else "Unassigned",
                                 "grade": s.employee_id.security_grade_id.name
                                 if s.employee_id and s.employee_id.security_grade_id else None},
                       "post": s.post_id.name, "shift": s.shift_template_id.name,
                       "manual_presence": "not_marked"} for s in slots]
            overtime_pending = []

        return _json_ok({
            "date": str(target_date),
            "site": {"id": site.id, "name": site.name, "client": site.partner_id.name},
            "batch_id": batch.id if batch else None,
            "batch_state": batch.state if batch else "no_batch",
            "supervisor": site.supervisor_id.name if site.supervisor_id else None,
            "roster": roster,
            "overtime_pending": overtime_pending,
        })

    @http.route("/api/security/mobile/manager/overtime",
                auth="user", methods=["GET"], type="http", csrf=False, cors="*")
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_overtime_list(self, **kw):
        """All attendance records with pending overtime across all sites."""
        env = request.env
        records = env["security.attendance.record"].sudo().search([
            ("overtime_approved", "=", False),
        ])
        pending = [r for r in records if getattr(r, "overtime_hours", 0) > 0]

        result = []
        for rec in pending:
            batch = rec.attendance_batch_id
            site = batch.site_id if batch else None
            result.append({
                "record_id": rec.id,
                "guard": {
                    "id": rec.employee_id.id,
                    "name": rec.employee_id.name,
                    "grade": rec.employee_id.security_grade_id.name
                    if rec.employee_id.security_grade_id else None,
                },
                "site_name": site.name if site else None,
                "post": rec.post_id.name if rec.post_id else None,
                "shift": rec.shift_template_id.name if rec.shift_template_id else None,
                "hours": getattr(rec, "overtime_hours", 0),
                "date": str(batch.attendance_date)
                if batch and hasattr(batch, "attendance_date") else None,
            })

        return _json_ok(result)

    @http.route("/api/security/mobile/manager/overtime/approve",
                auth="user", methods=["POST"], type="http", csrf=False, cors="*")
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_overtime_approve(self, **kw):
        """Approve/reject overtime. Body: {record_id, approved, note?}"""
        body      = _parse_body()
        record_id = body.get("record_id")
        if not record_id:
            return _json_err("record_id is required.")

        record = request.env["security.attendance.record"].sudo().browse(int(record_id))
        if not record.exists():
            return _json_err(f"Record {record_id} not found.", status=404)

        vals = {"overtime_approved": bool(body.get("approved", True))}
        if body.get("note"):
            vals["overtime_approval_note"] = body["note"]
        record.write(vals)

        return _json_ok({"record_id": record.id,
                         "overtime_approved": getattr(record, "overtime_approved", True)})

    @http.route(
        "/api/security/mobile/manager/leave-requests",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
        cors="*",
    )
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_leave_requests(self, **kw):
        """Pending leave requests awaiting manager approval."""
        env = request.env
        if "security.leave.request" not in env:
            return _json_ok([])

        requests = env["security.leave.request"].sudo().search(
            [("state", "=", "draft")],
            order="date_from asc",
        )
        return _json_ok([
            {
                "id": req.id,
                "employee": {
                    "id": req.employee_id.id,
                    "name": req.employee_id.name,
                    "grade": req.employee_id.security_grade_id.name
                    if req.employee_id.security_grade_id else None,
                },
                "leave_type": req.leave_type_id.name if req.leave_type_id else None,
                "date_from": str(req.date_from),
                "date_to": str(req.date_to),
                "requested_days": req.requested_days,
                "state": req.state,
                "balance_days": req.balance_id.balance_days
                if req.balance_id else None,
            }
            for req in requests
        ])

    @http.route(
        "/api/security/mobile/manager/leave-requests/<int:req_id>/action",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
        cors="*",
    )
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_leave_action(self, req_id, **kw):
        """Approve or refuse a leave request. Body: { action: 'approve'|'refuse' }"""
        body = _parse_body()
        action = body.get("action")
        if action not in ("approve", "refuse"):
            return _json_err("action must be 'approve' or 'refuse'.")

        env = request.env
        req = env["security.leave.request"].sudo().browse(req_id)
        if not req.exists():
            return _json_err(f"Leave request {req_id} not found.", status=404)
        if req.state != "draft":
            return _json_err(f"Request is already '{req.state}' — cannot act on it.")

        if action == "approve":
            req.action_approve()
        else:
            req.action_refuse()

        return _json_ok({
            "id": req.id,
            "employee": req.employee_id.name,
            "new_state": req.state,
        })

    @http.route(
        "/api/security/mobile/manager/guard-performance",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
        cors="*",
    )
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_guard_performance(self, **kw):
        """Guards with performance flags: ≥3 late arrivals or ≥2 AWOLs in the last 30 days,
        or >20 OT hours this month."""
        from datetime import timedelta
        today = date.today()
        thirty_ago = today - timedelta(days=30)
        month_start = today.replace(day=1)

        env = request.env
        records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id.attendance_date", ">=", thirty_ago),
            ("attendance_batch_id.attendance_date", "<=", today),
        ])

        by_emp = {}
        for rec in records:
            emp = rec.employee_id
            if not emp:
                continue
            eid = emp.id
            if eid not in by_emp:
                by_emp[eid] = {
                    "id": eid,
                    "name": emp.name,
                    "grade": emp.security_grade_id.name if emp.security_grade_id else None,
                    "late_count": 0,
                    "awol_count": 0,
                    "ot_hours": 0.0,
                }
            if rec.manual_presence == "present" and getattr(rec, "late_minutes", 0) > 0:
                by_emp[eid]["late_count"] += 1
            elif rec.manual_presence == "awol":
                by_emp[eid]["awol_count"] += 1
            batch = rec.attendance_batch_id
            if batch and hasattr(batch, "attendance_date") and batch.attendance_date >= month_start:
                by_emp[eid]["ot_hours"] += getattr(rec, "overtime_hours", 0) or 0

        flagged = []
        for emp_data in by_emp.values():
            flags = []
            if emp_data["late_count"] >= 3:
                flags.append({"type": "late", "label": f"{emp_data['late_count']} late arrivals in 30 days"})
            if emp_data["awol_count"] >= 2:
                flags.append({"type": "awol", "label": f"{emp_data['awol_count']} AWOLs in 30 days"})
            ot = round(emp_data["ot_hours"], 1)
            if ot > 20:
                flags.append({"type": "ot", "label": f"{ot} OT hours this month"})
            if not flags:
                continue
            flagged.append({
                "id": emp_data["id"],
                "name": emp_data["name"],
                "grade": emp_data["grade"],
                "late_count": emp_data["late_count"],
                "awol_count": emp_data["awol_count"],
                "ot_hours": ot,
                "flags": flags,
            })

        # Most severe first: AWOL > late > OT
        flagged.sort(key=lambda e: (e["awol_count"], e["late_count"], e["ot_hours"]), reverse=True)
        return _json_ok({"total_flagged": len(flagged), "guards": flagged})

    @http.route(
        "/api/security/mobile/manager/guard/review",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
        cors="*",
    )
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_guard_review(self, **kw):
        """Initiate a performance review — posts a chatter note on the employee record."""
        body = _parse_body()
        employee_id = body.get("employee_id")
        if not employee_id:
            return _json_err("employee_id is required.")
        note_text = body.get("note") or "Performance review initiated via DeployGuard."
        employee = request.env["hr.employee"].sudo().browse(int(employee_id))
        if not employee.exists():
            return _json_err(f"Employee {employee_id} not found.", status=404)
        employee.message_post(
            body=note_text,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=request.env.user.partner_id.id,
        )
        return _json_ok({"employee_id": employee.id, "employee_name": employee.name})

    @http.route(
        "/api/security/mobile/manager/ot-summary",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
        cors="*",
    )
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_ot_summary(self, **kw):
        """OT hours by site for the current month, plus projected month-end total."""
        import calendar
        today = date.today()
        month_start = today.replace(day=1)
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_elapsed = today.day

        env = request.env
        records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id.attendance_date", ">=", month_start),
            ("attendance_batch_id.attendance_date", "<=", today),
        ])

        total_ot = 0.0
        by_site = {}
        for rec in records:
            ot = getattr(rec, "overtime_hours", 0) or 0
            if not ot:
                continue
            total_ot += ot
            batch = rec.attendance_batch_id
            site = batch.site_id if batch else None
            sid = site.id if site else 0
            if sid not in by_site:
                by_site[sid] = {"site_id": sid, "site_name": site.name if site else "Unknown", "ot_hours": 0.0}
            by_site[sid]["ot_hours"] += ot

        sites = sorted(by_site.values(), key=lambda s: s["ot_hours"], reverse=True)
        for s in sites:
            s["ot_hours"] = round(s["ot_hours"], 1)

        projected = round(total_ot * days_in_month / days_elapsed, 1) if days_elapsed else 0
        return _json_ok({
            "month": str(month_start)[:7],
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
            "total_ot_hours": round(total_ot, 1),
            "projected_ot_hours": projected,
            "sites": sites,
        })

    @http.route(
        "/api/security/mobile/manager/unassigned-slots",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
        cors="*",
    )
    @require_group(GROUP_MANAGER, GROUP_OWNER)
    def manager_unassigned_slots(self, **kw):
        """Unassigned roster slots in the next 7 days, grouped by site."""
        from datetime import timedelta
        today = date.today()
        in_7_days = today + timedelta(days=7)
        env = request.env

        slots = env["security.roster.slot"].sudo().search([
            ("employee_id", "=", False),
            ("shift_date", ">=", today),
            ("shift_date", "<=", in_7_days),
        ])

        by_site = {}
        for slot in slots:
            site = getattr(slot.post_id, "site_id", None) if slot.post_id else None
            site_id = site.id if site else 0
            site_name = site.name if site else "Unknown Site"
            if site_id not in by_site:
                by_site[site_id] = {"site_id": site_id, "site_name": site_name, "count": 0, "slots": []}
            by_site[site_id]["count"] += 1
            by_site[site_id]["slots"].append({
                "slot_id": slot.id,
                "shift_date": str(slot.shift_date),
                "post": slot.post_id.name if slot.post_id else None,
                "shift": slot.shift_template_id.name if slot.shift_template_id else None,
            })

        return _json_ok({
            "total": len(slots),
            "sites": sorted(by_site.values(), key=lambda x: x["count"], reverse=True),
        })
