{
    'name': 'DogForce White-Label Theme',
    'version': '19.0.1.0.0',
    'category': 'Customization',
    'summary': 'Branding, theme presets, login white-label, and PDF report theming',
    'depends': ['web', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_config_parameter.xml',
        'views/res_config_settings_views.xml',
        'views/login_template.xml',
        'views/report_layout.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'security_theme/static/src/css/themes.css',
            'security_theme/static/src/js/theme_loader.js',
        ],
        'web.assets_frontend': [
            'security_theme/static/src/css/themes.css',
            'security_theme/static/src/css/login_custom.css',
        ],
        'web.report_assets_pdf': [
            'security_theme/static/src/css/report_brand.css',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
