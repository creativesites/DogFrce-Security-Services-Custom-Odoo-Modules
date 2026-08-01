# -*- coding: utf-8 -*-
{
    'name': 'DogForce Security Services Suite',
    'version': '19.0.1.0.0',
    'summary': 'All-in-One installer for the complete DogForce Security Services Suite & Zambian Localization',
    'description': """
        DogForce Security Services Custom Odoo Modules Meta-Module.
        Installing this module will automatically install all related custom modules in the system:
        - Security Base & Master Data
        - Security Operations (Sites, Posts, Guard Roster, Operations CRM)
        - Security Attendance & Posting Sheets
        - Security Leave Management
        - Security Payroll Core, Namibia & Zambia Localization
        - Security Loans, Discipline, & Equipment Tracking
        - Security Clients, Billing, Invoicing & ZRA Compliance
        - Security AI Engine & WhatsApp Bridge
        - Security Client Reports & Reporting
        - DogForce Licensing & Onboarding
        - Zambian Demo Data Seed (Sentinel Security Zambia Ltd)
    """,
    'category': 'Security Services',
    'author': 'Winston Zulu',
    'license': 'LGPL-3',
    'depends': [
        'security_accounting_controls',
        'security_ai_engine',
        'security_ai_whatsapp_bridge',
        'security_attendance',
        'security_backup_vault',
        'security_base',
        'security_billing',
        'security_billing_account',
        'security_billing_crm',
        'security_billing_sale',
        'security_client_onboarding',
        'security_client_reports',
        'security_compliance_roster',
        'security_discipline',
        'security_discipline_payroll',
        'security_documents',
        'security_dogforce_data',
        'security_dogforce_migration',
        'security_equipment',
        'security_equipment_payroll',
        'security_fleet',
        'security_fleet_ops',
        'security_help',
        'security_l10n_na',
        'security_leave',
        'security_licensing',
        'security_loans',
        'security_mobile',
        'security_mobile_bridge',
        'security_notifications',
        'security_operations',
        'security_operations_crm',
        'security_payroll_core',
        'security_portal',
        'security_reconciliation_billing_account',
        'security_reconciliation_core',
        'security_reporting',
        'security_shift_planner',
        'security_theme',
        'security_tour',
    ],
    'data': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
