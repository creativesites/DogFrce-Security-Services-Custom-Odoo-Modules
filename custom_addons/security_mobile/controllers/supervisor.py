"""
Supervisor endpoints — multi-site posting sheet & presence marking.
"""
import logging
from datetime import date, datetime

from odoo import http
from odoo.http import request

from .main import (
    GROUP_SUPERVISOR,
    GROUP_MANAGER,
    GROUP_OWNER,
    _employee_for_user,
    _json_err,
    _json_ok,
    _parse_body,
    require_group,
)

_logger = logging.getLogger(__name__)


def _serialize_record(rec):
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
        "post_id": slot.post_id.id if slot and slot.post_id else None,
        "shift": slot.shift_template_id.name if slot else None,
        "shift_template_id": slot.shift_template_id.id if slot and slot.shift_template_id else None,
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
    site = batch.site_id
    return {
        "batch_id": batch.id,
        "batch_state": batch.state,
        "date": str(batch.attendance_date) if hasattr(batch, "attendance_date") else str(date.today()),
        "site": {"id": site.id, "name": site.name} if site else None,
        "client": {"id": site.partner_id.id, "name": site.partner_id.name} if site else None,
    }


def _site_day_summary(site, today, env):
    """Return a summary dict for one site's day — used by the multi-site list."""
    batch = env["security.attendance.batch"].sudo().search(
        [("attendance_date", "=", today), ("site_id", "=", site.id)], limit=1
    )
    if batch:
        records = env["security.attendance.record"].sudo().search(
            [("attendance_batch_id", "=", batch.id)]
        )
        total = len(records)
        present = len(records.filtered(lambda r: r.manual_presence == "present"))
        absent = len(records.filtered(lambda r: r.manual_presence == "absent"))
        awol = len(records.filtered(lambda r: r.manual_presence == "awol"))
        not_marked = total - present - absent - awol
        return {
            "site_id": site.id,
            "site_name": site.name,
            "client": site.partner_id.name if site.partner_id else None,
            "supervisor": site.supervisor_id.name if site.supervisor_id else None,
            "batch_id": batch.id,
            "batch_state": batch.state,
            "date": str(today),
            "total": total,
            "present": present,
            "absent": absent,
            "awol": awol,
            "not_marked": not_marked,
            "attendance_rate": round(present / total * 100, 1) if total else 0,
            "has_batch": True,
        }
    else:
        slots = env["security.roster.slot"].sudo().search([
            ("shift_date", "=", today),
            ("site_id", "=", site.id),
            ("state", "not in", ["cancelled"]),
        ])
        return {
            "site_id": site.id,
            "site_name": site.name,
            "client": site.partner_id.name if site.partner_id else None,
            "supervisor": site.supervisor_id.name if site.supervisor_id else None,
            "batch_id": None,
            "batch_state": "no_batch",
            "date": str(today),
            "total": len(slots),
            "present": 0,
            "absent": 0,
            "awol": 0,
            "not_marked": len(slots),
            "attendance_rate": 0,
            "has_batch": False,
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
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_today(self, **kw):
        """
        Without ?site_id: returns all active sites with today's batch summary
        (multi-site list for the supervisor to pick from).

        With ?site_id=X: returns the full posting sheet (batch + records) for
        that specific site.
        """
        today = date.today()
        env = request.env
        site_id_param = kw.get("site_id")

        if site_id_param:
            # ── Single-site posting sheet ──────────────────────────────────
            try:
                site_id = int(site_id_param)
            except (ValueError, TypeError):
                return _json_err("site_id must be an integer.")

            site = env["security.client.site"].sudo().browse(site_id)
            if not site.exists():
                return _json_err(f"Site {site_id} not found.", status=404)

            batch = env["security.attendance.batch"].sudo().search(
                [("attendance_date", "=", today), ("site_id", "=", site_id)], limit=1
            )

            if batch:
                data = _serialize_batch(batch)
                records = env["security.attendance.record"].sudo().search(
                    [("attendance_batch_id", "=", batch.id)],
                    order="employee_id asc",
                )
                data["slots"] = [_serialize_record(r) for r in records]
                return _json_ok(data)
            else:
                # No batch yet — return roster slots for this site
                slots = env["security.roster.slot"].sudo().search(
                    [
                        ("shift_date", "=", today),
                        ("site_id", "=", site_id),
                        ("state", "not in", ["cancelled"]),
                    ],
                    order="shift_template_id, post_id",
                )
                return _json_ok({
                    "date": str(today),
                    "has_batch": False,
                    "site": {"id": site.id, "name": site.name},
                    "client": {"id": site.partner_id.id, "name": site.partner_id.name} if site.partner_id else None,
                    "roster_slots": [
                        {
                            "slot_id": s.id,
                            "guard": {
                                "id": s.employee_id.id if s.employee_id else None,
                                "name": s.employee_id.name if s.employee_id else "Unassigned",
                                "grade": s.employee_id.security_grade_id.name
                                if s.employee_id and s.employee_id.security_grade_id else None,
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

        # ── All-sites summary (no site_id) ────────────────────────────────
        sites = env["security.client.site"].sudo().search([("active", "=", True)])
        summaries = [_site_day_summary(site, today, env) for site in sites]
        # Put sites with active batches first, then by name
        summaries.sort(key=lambda s: (0 if s["has_batch"] else 1, s["site_name"]))
        return _json_ok({"date": str(today), "sites": summaries})

    # ── POST /api/security/mobile/supervisor/mark ──────────────────────────
    @http.route(
        "/api/security/mobile/supervisor/mark",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_mark(self, **kw):
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
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_checkin(self, **kw):
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
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_batch_submit(self, **kw):
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

        try:
            if hasattr(batch, "action_capture"):
                batch.action_capture()
            else:
                batch.write({"state": "captured"})
        except Exception as exc:
            _logger.exception("Batch submit failed for batch %s", batch_id)
            return _json_err(str(exc), status=500)

        return _json_ok({"batch_id": batch.id, "new_state": batch.state})

    # ── GET /api/security/mobile/supervisor/site/<id>/assignable ─────────
    @http.route(
        "/api/security/mobile/supervisor/site/<int:site_id>/assignable",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_site_assignable(self, site_id, **kw):
        """
        Returns the data needed to populate the 'Assign Guard' modal:
          - guards: all active security guards NOT already in today's batch for this site
          - posts: posts linked to this site
          - shifts: all active shift templates
        """
        today = date.today()
        env = request.env

        site = env["security.client.site"].sudo().browse(site_id)
        if not site.exists():
            return _json_err(f"Site {site_id} not found.", status=404)

        # Find guards already assigned today at this site
        batch = env["security.attendance.batch"].sudo().search(
            [("attendance_date", "=", today), ("site_id", "=", site_id)], limit=1
        )
        assigned_ids = set()
        if batch:
            recs = env["security.attendance.record"].sudo().search(
                [("attendance_batch_id", "=", batch.id)]
            )
            assigned_ids = {r.employee_id.id for r in recs}

        # Available guards
        all_guards = env["hr.employee"].sudo().search([
            ("security_guard", "=", True),
            ("active", "=", True),
        ])
        guards = [
            {
                "id": g.id,
                "name": g.name,
                "grade": g.security_grade_id.name if g.security_grade_id else None,
            }
            for g in all_guards
            if g.id not in assigned_ids
        ]

        # Posts for this site
        posts = env["security.post"].sudo().search([
            ("site_id", "=", site_id),
            ("active", "=", True),
        ])
        post_list = [{"id": p.id, "name": p.name} for p in posts]

        # All active shift templates
        shifts = env["security.shift.template"].sudo().search([("active", "=", True)])
        shift_list = [
            {
                "id": s.id,
                "name": s.name,
                "start_hour": s.start_hour,
                "end_hour": s.end_hour,
                "duration_hours": s.duration_hours,
            }
            for s in shifts
        ]

        return _json_ok({
            "site_id": site_id,
            "site_name": site.name,
            "guards": guards,
            "posts": post_list,
            "shifts": shift_list,
            "has_batch": bool(batch),
            "batch_state": batch.state if batch else None,
        })

    # ── POST /api/security/mobile/supervisor/site/<id>/assign ────────────
    @http.route(
        "/api/security/mobile/supervisor/site/<int:site_id>/assign",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_site_assign(self, site_id, **kw):
        """
        Assigns a guard to a site for today by:
          1. Creating a security.roster.slot (state=assigned, shift_date=today)
          2. Getting or creating today's security.attendance.batch for the site
          3. Creating the security.attendance.record linked to both
          4. Optionally marking the guard as present immediately (mark_present=true)
        """
        body = _parse_body()
        employee_id = body.get("employee_id")
        post_id = body.get("post_id")
        shift_template_id = body.get("shift_template_id")
        mark_present = bool(body.get("mark_present", False))

        if not employee_id:
            return _json_err("employee_id is required.")
        if not post_id:
            return _json_err("post_id is required.")
        if not shift_template_id:
            return _json_err("shift_template_id is required.")

        today = date.today()
        env = request.env

        site = env["security.client.site"].sudo().browse(site_id)
        if not site.exists():
            return _json_err(f"Site {site_id} not found.", status=404)

        employee = env["hr.employee"].sudo().browse(int(employee_id))
        if not employee.exists():
            return _json_err("Guard not found.", status=404)

        post = env["security.post"].sudo().browse(int(post_id))
        if not post.exists():
            return _json_err("Post not found.", status=404)

        shift = env["security.shift.template"].sudo().browse(int(shift_template_id))
        if not shift.exists():
            return _json_err("Shift template not found.", status=404)

        # Get or create today's batch
        batch = env["security.attendance.batch"].sudo().search(
            [("attendance_date", "=", today), ("site_id", "=", site_id)], limit=1
        )
        if not batch:
            batch = env["security.attendance.batch"].sudo().create({
                "site_id": site_id,
                "partner_id": site.partner_id.id if site.partner_id else False,
                "attendance_date": today,
                "state": "draft",
            })
        elif batch.state not in ("draft",):
            return _json_err(
                f"Cannot add guards — posting sheet is already '{batch.state}'."
            )

        # Check for duplicate assignment
        duplicate = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id", "=", batch.id),
            ("employee_id", "=", int(employee_id)),
        ], limit=1)
        if duplicate:
            return _json_err(f"{employee.name} is already on the posting sheet for today.")

        # 1. Create roster slot
        slot = env["security.roster.slot"].sudo().create({
            "shift_date": today,
            "post_id": int(post_id),
            "shift_template_id": int(shift_template_id),
            "employee_id": int(employee_id),
            "state": "assigned",
        })

        # 2. Create attendance record
        now = datetime.utcnow()
        record_vals = {
            "attendance_batch_id": batch.id,
            "roster_slot_id": slot.id,
            "manual_presence": "present" if mark_present else "not_marked",
        }
        if mark_present:
            record_vals["check_in"] = now

        record = env["security.attendance.record"].sudo().create(record_vals)

        return _json_ok({
            "record_id": record.id,
            "batch_id": batch.id,
            "slot_id": slot.id,
            "guard": {"id": employee.id, "name": employee.name},
            "post": post.name,
            "shift": shift.name,
            "manual_presence": record.manual_presence,
            "check_in": now.isoformat() if mark_present else None,
        })

    # ── GET /api/security/mobile/supervisor/guard/<id>/profile ─────────────
    @http.route(
        "/api/security/mobile/supervisor/guard/<int:guard_id>/profile",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_guard_profile(self, guard_id, **kw):
        """
        Mini guard profile for in-context decision making.
        Returns reliability score, grade, 7-day attendance history,
        open incident count, and active leave status.
        """
        from datetime import timedelta
        env = request.env
        today = date.today()

        guard = env["hr.employee"].sudo().browse(guard_id)
        if not guard.exists():
            return _json_err(f"Guard {guard_id} not found.", status=404)

        # 7-day attendance history
        week_ago = today - timedelta(days=6)
        records = env["security.attendance.record"].sudo().search([
            ("employee_id", "=", guard_id),
            ("attendance_batch_id.attendance_date", ">=", week_ago),
            ("attendance_batch_id.attendance_date", "<=", today),
        ])
        record_by_date = {
            str(rec.attendance_batch_id.attendance_date): rec.manual_presence
            for rec in records
        }
        attendance_7d = []
        for i in range(7):
            d = str(week_ago + timedelta(days=i))
            attendance_7d.append({"date": d, "presence": record_by_date.get(d, "no_shift")})

        # Open incidents
        open_incidents = env["security.incident"].sudo().search_count([
            ("employee_id", "=", guard_id),
            ("state", "=", "draft"),
        ])

        # Active approved leave today
        active_leave = None
        if "security.leave.request" in env:
            leave = env["security.leave.request"].sudo().search([
                ("employee_id", "=", guard_id),
                ("state", "=", "approved"),
                ("date_from", "<=", today),
                ("date_to", ">=", today),
            ], limit=1)
            if leave:
                active_leave = {
                    "leave_type": leave.leave_type_id.name,
                    "date_from": str(leave.date_from),
                    "date_to": str(leave.date_to),
                    "requested_days": leave.requested_days,
                }

        return _json_ok({
            "id": guard.id,
            "name": guard.name,
            "grade": guard.security_grade_id.name if guard.security_grade_id else None,
            "reliability_score": guard.security_reliability_score
            if hasattr(guard, "security_reliability_score") else None,
            "mobile_phone": guard.mobile_phone or None,
            "site": guard.security_current_site_id.name
            if hasattr(guard, "security_current_site_id") and guard.security_current_site_id else None,
            "attendance_7d": attendance_7d,
            "open_incidents": open_incidents,
            "active_leave": active_leave,
        })

    # ── POST /api/security/mobile/supervisor/site/<id>/bulk-mark ───────────
    @http.route(
        "/api/security/mobile/supervisor/site/<int:site_id>/bulk-mark",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_bulk_mark_present(self, site_id, **kw):
        """Mark all not_marked attendance records in today's batch as present."""
        today = date.today()
        env = request.env

        batch = env["security.attendance.batch"].sudo().search(
            [("attendance_date", "=", today), ("site_id", "=", site_id)], limit=1
        )
        if not batch:
            return _json_err("No active posting sheet found for today.", status=404)

        records = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id", "=", batch.id),
            ("manual_presence", "=", "not_marked"),
        ])

        now = datetime.utcnow()
        updated = 0
        for rec in records:
            rec.write({
                "manual_presence": "present",
                "check_in": now,
            })
            updated += 1

        return _json_ok({"updated": updated, "batch_id": batch.id})

    # ── GET /api/security/mobile/supervisor/incident-types ─────────────────
    @http.route(
        "/api/security/mobile/supervisor/incident-types",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_incident_types(self, **kw):
        """Return all active incident types for the mobile incident logger."""
        types = request.env["security.incident.type"].sudo().search([("active", "=", True)])
        return _json_ok([
            {
                "id": t.id,
                "name": t.name,
                "severity": t.severity,
                "deduction_amount": t.deduction_amount,
            }
            for t in types
        ])

    # ── POST /api/security/mobile/supervisor/incident ──────────────────────
    @http.route(
        "/api/security/mobile/supervisor/incident",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_log_incident(self, **kw):
        """
        Log a security incident from the mobile app.
        Body: employee_id, incident_type_id, note? (incident_date defaults to today)
        """
        body = _parse_body()
        employee_id = body.get("employee_id")
        incident_type_id = body.get("incident_type_id")
        note = body.get("note", "")

        if not employee_id:
            return _json_err("employee_id is required.")
        if not incident_type_id:
            return _json_err("incident_type_id is required.")

        env = request.env

        employee = env["hr.employee"].sudo().browse(int(employee_id))
        if not employee.exists():
            return _json_err("Guard not found.", status=404)

        inc_type = env["security.incident.type"].sudo().browse(int(incident_type_id))
        if not inc_type.exists():
            return _json_err("Incident type not found.", status=404)

        incident = env["security.incident"].sudo().create({
            "employee_id": int(employee_id),
            "incident_type_id": int(incident_type_id),
            "incident_date": date.today(),
            "note": note,
            "state": "draft",
        })

        return _json_ok({
            "incident_id": incident.id,
            "guard": employee.name,
            "incident_type": inc_type.name,
            "severity": inc_type.severity,
            "date": str(date.today()),
            "state": "draft",
        })

    # ── POST /api/security/mobile/supervisor/site/<id>/reassign ────────────
    @http.route(
        "/api/security/mobile/supervisor/site/<int:site_id>/reassign",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_reassign_guard(self, site_id, **kw):
        """
        Emergency guard reassignment.
        Marks the released guard's record as absent and creates a new slot +
        attendance record for the replacement.  Bypasses batch.state check
        (unlike the normal assign flow) because this is an emergency action.
        Body: record_id, employee_id, post_id, shift_template_id, mark_present?
        """
        body = _parse_body()
        record_id = body.get("record_id")
        employee_id = body.get("employee_id")
        post_id = body.get("post_id")
        shift_template_id = body.get("shift_template_id")
        mark_present = bool(body.get("mark_present", True))

        if not record_id:
            return _json_err("record_id is required.")
        if not employee_id:
            return _json_err("employee_id is required.")
        if not post_id:
            return _json_err("post_id is required.")
        if not shift_template_id:
            return _json_err("shift_template_id is required.")

        env = request.env

        old_record = env["security.attendance.record"].sudo().browse(int(record_id))
        if not old_record.exists():
            return _json_err(f"Attendance record {record_id} not found.", status=404)

        batch = old_record.attendance_batch_id
        if not batch or not batch.exists():
            return _json_err("Attendance batch not found for this record.", status=404)

        employee = env["hr.employee"].sudo().browse(int(employee_id))
        if not employee.exists():
            return _json_err("Replacement guard not found.", status=404)

        post = env["security.post"].sudo().browse(int(post_id))
        if not post.exists():
            return _json_err("Post not found.", status=404)

        shift = env["security.shift.template"].sudo().browse(int(shift_template_id))
        if not shift.exists():
            return _json_err("Shift template not found.", status=404)

        # Guard against double-assignment
        duplicate = env["security.attendance.record"].sudo().search([
            ("attendance_batch_id", "=", batch.id),
            ("employee_id", "=", int(employee_id)),
        ], limit=1)
        if duplicate:
            return _json_err(f"{employee.name} is already on the posting sheet for today.")

        released_name = old_record.employee_id.name if old_record.employee_id else "Unknown"

        # 1. Release the AWOL/absent guard
        old_record.write({
            "manual_presence": "absent",
            "override_reason": f"Released — reassigned to {employee.name}",
        })

        today = date.today()

        # 2. Create new roster slot for replacement
        slot = env["security.roster.slot"].sudo().create({
            "shift_date": today,
            "post_id": int(post_id),
            "shift_template_id": int(shift_template_id),
            "employee_id": int(employee_id),
            "state": "assigned",
        })

        # 3. Create new attendance record on the same batch
        now = datetime.utcnow()
        record_vals = {
            "attendance_batch_id": batch.id,
            "roster_slot_id": slot.id,
            "manual_presence": "present" if mark_present else "not_marked",
        }
        if mark_present:
            record_vals["check_in"] = now

        new_record = env["security.attendance.record"].sudo().create(record_vals)

        return _json_ok({
            "released_guard": released_name,
            "new_record_id": new_record.id,
            "batch_id": batch.id,
            "slot_id": slot.id,
            "guard": {"id": employee.id, "name": employee.name},
            "post": post.name,
            "shift": shift.name,
            "manual_presence": new_record.manual_presence,
            "check_in": now.isoformat() if mark_present else None,
        })

    # ── GET /api/security/mobile/supervisor/history ────────────────────────
    @http.route(
        "/api/security/mobile/supervisor/history",
        auth="user",
        methods=["GET"],
        type="http",
        csrf=False,
    )
    @require_group(GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)
    def supervisor_history(self, **kw):
        """Paginated posting sheet history across all sites."""
        limit = min(int(kw.get("limit", 20)), 100)
        offset = int(kw.get("offset", 0))
        site_id_param = kw.get("site_id")

        env = request.env
        domain = []
        if site_id_param:
            domain.append(("site_id", "=", int(site_id_param)))

        batches = env["security.attendance.batch"].sudo().search(
            domain,
            order="attendance_date desc",
            limit=limit,
            offset=offset,
        )
        total = env["security.attendance.batch"].sudo().search_count(domain)

        results = []
        for batch in batches:
            records = env["security.attendance.record"].sudo().search(
                [("attendance_batch_id", "=", batch.id)]
            )
            present = len(records.filtered(lambda r: r.manual_presence == "present"))
            late = len(records.filtered(
                lambda r: r.manual_presence == "present"
                and getattr(r, "late_minutes", 0) > 0
            ))
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
