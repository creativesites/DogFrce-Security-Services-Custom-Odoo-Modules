{
    "name": "Security Reconciliation Core",
    "summary": "Governed cross-module synchronization, reconciliation, and audit framework",
    "version": "19.0.1.0.0",
    "category": "Security/Operations",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_base", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "security/security_reconciliation_security.xml",
        "data/security_reconciliation_cron.xml",
        "views/security_reconciliation_views.xml",
    ],
    "installable": True,
    "application": False,
}
