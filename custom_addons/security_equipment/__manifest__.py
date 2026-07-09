{
    "name": "DogForce Security Equipment & Asset Tracking",
    "version": "19.0.1.0.0",
    "category": "Security/Equipment",
    "summary": "Manage guard uniforms, trackable radios, firearms, allocations, damages, and automated payroll deductions.",
    "description": """
        DogForce Security Services Custom Odoo Module for Equipment & Asset Tracking:
        - Uniforms (boots, caps, shirts) tracking via stock quantity.
        - Radios and Firearms serialized item tracking.
        - Guard allocations, issue, and return registers.
        - Automatic Odoo payslip deductions for lost or damaged equipment.
    """,
    "author": "Google DeepMind team working on Advanced Agentic Coding",
    "depends": ["security_base", "security_payroll_core", "security_operations"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/security_equipment_views.xml",
        "reports/equipment_allocation_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "security_equipment/static/src/js/equipment_dashboard.js",
            "security_equipment/static/src/xml/equipment_dashboard.xml",
        ],
    },
    "installable": True,
    "application": True,
    "auto_install": False,
    "license": "LGPL-3",
}
