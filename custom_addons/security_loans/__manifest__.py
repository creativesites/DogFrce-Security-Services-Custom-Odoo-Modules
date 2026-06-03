{
    "name": "Security Loans",
    "summary": "Employee loans and payroll-linked loan deductions for security companies",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_payroll_core"],
    "data": [
        "security/ir.model.access.csv",
        "views/security_loans_views.xml",
        "reports/security_loan_statement.xml",
    ],
    "installable": True,
    "application": False,
}
