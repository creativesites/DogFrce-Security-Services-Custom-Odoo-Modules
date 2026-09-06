import uuid

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    security_telephony_webhook_token = fields.Char(
        string="Webhook Token",
        config_parameter="security_telephony.webhook_token",
        default=lambda self: str(uuid.uuid4()),
        help="Shared secret the PBX must send with every call event posted to "
             "/api/telephony/event. Generated the first time this settings page "
             "is opened and saved — until then the webhook has no token to check "
             "against and will reject every event, so visit and save this page "
             "once before pointing a PBX at the endpoint. Rotate it here if it "
             "leaks — you'll need to update the PBX-side config to match.",
    )
    security_telephony_sip_provider = fields.Selection(
        [
            ("none", "Not connected yet"),
            ("mtc_cirrus", "MTC Cirrus CloudPBX"),
            ("paratus", "Paratus Namibia"),
            ("telepassport", "0824 Telco / Telepassport"),
            ("other", "Other"),
        ],
        string="SIP Trunk Provider",
        config_parameter="security_telephony.sip_provider",
        default="none",
        help="Documentation only — which local SIP trunk feeds the PBX. "
             "Does not change how the integration works; every provider "
             "above speaks standard SIP into the same Asterisk instance.",
    )
    security_telephony_control_room_number = fields.Char(
        string="Control Room Number",
        config_parameter="security_telephony.control_room_number",
        help="The public-facing number clients/guards call, once one exists.",
    )
