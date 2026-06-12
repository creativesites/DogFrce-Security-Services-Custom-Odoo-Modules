# -*- coding: utf-8 -*-
{
    'name': 'DogForce Security Services Suite',
    'version': '19.0.1.0.0',
    'summary': 'All-in-One installer for the complete DogForce Security Services Custom Suite',
    'description': """
        DogForce Security Services Custom Odoo Modules Meta-Module.
        Installing this module will automatically install all related custom modules in the system:
        - Security Base & Master Data
        - Security Operations (Sites, Posts, Guard Roster)
        - Security Attendance & Posting Sheets
        - Security Leave Management
        - Security Payroll Core & Namibia Localization
        - Security Loans, Discipline, & Equipment Tracking
        - Security Clients & Billing
        - Security AI Engine
        - Security Client Reports & Reporting
        - DeployGuard Licensing
        - DogForce Data Migration
        - Demo Data Seed
    """,
    'category': 'Security Services',
    'author': 'Winston Zulu',
    'license': 'LGPL-3',
    'depends': [
        'security_base',
        'security_operations',
        'security_attendance',
        'security_leave',
        'security_l10n_na',
        'security_payroll_core',
        'security_loans',
        'security_discipline',
        'security_billing',
        'security_client_reports',
        'security_equipment',
        'security_fleet',
        'security_accounting_controls',
        'security_reporting',
        'security_ai_engine',
        'security_shift_planner',
        'security_mobile',
        'security_documents',
        'security_notifications',
        'security_licensing',
        'security_dogforce_migration',
        'security_demo_data',
        'security_help',
    ],
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
