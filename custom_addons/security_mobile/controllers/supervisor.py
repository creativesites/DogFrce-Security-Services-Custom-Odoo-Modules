"""
Supervisor endpoints — posting sheet & presence marking.
"""
import logging
from datetime import date, datetime

from odoo import http
from odoo.http import request

from .main import (
    GROUP_SUPERVISOR,
    _employee_for_user,
    _json_err,
    _json_ok,
    _parse_body,
    require_group,
)

_logger = logging.getLogger(__name__)


def _serialize_record(rec):
    """Serialize one security.attendance.record to a dict for the API."""
    slot = rec.roster_slot_id
    employee = rec.employee_id
    grade = employee.security_grade_id.name if employee.security_grade_id else None

    def _fmt_dt(dt_val):
        if not dt_val:
            return None
        if isinstance(dt_val, datetime):
            return dt_val.isoformat()
        return str(dt_val)

    return {
        "record_id": rec.id,
        "slot_id": slot.id if slot else None,
        "guard": {
            "id": employee.id,
            "name": employee.name,
            "grade": grade,
        },
        "post": slot.post_id.name if slot else None,
        "shift": slot.shift_template_id.name if slot else None,
        "shift_start": slot.shift_template_id.start_hour if slot else None,
        "shift_end": slot.shift_template_id.end_hour if slot else None,
        "status": rec.status if hasattr(rec, "status") else "scheduled",
        "manual_presence": rec.manual_presence or "not_marked",
        "check_in": _fmt_dt(rec.check_in),
        "check_out": _fmt_dt(rec.check_out),
        "late_minutes": rec.late_minutes if hasattr(rec, "late_minutes") else 0,
        "overtime_hours": rec.overtime_hours if hasattr(rec, "overtime_hours") else 0,
        "override_reason": rec.override_reason or None,
    }


def _serialize_batch(batch):
    """Serialize one security.attendance.batch header."""
    site = batch.site_id
    return {
        "batch_id": batch.id,
        "batch_state": batch.state,
        "date": str(batch.attendance_date) if hasattr(batch, "attendance_date") else str(date.today()),
        "site": {"id": site.id, "name": site.name} if site else None,
        "client": {"id": site.partner_id.id, "name": site.partner_id.name} if site else None,
    }


