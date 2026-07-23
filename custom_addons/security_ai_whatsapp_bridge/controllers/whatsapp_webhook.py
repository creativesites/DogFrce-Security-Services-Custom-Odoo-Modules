import json
import logging
from odoo import _, http
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
            raw_data = request.get_json_data() or {}
        except Exception:
            raw_data = {}

        _logger.info("WhatsApp Webhook | Received raw payload: %s", json.dumps(raw_data))

        # Handle both standard JSON payload and Odoo JSON-RPC wrapper format
        data = raw_data.get("params", raw_data) if isinstance(raw_data, dict) else {}

        sender = data.get("From", "")
        raw_body = str(data.get("Body", "")).strip()

        if not raw_body:
            _logger.warning("WhatsApp Webhook | Received empty Body from sender [%s]", sender)
            return {
                "status": "error",
                "reply": "DeployGuard AI: Empty message body received. Please type 'help' for instructions.",
            }

        bridge_model = request.env["security.whatsapp.bridge"].sudo()
        reply_msg = bridge_model.process_incoming_message(raw_body, sender)

        if not reply_msg:
            return {
                "status": "ignored",
                "reply": "",
            }

        return {
            "status": "success",
            "reply": reply_msg,
        }
