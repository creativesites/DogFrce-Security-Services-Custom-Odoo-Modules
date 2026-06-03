{
    "name": "Security Discipline",
    "summary": "Behavioral incidents, reliability score impact, and payroll-linked deductions",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_loans", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_discipline_views.xml",
        "views/hr_employee_discipline_views.xml",
    ],
    "installable": True,
    "application": False,
}
