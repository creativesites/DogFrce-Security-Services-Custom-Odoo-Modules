from odoo import api, fields, models


class SecurityDemoAccount(models.Model):
    _name = 'security.demo.account'
    _description = 'Demo Account'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string='Role Label')
    login = fields.Char(required=True, string='Login (Email)')
    password_hint = fields.Char(required=True, string='Password (display)')
    description = fields.Char(string='Short Description')
    features = fields.Text(string='Access Features', help='One feature per line, shown as bullet points on the login panel')
    badge_color = fields.Char(string='Badge Color', default='#1e3a5f', help='Hex color for the role badge')
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Linked User', ondelete='set null')

    @api.model
    def get_demo_accounts(self):
        return self.search_read(
            [('active', '=', True)],
            ['name', 'login', 'password_hint', 'description', 'features', 'badge_color'],
            order='sequence asc',
        )


class SecurityDemoSiteConfig(models.TransientModel):
    _inherit = 'res.config.settings'

    demo_site_enabled = fields.Boolean(
        string='Show Demo Panel on Login Page',
        default=True,
        config_parameter='security.demo.panel_enabled')

    demo_redirect_action = fields.Char(
        string='Post-Login Redirect URL',
        default='/odoo/security-suite',
        help='Where demo users land after logging in.',
        config_parameter='security.demo.redirect_url')

    demo_panel_title = fields.Char(
        string='Demo Panel Title',
        default='Try the Live Demo',
        config_parameter='security.demo.panel_title')
