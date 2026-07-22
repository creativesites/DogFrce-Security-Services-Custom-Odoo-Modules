import json
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WhatsAppWebhookController(http.Controller):

    @http.route("/api/whatsapp/webhook", type="json", auth="none", methods=["POST"], csrf=False)
    def whatsapp_webhook(self):
        """
        Receives real-time message payloads from WhatsApp API gateways, executes conversational AI
        entity parsers to log operational status updates, and responds with immediate confirmation logs.
        """
        try:
            data = request.get_json_data() or {}
        except Exception:
            data = {}

        _logger.info("WhatsApp Webhook | Received raw payload: %s", json.dumps(data))

        sender = data.get("From", "")
        body = str(data.get("Body", "")).strip().lower()

        if not body:
            return {
                "status": "error",
                "reply": "DeployGuard AI: Empty message body received. Please type 'help' for instructions.",
            }

        bridge_model = request.env["security.whatsapp.bridge"].sudo()

        # Simple high-speed NLP intent classifier
        if "awol" in body:
            # Extract guard name candidate: take anything after the word 'awol'
            parts = body.split("awol", 1)
            guard_candidate = parts[1].strip() if len(parts) > 1 else ""
            guard_candidate = guard_candidate.strip(":- ")

            if not guard_candidate:
                return {
                    "status": "warning",
                    "reply": "DeployGuard AI: Intent classified as 'AWOL', but no Guard Name was extracted. Syntax: 'AWOL [Guard Name]'",
                }

            result = bridge_model.mark_guard_awol(guard_candidate)
            return {
                "status": "success",
                "reply": _("DeployGuard AI: %s") % result,
            }

        elif "status" in body or "roster" in body:
            stats = bridge_model.get_roster_status_summary()
            return {
                "status": "success",
                "reply": _(
                    "DeployGuard AI Status Summary:\n"
                    "- Today's Total Posts: %d\n"
                    "- Active Guards Present: %d\n"
                    "- AWOL / Missing Gaps: %d\n"
                    "All rosters are synchronized live."
                ) % (stats["total"], stats["present"], stats["awol"]),
            }

        # Default help fallback response
        return {
            "status": "success",
            "reply": _(
                "Welcome to DeployGuard Security WhatsApp AI Service.\n"
                "Available Commands:\n"
                "1. 'AWOL [Guard Name]' - Mark a guard as unexcused absent today\n"
                "2. 'STATUS' - Query today's active roster coverage numbers"
            ),
        }
