"""
Push notification utilities and device token registration.
Uses Expo's push notification service (no raw FCM credentials needed).
"""
import json
import logging
import urllib.request
import urllib.error

from odoo import http
from odoo.http import request

from .main import _json_err, _json_ok, _parse_body, _employee_for_user

_logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"


def send_expo_push(tokens, title, body, data=None, sound="default"):
    """Send push notifications via Expo Push Service to one or more tokens."""
    if not tokens:
        return
    valid = [t for t in tokens if t and str(t).startswith("ExponentPushToken")]
    if not valid:
        _logger.debug("No valid Expo push tokens — skipping notification")
        return

    messages = [
        {"to": t, "title": title, "body": body, "data": data or {}, "sound": sound}
        for t in valid
    ]
    payload = json.dumps(messages).encode("utf-8")
    req = urllib.request.Request(
        EXPO_PUSH_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            _logger.info("Expo push sent to %d token(s): %s", len(valid), title)
    except urllib.error.URLError as exc:
        _logger.warning("Expo push failed (network): %s", exc)
    except Exception as exc:
        _logger.warning("Expo push unexpected error: %s", exc)


def _tokens_for_groups(env, *group_xml_ids):
    """Collect unique device tokens for all employees in the given Odoo groups."""
    tokens = []
    seen = set()
    for xml_id in group_xml_ids:
        group = env.ref(xml_id, raise_if_not_found=False)
        if not group:
            continue
        for user in group.users:
            emp = env["hr.employee"].sudo().search([("user_id", "=", user.id)], limit=1)
            if emp and emp.security_mobile_device_token:
                t = emp.security_mobile_device_token
                if t not in seen:
                    seen.add(t)
                    tokens.append(t)
    return tokens


def get_owner_tokens(env):
    from .main import GROUP_OWNER
    return _tokens_for_groups(env, GROUP_OWNER)


def get_manager_tokens(env):
    from .main import GROUP_MANAGER, GROUP_OWNER
    return _tokens_for_groups(env, GROUP_MANAGER, GROUP_OWNER)


def get_supervisor_tokens(env):
    from .main import GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER
    return _tokens_for_groups(env, GROUP_SUPERVISOR, GROUP_MANAGER, GROUP_OWNER)


class NotificationController(http.Controller):

    @http.route(
        "/api/security/mobile/device/token",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    def register_device_token(self, **kw):
        """Register the Expo push token for the logged-in user's employee record."""
        body = _parse_body()
        token = (body.get("token") or "").strip()
        if not token:
            return _json_err("token is required")

        employee = _employee_for_user()
        if not employee:
            return _json_err("No employee record linked to your account.")

        employee.sudo().write({"security_mobile_device_token": token})
        _logger.info("Push token registered: employee=%s token=%.20s…", employee.name, token)
        return _json_ok({"registered": True, "employee_id": employee.id})

    @http.route(
        "/api/security/mobile/notifications/test",
        auth="user",
        methods=["POST"],
        type="http",
        csrf=False,
    )
    def send_test_notification(self, **kw):
        """Send a test push to the calling user's own device."""
        employee = _employee_for_user()
        if not employee or not getattr(employee, "security_mobile_device_token", None):
            return _json_err("No device token registered for your account.")

        send_expo_push(
            [employee.security_mobile_device_token],
            "DeployGuard",
            "Push notifications are working!",
            {"type": "test"},
        )
        return _json_ok({"sent": True})
