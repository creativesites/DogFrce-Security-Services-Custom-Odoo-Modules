{
    "name": "DogForce Armed Response & Armoury",
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "summary": "Armed response unit dispatch board and armoury issue/return ledger",
    "description": """
        DogForce Security Services — Armed Response & Armoury:
        - Response unit register (commander, members, assigned vehicle, status).
        - Dispatch board: raise a callout (panic button, phone call, linked
          incident, or manual), assign a unit, track it through
          acknowledged -> dispatched -> on scene -> resolved.
        - Armoury ledger: a filtered view over the existing equipment
          register/allocation models (security_equipment), scoped to
          licensed items (firearms, ammunition), with a dedicated
          custodian role.
        Live callout map is a follow-up slice — this ships the data model
        and dispatch workflow first.
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
        "views/security_armed_response_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_armed_response/static/src/css/dispatch_board.css",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
