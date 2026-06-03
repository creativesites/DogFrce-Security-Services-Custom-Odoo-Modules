{
    "name": "Security Leave",
    "summary": "Leave setup, balances, and requests for security operations",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_attendance"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_leave_views.xml",
        "data/security_leave_cron.xml",
        "data/security_leave_yearend_cron.xml",
    ],
    "installable": True,
    "application": False,
}
