# -*- coding: utf-8 -*-
{
    'name': 'DogForce Real Company Data',
    'version': '19.0.1.0.0',
    'category': 'Customization',
    'summary': 'Loads real DogForce company data from XLSX exports via post-init hook',
    'author': 'Winston Zulu',
    'license': 'LGPL-3',
    'depends': [
        'security_base',
        'security_operations',
        'security_billing',
        'hr_attendance',
        'sale',
    ],
    'data': [],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'auto_install': False,
}
