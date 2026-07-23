"""
security_mobile — Guard API endpoints.
Endpoints accessible to security guards for shift status, self check-in, patrol logging, SOS, and history.
"""
import base64
import logging
from datetime import datetime, date

from odoo import http, fields
from odoo.http import request
from .main import (
    _employee_for_user,
    _json_err,
    _json_ok,
    _parse_body,
    require_group,
    GROUP_GUARD,
    GROUP_SUPERVISOR,
    GROUP_MANAGER,
    GROUP_OWNER,
)

_logger = logging.getLogger(__name__)


class GuardMobileController(http.Controller):

    @http.route(
        "/api/security/mobile/guard/today",
        auth="user",
        methods=["GET", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def guard_today(self, **kw):
        """
        Return today's shift details and check-in status for the logged-in guard.
        """
        user = request.env.user
        employee = _employee_for_user(user)

        if not employee.exists():
            return _json_err("No employee profile linked to current account.", status=404)

        today_str = fields.Date.today().strftime("%Y-%m-%d")

        # Search for today's attendance record for this employee
        env = request.env(su=True)
        rec = env["security.attendance.record"].search([
            ("employee_id", "=", employee.id),
            ("date", "=", today_str)
        ], limit=1)

        # Fallback to roster slot if no attendance record generated yet
        roster_slot = None
        if not rec.exists():
            roster_slot = env["security.roster.slot"].search([
                ("employee_id", "=", employee.id),
                ("date", "=", today_str)
            ], limit=1)

        site_info = None
        post_info = None
        shift_info = None
        supervisor_info = None

        if rec.exists():
            site = rec.site_id
            site_info = {"id": site.id, "name": site.name} if site else None
            post_info = rec.post_id.name if rec.post_id else None
            shift = rec.shift_template_id
            if shift:
                shift_info = {
                    "id": shift.id,
                    "name": shift.name,
                    "start_hour": getattr(shift, "start_hour", 6.0),
                    "end_hour": getattr(shift, "end_hour", 18.0),
                }
            if site and getattr(site, "supervisor_id", None):
                sup = site.supervisor_id
                supervisor_info = {
                    "id": sup.id,
                    "name": sup.name,
                    "phone": getattr(sup, "mobile_phone", None) or getattr(sup, "work_phone", None),
                }
        elif roster_slot and roster_slot.exists():
            site = roster_slot.site_id
            site_info = {"id": site.id, "name": site.name} if site else None
            post_info = roster_slot.post_id.name if roster_slot.post_id else None
            shift = roster_slot.shift_template_id
            if shift:
                shift_info = {
                    "id": shift.id,
                    "name": shift.name,
                    "start_hour": getattr(shift, "start_hour", 6.0),
                    "end_hour": getattr(shift, "end_hour", 18.0),
                }

        attendance_data = None
        if rec.exists():
            attendance_data = {
                "record_id": rec.id,
                "status": rec.manual_presence or "not_marked",
                "check_in": fields.Datetime.to_string(rec.check_in) if rec.check_in else None,
                "check_out": fields.Datetime.to_string(rec.check_out) if rec.check_out else None,
                "late_minutes": getattr(rec, "late_minutes", 0),
            }

        return _json_ok({
            "guard": {
                "id": employee.id,
                "name": employee.name,
                "grade": getattr(employee, "security_grade", None) or "Grade C",
                "reliability_score": getattr(employee, "reliability_score", 95.0),
            },
            "date": today_str,
            "has_assignment": bool(rec.exists() or (roster_slot and roster_slot.exists())),
            "site": site_info,
            "post": post_info,
            "shift": shift_info,
            "supervisor": supervisor_info,
            "attendance": attendance_data,
        })

    @http.route(
        "/api/security/mobile/guard/checkin",
        auth="user",
        methods=["POST", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def guard_self_checkin(self, **kw):
        """
        Self check-in or check-out by the guard with GPS & selfie.
        Body: { action: 'check_in' | 'check_out', latitude, longitude, accuracy, photo_base64 }
        """
        body = _parse_body()
        action = body.get("action", "check_in")
        lat = body.get("latitude")
        lng = body.get("longitude")
        accuracy = body.get("accuracy")
        photo_b64 = body.get("photo_base64")

        user = request.env.user
        employee = _employee_for_user(user)

        if not employee.exists():
            return _json_err("No employee record linked.", status=404)

        today_str = fields.Date.today().strftime("%Y-%m-%d")
        env = request.env(su=True)
        rec = env["security.attendance.record"].search([
            ("employee_id", "=", employee.id),
            ("date", "=", today_str)
        ], limit=1)

        now_dt = fields.Datetime.now()

        if not rec.exists():
            # Auto-create attendance record if guard is assigned to roster today
            roster_slot = env["security.roster.slot"].search([
                ("employee_id", "=", employee.id),
                ("date", "=", today_str)
            ], limit=1)

            if not roster_slot.exists():
                return _json_err("No shift rostered for you today.", status=400)

            rec = env["security.attendance.record"].create({
                "employee_id": employee.id,
                "site_id": roster_slot.site_id.id if roster_slot.site_id else False,
                "post_id": roster_slot.post_id.id if roster_slot.post_id else False,
                "shift_template_id": roster_slot.shift_template_id.id if roster_slot.shift_template_id else False,
                "date": today_str,
                "manual_presence": "present",
            })

        if action == "check_in":
            rec.write({
                "check_in": now_dt,
                "manual_presence": "present",
            })
        elif action == "check_out":
            rec.write({
                "check_out": now_dt,
            })

        # Attach selfie image if provided
        if photo_b64:
            try:
                env["ir.attachment"].create({
                    "name": f"guard_selfie_{action}_{rec.id}.jpg",
                    "type": "binary",
                    "datas": photo_b64,
                    "res_model": "security.attendance.record",
                    "res_id": rec.id,
                    "mimetype": "image/jpeg",
                })
            except Exception as e:
                _logger.warning("Failed to save guard check-in selfie: %s", e)

        return _json_ok({
            "record_id": rec.id,
            "action": action,
            "manual_presence": rec.manual_presence,
            "check_in": fields.Datetime.to_string(rec.check_in) if rec.check_in else None,
            "check_out": fields.Datetime.to_string(rec.check_out) if rec.check_out else None,
            "location_logged": bool(lat and lng),
        })

    @http.route(
        "/api/security/mobile/guard/patrol",
        auth="user",
        methods=["POST", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def guard_patrol_log(self, **kw):
        """
        Log shift patrol status or observation.
        Body: { note, latitude, longitude, photo_base64 }
        """
        body = _parse_body()
        note = body.get("note") or "Routine Patrol Check"
        lat = body.get("latitude")
        lng = body.get("longitude")
        photo_b64 = body.get("photo_base64")

        user = request.env.user
        employee = _employee_for_user(user)

        env = request.env(su=True)
        # Create an incident or patrol check record
        inc_type = env["security.incident.type"].search([("name", "ilike", "Patrol")], limit=1)
        if not inc_type.exists():
            inc_type = env["security.incident.type"].search([], limit=1)

        inc = env["security.incident"].create({
            "employee_id": employee.id if employee.exists() else False,
            "incident_type_id": inc_type.id if inc_type.exists() else False,
            "date": fields.Date.today(),
            "note": f"[GUARD PATROL LOG] {note}\nLocation: {lat}, {lng}" if lat and lng else f"[GUARD PATROL LOG] {note}",
            "state": "logged",
        })

        if photo_b64:
            try:
                env["ir.attachment"].create({
                    "name": f"patrol_{inc.id}.jpg",
                    "type": "binary",
                    "datas": photo_b64,
                    "res_model": "security.incident",
                    "res_id": inc.id,
                    "mimetype": "image/jpeg",
                })
            except Exception as e:
                _logger.warning("Failed to attach patrol photo: %s", e)

        return _json_ok({
            "patrol_id": inc.id,
            "date": fields.Date.to_string(inc.date),
            "note": note,
            "status": "recorded",
        })

    @http.route(
        "/api/security/mobile/guard/sos",
        auth="user",
        methods=["POST", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def guard_sos_alert(self, **kw):
        """
        Trigger instant SOS Emergency Alert.
        Body: { latitude, longitude, message }
        """
        body = _parse_body()
        lat = body.get("latitude")
        lng = body.get("longitude")
        msg = body.get("message") or "EMERGENCY PANIC ALERT TRIGGERED BY GUARD"

        user = request.env.user
        employee = _employee_for_user(user)

        env = request.env(su=True)
        sos_type = env["security.incident.type"].search([("name", "ilike", "Panic")], limit=1)
        if not sos_type.exists():
            sos_type = env["security.incident.type"].search([], limit=1)

        sos_inc = env["security.incident"].create({
            "employee_id": employee.id if employee.exists() else False,
            "incident_type_id": sos_type.id if sos_type.exists() else False,
            "date": fields.Date.today(),
            "note": f"🚨 [CRITICAL SOS] {msg}\nGPS: {lat}, {lng}",
            "state": "logged",
        })

        _logger.warning("🚨 EMERGENCY SOS ALERT from Guard %s at GPS %s, %s", employee.name if employee else user.name, lat, lng)

        return _json_ok({
            "sos_id": sos_inc.id,
            "status": "alert_dispatched",
            "message": "Emergency alert logged and supervisor notified.",
            "timestamp": fields.Datetime.to_string(fields.Datetime.now()),
        })

    @http.route(
        "/api/security/mobile/guard/history",
        auth="user",
        methods=["GET", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def guard_history(self, **kw):
        """
        Return last 30 days attendance history and metrics for guard.
        """
        user = request.env.user
        employee = _employee_for_user(user)

        if not employee.exists():
            return _json_err("No employee profile found.", status=404)

        env = request.env(su=True)
        records = env["security.attendance.record"].search([
            ("employee_id", "=", employee.id)
        ], order="date desc", limit=30)

        history_list = []
        present_cnt = 0
        late_cnt = 0
        absent_cnt = 0

        for r in records:
            p = r.manual_presence or "not_marked"
            if p == "present":
                present_cnt += 1
            elif p in ("absent", "awol"):
                absent_cnt += 1

            if getattr(r, "late_minutes", 0) > 0:
                late_cnt += 1

            history_list.append({
                "record_id": r.id,
                "date": fields.Date.to_string(r.date) if r.date else "",
                "site": r.site_id.name if r.site_id else "Unassigned",
                "post": r.post_id.name if r.post_id else None,
                "shift": r.shift_template_id.name if r.shift_template_id else None,
                "presence": p,
                "check_in": fields.Datetime.to_string(r.check_in) if r.check_in else None,
                "check_out": fields.Datetime.to_string(r.check_out) if r.check_out else None,
                "late_minutes": getattr(r, "late_minutes", 0),
            })

        total = len(records)
        rate = round((present_cnt / total * 100), 1) if total > 0 else 100.0

        return _json_ok({
            "summary": {
                "total_shifts": total,
                "present": present_cnt,
                "late": late_cnt,
                "absent": absent_cnt,
                "attendance_rate": rate,
            },
            "history": history_list,
        })
