{
    "name": "DogForce Armed Response & Armoury",
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "summary": "Armed response unit dispatch board, live callout map, and armoury issue/return ledger",
    "description": """
        DogForce Security Services — Armed Response & Armoury:
        - Response unit register (commander, members, assigned vehicle, status).
        - Dispatch board: raise a callout (panic button, phone call, linked
          incident, or manual), assign a unit, track it through
          acknowledged -> dispatched -> on scene -> resolved.
        - Live Callout Map: Google Maps view of response units and open
          callouts. Units carry a per-unit GPS ping token and an inbound
          /api/armed_response/units/<id>/ping endpoint — point whatever GPS
          tracking provider gets chosen at it later; the map itself only
          reads last_lat/last_lng and doesn't change.
        - Armoury ledger: a filtered view over the existing equipment
          register/allocation models (security_equipment), scoped to
          licensed items (firearms, ammunition), with a dedicated
          custodian role.
    """,
    "author": "DogForce Security Services",
    "depends": ["security_base", "security_operations", "security_discipline", "security_equipment", "security_fleet"],
    "data": [
        "security/security_groups.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/security_response_unit_views.xml",
        "views/security_response_dispatch_views.xml",
        "views/security_armoury_views.xml",
        "views/res_config_settings_views.xml",
        "views/security_armed_response_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_armed_response/static/src/css/dispatch_board.css",
            "security_armed_response/static/src/css/live_callout_map.css",
            "security_armed_response/static/src/js/live_callout_map.js",
            "security_armed_response/static/src/xml/live_callout_map.xml",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
