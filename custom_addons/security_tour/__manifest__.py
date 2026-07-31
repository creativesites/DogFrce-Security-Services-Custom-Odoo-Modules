# -*- coding: utf-8 -*-
{
    'name': 'DogForce Product Tours & Onboarding Engine',
    'version': '19.0.1.0.0',
    'category': 'Security Services/Onboarding',
    'summary': 'Interactive Product Tours, Prospect Demo Guides, and Role-Based Staff Onboarding Engine',
    'description': """
        DogForce Interactive Product Tours Module (security_tour).
        
        Features:
        - 3-Minute Prospect Demo Tour ("Silent Salesperson" for cold prospects)
        - High-Conversion CTA Modal for trial setup request
        - Role-Based Onboarding Tours for Supervisors, Managers, and Executives
        - Zuri Mascot Avatar Tooltip Cards & Microcopy
        - Top Systray Tour Menu Launcher
        - Tour completion tracking & user preferences on res.users
    """,
    'author': 'DogForce Security Services / Winston Zulu',
    'license': 'LGPL-3',
    'depends': [
        'web',
        'web_tour',
        'security_base',
        'security_help',
        'security_theme',
    ],
    'data': [
        'security/security_tour_security.xml',
        'security/ir.model.access.csv',
        'data/tour_definition_data.xml',
        'views/res_users_views.xml',
        'views/tour_definition_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'security_tour/static/src/css/security_tour.css',
            'security_tour/static/src/xml/tour_popover_template.xml',
            'security_tour/static/src/xml/tour_cta_modal.xml',
            # 'security_tour/static/src/xml/tour_systray.xml',
            'security_tour/static/src/xml/tour_runner_template.xml',
            'security_tour/static/src/js/tour_cta_modal.js',
            'security_tour/static/src/js/tour_runner.js',
            # 'security_tour/static/src/js/systray/tour_systray.js',
            'security_tour/static/src/js/tour_service_patch.js',
            'security_tour/static/src/js/tours/prospect_demo_tour.js',
            'security_tour/static/src/js/tours/supervisor_tour.js',
            'security_tour/static/src/js/tours/manager_tour.js',
            'security_tour/static/src/js/tours/owner_tour.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
