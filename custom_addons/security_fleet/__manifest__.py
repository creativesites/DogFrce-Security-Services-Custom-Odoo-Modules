{
    "name": "DogForce Security Fleet & Guard Transport",
    "version": "19.0.1.0.0",
    "category": "Security/Fleet",
    "summary": "Manage guard transport shuttles, prearranged routes, passenger boarding manifests, fuel logs, pre-departure inspections, and service records.",
    "description": """
        DogForce Security Services Fleet & Shuttle Transport Module:
        - Vehicle fleet register with condition and odometer tracking.
        - Prearranged shuttle routes with ordered pickup/drop-off stops.
        - Per-trip passenger boarding manifests (boarded / no-show / dropped-off).
        - Pre-departure vehicle safety inspections with auto-blocking.
        - Fuel slip logs and external service records.
        - Incident linkage to specific vehicles and shuttle runs.
    """,
    "author": "DogForce Security Services",
    "depends": ["security_base", "security_operations", "security_attendance", "security_discipline"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/security_fleet_views.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
