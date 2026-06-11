from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    security_active_theme = fields.Selection([
        ('dogforce_navy', 'DogForce Navy (Default)'),
        ('corporate_dark', 'Corporate Dark'),
        ('forest_guard', 'Forest Guard'),
        ('executive_slate', 'Executive Slate'),
    ], string='UI Theme', default='dogforce_navy',
        config_parameter='security.theme.active')

    security_login_footer = fields.Char(
        string='Login Footer Text',
        default='© 2026 DogForce Security Services. All rights reserved.',
        config_parameter='security.theme.login_footer')

    security_login_bg_color = fields.Char(
        string='Login Background Color',
        default='#1e3a5f',
        config_parameter='security.theme.login_bg_color')

    security_report_primary_color = fields.Char(
        string='Report Primary Color',
        default='#1e3a5f',
        help='Color used for PDF report headers, table headers, and footers.',
        config_parameter='security.theme.report_primary_color')
