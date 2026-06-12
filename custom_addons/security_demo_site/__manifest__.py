{
    'name': 'DogForce Demo Site',
    'version': '19.0.1.0.0',
    'category': 'Customization',
    'summary': 'Demo account management, login panel, and post-login redirect to Security Suite',
    'depends': ['web', 'base', 'security_theme', 'security_suite'],
    'data': [
        'security/ir.model.access.csv',
        'views/login_demo_panel.xml',
        'views/security_demo_config_views.xml',
        'views/security_demo_menu.xml',
        'data/demo_accounts.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'security_demo_site/static/src/css/demo_panel.css',
            'security_demo_site/static/src/js/demo_autofill.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
