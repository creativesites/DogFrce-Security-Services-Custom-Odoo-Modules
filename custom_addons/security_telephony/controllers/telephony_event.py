import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

VALID_EVENTS = {"ringing", "answered", "hangup", "failed"}


class TelephonyEventController(http.Controller):
    """Provider-agnostic inbound call-event webhook. No PBX is connected
    today — this is the receiving end so that whichever one DogForce ends
    up with (self-hosted Asterisk, fed by a local SIP trunk, is the
    recommended architecture) only needs a small AGI/ARI script pointed
    at this URL. Nothing here assumes a specific provider.

    Expected payload:
      {
        "token": "<security_telephony.webhook_token>",
        "event": "ringing" | "answered" | "hangup" | "failed",
        "pbx_call_id": "<PBX's own channel/call id — required, the idempotency key>",
        "direction": "inbound" | "outbound",   (only read on "ringing")
        "from_number": "...",                  (only read on "ringing")
        "to_number": "...",                    (only read on "ringing")
        "recording_url": "..."                 (optional, on "hangup")
      }
    """

    @http.route("/api/telephony/event", type="json", auth="none", methods=["POST"], csrf=False)
    def telephony_event(self, **kwargs):
        try:
            payload = request.get_json_data() or {}
        except Exception:
            payload = {}

        config = request.env["ir.config_parameter"].sudo()
        expected_token = config.get_param("security_telephony.webhook_token")
        token = payload.get("token") or request.httprequest.headers.get("X-Telephony-Token")
        if not expected_token or token != expected_token:
            _logger.warning("Telephony webhook | rejected — bad or missing token.")
            return {"success": False, "error": "Invalid token."}

        event = payload.get("event")
        pbx_call_id = payload.get("pbx_call_id")
        if event not in VALID_EVENTS or not pbx_call_id:
            return {"success": False, "error": "event must be one of %s and pbx_call_id is required." % sorted(VALID_EVENTS)}

        Call = request.env["security.telephony.call"].sudo()
        call = Call.search([("pbx_call_id", "=", pbx_call_id)], limit=1)

        if event == "ringing":
            if call:
                return {"success": True, "call_id": call.id}
            call = Call.create({
                "pbx_call_id": pbx_call_id,
                "direction": payload.get("direction", "inbound"),
                "from_number": payload.get("from_number"),
                "to_number": payload.get("to_number"),
                "state": "ringing",
                "started_at": fields.Datetime.now(),
            })
            if call.direction == "inbound" and call.from_number:
                call._resolve_caller_identity()
            return {"success": True, "call_id": call.id}

        if not call:
            _logger.warning("Telephony webhook | %s for unknown pbx_call_id=%s", event, pbx_call_id)
            return {"success": False, "error": "Unknown pbx_call_id — no matching 'ringing' event was received first."}

        if event == "answered":
            call.write({"state": "answered", "answered_at": fields.Datetime.now()})
        elif event == "hangup":
            values = {
                "state": "completed" if call.answered_at else "missed",
                "ended_at": fields.Datetime.now(),
            }
            if payload.get("recording_url"):
                values["recording_url"] = payload["recording_url"]
            call.write(values)
        elif event == "failed":
            call.write({"state": "failed", "ended_at": fields.Datetime.now()})

        return {"success": True, "call_id": call.id}