class SupervisorController(http.Controller):

    # ── GET /api/security/mobile/supervisor/today ──────────────────────────
    @http.route(
        "/api/security/mobile/supervisor/today",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR)
    def supervisor_today(self, **kw):
        """
        Return today's posting sheet for the logged-in supervisor.

        Strategy:
        1. Find all sites where supervisor_id.user_id == current user.
        2. Find today's attendance batches for those sites.
        3. If no batch exists yet, fall back to today's roster slots (so the
           supervisor can start a new capture).
        """
        today = date.today()
        env = request.env
        employee = _employee_for_user()

        if not employee:
            return _json_err("No employee record linked to your user account.")

        # Sites supervised by this employee
        sites = env["security.client.site"].sudo().search(
            [("supervisor_id", "=", employee.id), ("active", "=", True)]
        )

        # Attendance batches for today
        batches = env["security.attendance.batch"].sudo().search(
            [
                ("attendance_date", "=", today),
                ("site_id", "in", sites.ids),
            ]
        )

        # If no batch found (shift has not started yet), look for one by captured_by
        if not batches:
            batches = env["security.attendance.batch"].sudo().search(
                [
                    ("attendance_date", "=", today),
                    ("captured_by_id", "=", request.env.user.id),
                ]
            )

        results = []
        for batch in batches:
            data = _serialize_batch(batch)
            records = env["security.attendance.record"].sudo().search(
                [("batch_id", "=", batch.id)],
                order="employee_id asc",
            )
            data["slots"] = [_serialize_record(r) for r in records]
            results.append(data)

        # Fallback: return unlinked roster slots so supervisor can create batch
        if not results:
            slots = env["security.roster.slot"].sudo().search(
                [
                    ("shift_date", "=", today),
                    ("site_id", "in", sites.ids),
                    ("state", "not in", ["cancelled"]),
                ],
                order="shift_template_id, post_id",
            )
            return _json_ok({
                "date": str(today),
                "has_batch": False,
                "roster_slots": [
                    {
                        "slot_id": s.id,
                        "guard": {
                            "id": s.employee_id.id if s.employee_id else None,
                            "name": s.employee_id.name if s.employee_id else "Unassigned",
                            "grade": s.employee_id.security_grade_id.name if s.employee_id and s.employee_id.security_grade_id else None,
                        },
                        "post": s.post_id.name,
                        "site": {"id": s.site_id.id, "name": s.site_id.name} if s.site_id else None,
                        "shift": s.shift_template_id.name,
                        "shift_start": s.shift_template_id.start_hour,
                        "shift_end": s.shift_template_id.end_hour,
                        "state": s.state,
                    }
                    for s in slots
                ],
            })

        return _json_ok(results if len(results) > 1 else results[0])

    # ── POST /api/security/mobile/supervisor/mark ──────────────────────────
    @http.route(
        "/api/security/mobile/supervisor/mark",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR)
    def supervisor_mark(self, **kw):
        """
        Mark or update presence for a single attendance record.

        Body: { record_id, manual_presence, check_in?, check_out?, override_reason? }
        """
        body = _parse_body()
        record_id = body.get("record_id")
        manual_presence = body.get("manual_presence")

        if not record_id:
            return _json_err("record_id is required.")
        if manual_presence and manual_presence not in ("present", "absent", "awol", "not_marked"):
            return _json_err("manual_presence must be present | absent | awol | not_marked.")

        record = request.env["security.attendance.record"].sudo().browse(int(record_id))
        if not record.exists():
            return _json_err(f"Attendance record {record_id} not found.", status=404)

        vals = {}
        if manual_presence:
            vals["manual_presence"] = manual_presence

        raw_in = body.get("check_in")
        raw_out = body.get("check_out")
        if raw_in:
            try:
                vals["check_in"] = datetime.fromisoformat(raw_in)
            except ValueError:
                return _json_err(f"Invalid check_in datetime: {raw_in}")
        if raw_out:
            try:
                vals["check_out"] = datetime.fromisoformat(raw_out)
            except ValueError:
                return _json_err(f"Invalid check_out datetime: {raw_out}")
        if body.get("override_reason"):
            vals["override_reason"] = body["override_reason"]

        if not vals:
            return _json_err("Nothing to update — provide at least one field.")

        record.write(vals)
        return _json_ok(_serialize_record(record))

    # ── POST /api/security/mobile/supervisor/checkin ───────────────────────
    @http.route(
        "/api/security/mobile/supervisor/checkin",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR)
    def supervisor_checkin(self, **kw):
        """
        Quick check-in / check-out using NOW as the timestamp.

        Body: { record_id, action: "check_in" | "check_out" }
        """
        body = _parse_body()
        record_id = body.get("record_id")
        action = body.get("action")

        if not record_id:
            return _json_err("record_id is required.")
        if action not in ("check_in", "check_out"):
            return _json_err("action must be check_in or check_out.")

        record = request.env["security.attendance.record"].sudo().browse(int(record_id))
        if not record.exists():
            return _json_err(f"Attendance record {record_id} not found.", status=404)

        now = datetime.utcnow()
        vals = {action: now}
        if action == "check_in":
            vals["manual_presence"] = "present"

        record.write(vals)
        return _json_ok(_serialize_record(record))

    # ── POST /api/security/mobile/supervisor/batch/submit ─────────────────
    @http.route(
        "/api/security/mobile/supervisor/batch/submit",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR)
    def supervisor_batch_submit(self, **kw):
        """
        Submit (capture) a posting sheet batch.

        Body: { batch_id }
        """
        body = _parse_body()
        batch_id = body.get("batch_id")
        if not batch_id:
            return _json_err("batch_id is required.")

        batch = request.env["security.attendance.batch"].sudo().browse(int(batch_id))
        if not batch.exists():
            return _json_err(f"Batch {batch_id} not found.", status=404)

        if batch.state not in ("draft",):
            return _json_err(
                f"Batch is already in state '{batch.state}' and cannot be submitted again."
            )

        # Call Odoo action to capture the batch
        try:
            if hasattr(batch, "action_capture"):
                batch.action_capture()
            else:
                batch.write({"state": "captured"})
        except Exception as exc:
            _logger.exception("Batch submit failed for batch %s", batch_id)
            return _json_err(str(exc), status=500)

        return _json_ok({"batch_id": batch.id, "new_state": batch.state})

    # ── GET /api/security/mobile/supervisor/history ────────────────────────
    @http.route(
        "/api/security/mobile/supervisor/history",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR)
    def supervisor_history(self, **kw):
        """
        Return past posting sheet batches for the logged-in supervisor.

        Query params:
          ?limit=20  (default 20)
          ?offset=0  (default 0)
        """
        limit = min(int(kw.get("limit", 20)), 100)
        offset = int(kw.get("offset", 0))

        env = request.env
        employee = _employee_for_user()
        if not employee:
            return _json_err("No employee record linked to your user account.")

        sites = env["security.client.site"].sudo().search(
            [("supervisor_id", "=", employee.id), ("active", "=", True)]
        )

        batches = env["security.attendance.batch"].sudo().search(
            [("site_id", "in", sites.ids)],
            order="attendance_date desc",
            limit=limit,
            offset=offset,
        )

        total = env["security.attendance.batch"].sudo().search_count(
            [("site_id", "in", sites.ids)]
        )

        results = []
        for batch in batches:
            records = env["security.attendance.record"].sudo().search(
                [("batch_id", "=", batch.id)]
            )
            present = len(records.filtered(lambda r: r.manual_presence == "present"))
            late = len(records.filtered(lambda r: r.manual_presence == "present" and r.late_minutes > 0))
            absent = len(records.filtered(lambda r: r.manual_presence == "absent"))
            awol = len(records.filtered(lambda r: r.manual_presence == "awol"))
            total_recs = len(records)

            site = batch.site_id
            results.append({
                "batch_id": batch.id,
                "date": str(batch.attendance_date),
                "site": {"id": site.id, "name": site.name} if site else None,
                "state": batch.state,
                "summary": {
                    "total": total_recs,
                    "present": present,
                    "late": late,
                    "absent": absent,
                    "awol": awol,
                    "attendance_rate": round(present / total_recs * 100, 1) if total_recs else 0,
                },
            })

        return _json_ok({
            "batches": results,
            "pagination": {"limit": limit, "offset": offset, "total": total},
        })
