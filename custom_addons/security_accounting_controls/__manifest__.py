{
    "name": "Security Accounting Controls",
    "summary": "Client payment tracking, invoice ageing, and reconciliation controls",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_billing"],
    "data": [
        "data/ir_sequence.xml",
        "security/ir.model.access.csv",
        "views/security_accounting_controls_views.xml",
    ],
    "installable": True,
    "application": False,
}
