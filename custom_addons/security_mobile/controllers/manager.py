"""
Manager endpoints — multi-site dashboard & overtime approval.
"""
import logging
from datetime import date

from odoo import http
from odoo.http import request

from .main import (
    GROUP_MANAGER,
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
                auth="user", methods=["GET"], type="http", csrf=False)
    @require_group(GROUP_MANAGER)
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
                auth="user", methods=["GET"], type="http", csrf=False)
    @require_group(GROUP_MANAGER)
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

    @http.route("/api/security/mobile/manager/overtime/approve",
                auth="user", methods=["POST"], type="http", csrf=False)
    @require_group(GROUP_MANAGER)
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
