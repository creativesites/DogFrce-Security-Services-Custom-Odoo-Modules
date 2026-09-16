{
    "name": "DogForce Telephony",
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "summary": "Call log, screen-pop identity resolution, and dispatch linkage for the control room phone line",
    "description": """
        DogForce Security Services — Telephony:
        - security.telephony.call: every inbound/outbound call, caller
          identity resolved against employees/clients (reusing the same
          number-matching logic as the WhatsApp bridge), optionally
          promoted to an Armed Response dispatch by the controller who
          answered it.
        - /api/telephony/event: a provider-agnostic inbound webhook.
          No PBX is connected yet (DogForce has none today — see the
          architecture notes in docs/) — this is the receiving end so
          that whichever SIP trunk/PBX gets chosen (self-hosted Asterisk
          is the recommended architecture, fed by a local Namibian SIP
          trunk — MTC Cirrus, Paratus, or 0824 Telco/Telepassport all
          verified as real CRAN-licensed options) only needs to be
          pointed at this endpoint. Nothing else changes.
        - Click-to-call is scaffolded (a button + a clear "not connected
          yet" state) rather than faked — actually originating a call
          needs real Asterisk ARI connection details we don't have yet.
    """,
    "author": "DogForce Security Services",
    "depends": ["security_base", "security_ai_whatsapp_bridge", "security_armed_response"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/security_telephony_call_views.xml",
        "views/res_config_settings_views.xml",
        "views/security_telephony_menu.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
