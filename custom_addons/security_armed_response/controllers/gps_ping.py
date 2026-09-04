import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)


class ResponseUnitGpsController(http.Controller):
    """Inbound position-update endpoint for whatever GPS/tracking provider
    ends up in use — a device, a fleet-tracking platform's outbound
    webhook, or a manual test script can all call this the same way.

    The Live Callout Map only reads security.response.unit.last_lat/
    last_lng/last_position_at (see security_response_map.py), so pointing
    a real provider at this endpoint is the only change needed once one
    is chosen — the map itself does not change.

    Auth: each unit carries its own gps_token (rotate via 'Regenerate GPS
    Token' on the unit form if it leaks) rather than one shared module
    secret, so one compromised device credential doesn't expose every
    unit's feed.
    """

    @http.route(
        "/api/armed_response/units/<int:unit_id>/ping",
        type="json", auth="none", methods=["POST"], csrf=False,
    )
    def ping_position(self, unit_id, **kwargs):
        try:
            payload = request.get_json_data() or {}
        except Exception:
            payload = {}

        token = payload.get("token") or request.httprequest.headers.get("X-Gps-Token")
        lat = payload.get("lat")
        lng = payload.get("lng")

        if lat is None or lng is None:
            return {"success": False, "error": "lat and lng are required."}

        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return {"success": False, "error": "lat and lng must be numeric."}

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lng <= 180.0):
            return {"success": False, "error": "lat/lng out of range."}

        unit = request.env["security.response.unit"].sudo().search([
            ("id", "=", unit_id),
            ("gps_token", "=", token),
        ], limit=1)

        if not unit:
            _logger.warning("GPS ping | rejected — unknown unit or bad token (unit_id=%s)", unit_id)
            return {"success": False, "error": "Unknown unit or invalid token."}

        unit.write({
            "last_lat": lat,
            "last_lng": lng,
            "last_position_at": fields.Datetime.now(),
        })
        return {"success": True}
