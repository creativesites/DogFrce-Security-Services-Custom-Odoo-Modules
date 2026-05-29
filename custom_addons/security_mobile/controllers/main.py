"""
security_mobile — base helpers shared by all API controllers.
"""
import json
import logging
from functools import wraps

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ─── XML-IDs for the three mobile roles ────────────────────────────────────
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
