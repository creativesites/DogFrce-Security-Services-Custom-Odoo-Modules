import logging
from odoo import api, models, _
from odoo.addons.security_mobile.controllers.notifications import (
    send_expo_push,
    get_supervisor_tokens,
    get_manager_tokens,
    get_owner_tokens,
)

_logger = logging.getLogger(__name__)


class SecurityMobileBridge(models.AbstractModel):
    _name = "security.mobile.bridge"
    _description = "Security Mobile and Push Notification Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """
        Listens to the DeployGuard Central Intelligence Bus and converts critical business
        exceptions (AWOLs, vehicle breakdowns, compliance bypasses) directly into mobile push notifications.
        """
        _logger.info("Mobile Bridge | Processing event: %s", event_name)

        if event_name == "attendance.missed":
            guard = payload.get("guard_name", "")
            site = payload.get("site_name", "")
            post = payload.get("post_name", "")

            title = _("CRITICAL: Guard AWOL Detected")
            body = _("Guard '%s' missed shift at Site '%s' (Post: %s). Emergency replacement required immediately.") % (guard, site, post)

            tokens = get_supervisor_tokens(self.env)
            if tokens:
                send_expo_push(tokens, title, body, data={"event_name": event_name, "source_id": source_id})
                _logger.info("Mobile Bridge | Dispatched AWOL push alert to %s supervisors", len(tokens))

        elif event_name == "fleet.breakdown":
            vehicle = payload.get("vehicle_name", "")
            state = payload.get("state", "broken_down")
            active_runs = payload.get("active_runs", [])

            title = _("VEHICLE OUT OF SERVICE")
            body = _("Vehicle '%s' reported state change to: %s.") % (vehicle, state.replace("_", " ").upper())
            if active_runs:
                body += _("\nCRITICAL: Vehicle is currently assigned to active runs: %s!") % ", ".join(active_runs)

            tokens = get_manager_tokens(self.env)
            if tokens:
                send_expo_push(tokens, title, body, data={"event_name": event_name, "source_id": source_id})
                _logger.info("Mobile Bridge | Dispatched vehicle breakdown push alert to %s managers", len(tokens))

        elif event_name == "compliance.bypass":
            guard = payload.get("guard", "")
            site = payload.get("site", "")
            auth_by = payload.get("authorized_by", "")
            justification = payload.get("justification", "")

            title = _("COMPLIANCE BYPASS WARNING")
            body = _("Emergency override authorized by %s for Guard '%s' at Site '%s'. Reason: %s") % (auth_by, guard, site, justification)

            tokens = get_owner_tokens(self.env)
            if tokens:
                send_expo_push(tokens, title, body, data={"event_name": event_name, "source_id": source_id})
                _logger.info("Mobile Bridge | Dispatched compliance override push warning to %s owners", len(tokens))
