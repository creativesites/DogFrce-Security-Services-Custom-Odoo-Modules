"""
security_mobile — base helpers shared by all API controllers.
"""
import json
import logging
from functools import wraps

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ─── XML-IDs for the mobile roles ────────────────────────────────────
GROUP_GUARD      = "security_base.group_security_guard"
GROUP_SUPERVISOR = "security_base.group_security_supervisor"
GROUP_MANAGER    = "security_base.group_security_manager"
GROUP_OWNER      = "security_base.group_security_owner"


def _json_ok(data, status=200):
    """Return a JSON success response."""
    return request.make_json_response({"success": True, "data": data}, status=status)


def _json_err(message, status=400):
    """Return a JSON error response."""
    return request.make_json_response({"success": False, "error": message}, status=status)


def _parse_body():
    """Parse the raw JSON request body. Returns an empty dict on failure."""
    try:
        raw = request.httprequest.data or b"{}"
        return json.loads(raw)
    except (ValueError, TypeError):
        return {}


def require_group(*group_xml_ids):
    """
    Decorator that enforces group membership before the controller runs.
    Usage::

        @require_group(GROUP_SUPERVISOR)
        def my_endpoint(self, **kw): ...
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(self, *args, **kw):
            user = request.env.user
            for gid in group_xml_ids:
                if user.has_group(gid):
                    return fn(self, *args, **kw)
            return _json_err("Access denied: insufficient role.", status=403)
        return wrapper
    return decorator


def _employee_for_user(user=None):
    """Return the hr.employee record linked to the given (or current) user."""
    if user is None:
        user = request.env.user
    employee = request.env["hr.employee"].sudo().search(
        [("user_id", "=", user.id)], limit=1
    )
    return employee or request.env["hr.employee"]


class AuthController(http.Controller):

    @http.route(
        "/api/security/mobile/auth/login",
        auth="public",
        methods=["POST", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def auth_login(self, **kw):
        """
        Mobile app REST login endpoint.
        Body: { db, login/username, password }
        Returns session_id, uid, name, role, employee_id in JSON payload.
        """
        body = _parse_body()
        db = body.get("db") or request.db or "dogforce_dev"
        login = body.get("login") or body.get("username")
        password = body.get("password")

        if not login or not password:
            return _json_err("Username and password are required.", status=400)

        try:
            if db:
                request.session.db = db
            credential = {'login': login, 'password': password, 'type': 'password'}
            try:
                auth_info = request.session.authenticate(request.env, credential)
                uid = auth_info.get('uid') if isinstance(auth_info, dict) else request.session.uid
            except Exception:
                try:
                    uid = request.session.authenticate(login, password)
                except Exception:
                    uid = request.session.authenticate(db, login, password)
        except Exception as e:
            _logger.exception("Mobile login exception for %s on %s", login, db)
            return _json_err(f"Authentication failed: {e}", status=401)

        user = request.env["res.users"].sudo().browse(uid)
        if user.has_group(GROUP_OWNER):
            role = "owner"
        elif user.has_group(GROUP_MANAGER):
            role = "manager"
        elif user.has_group(GROUP_SUPERVISOR):
            role = "supervisor"
        else:
            role = "guard"

        employee = _employee_for_user(user)

        return _json_ok({
            "session_id": request.session.sid,
            "uid": user.id,
            "name": user.name,
            "username": login,
            "db": db,
            "role": role,
            "employee_id": employee.id if employee.exists() else None,
        })

    @http.route(
        "/api/security/mobile/auth/me",
        auth="user",
        methods=["GET", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def auth_me(self, **kw):
        """Return current user's role (from Odoo groups) and employee info."""
        user = request.env.user

        if user.has_group(GROUP_OWNER):
            role = "owner"
        elif user.has_group(GROUP_MANAGER):
            role = "manager"
        elif user.has_group(GROUP_SUPERVISOR):
            role = "supervisor"
        else:
            role = "guard"

        employee = _employee_for_user(user)

        return _json_ok({
            "uid": user.id,
            "name": user.name,
            "role": role,
            "employee_id": employee.id if employee.exists() else None,
        })


class PinController(http.Controller):

    @http.route(
        "/api/security/mobile/auth/pin",
        auth="public",
        methods=["POST", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def pin_auth(self, **kw):
        """
        Authenticate using a PIN hash.

        Body: { db, employee_id, pin_hash }
        Returns: session info on success, error on failure.
        """
        body = _parse_body()
        employee_id = body.get("employee_id")
        pin_hash = body.get("pin_hash")
        db = body.get("db") or request.db

        if not employee_id or not pin_hash:
            return _json_err("employee_id and pin_hash are required.")

        env = request.env(su=True)
        employee = env["hr.employee"].browse(int(employee_id))

        if not employee.exists():
            return _json_err("Employee not found.", status=404)

        stored_hash = getattr(employee, "security_mobile_pin_hash", None)
        if not stored_hash:
            return _json_err("PIN not configured for this employee.", status=401)

        if stored_hash != pin_hash:
            return _json_err("Invalid PIN.", status=401)

        # Authenticate the linked user
        user = employee.user_id
        if not user:
            return _json_err("No Odoo user linked to this employee.", status=401)

        # Create a new session
        request.session.authenticate(db, user.login, user._crypt_context().hash(pin_hash))

        return _json_ok({
            "uid": user.id,
            "name": user.name,
            "employee_id": employee.id,
            "employee_name": employee.name,
            "session_id": request.session.sid,
        })

    @http.route(
        "/api/security/mobile/auth/pin/set",
        auth="user",
        methods=["POST", "OPTIONS"],
        type="http",
        csrf=False,
        cors="*",
    )
    def pin_set(self, **kw):
        """Set or update the employee's mobile PIN hash."""
        body = _parse_body()
        pin_hash = body.get("pin_hash")
        if not pin_hash or len(pin_hash) < 8:
            return _json_err("pin_hash must be at least 8 characters (SHA-256 recommended).")

        employee = _employee_for_user()
        if not employee:
            return _json_err("No employee record linked to your account.")

        employee.sudo().write({"security_mobile_pin_hash": pin_hash})
        return _json_ok({"message": "PIN updated successfully."})

