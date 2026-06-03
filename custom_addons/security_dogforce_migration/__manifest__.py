{
    "name": "DogForce Data Migration",
    "summary": "CSV import tools for migrating guards, clients, leave balances, and loan data",
    "version": "19.0.1.0.0",
    "category": "Security/Migration",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_billing", "security_leave", "security_loans"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_migration_views.xml",
        "data/security_migration_templates.xml",
    ],
    "installable": True,
    "application": False,
}
