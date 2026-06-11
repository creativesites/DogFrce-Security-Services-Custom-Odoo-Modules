from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class DemoSiteHome(Home):

    @http.route('/web/login', type='http', auth='none', sitemap=False)
    def web_login(self, redirect=None, **kw):
        response = super().web_login(redirect=redirect, **kw)

        # After a successful login, redirect demo users to the configured URL
        if request.session.uid:
            redirect_url = request.env['ir.config_parameter'].sudo().get_param(
                'security.demo.redirect_url', '/odoo/security-suite'
            )
            if redirect_url and not redirect:
                return request.redirect(redirect_url)

        return response

    @http.route('/security/demo/accounts', type='jsonrpc', auth='public', methods=['POST'])
    def get_demo_accounts(self, **kw):
        panel_enabled = request.env['ir.config_parameter'].sudo().get_param(
            'security.demo.panel_enabled', 'True'
        )
        if panel_enabled not in ('True', '1', 'true'):
            return {'enabled': False, 'accounts': []}

        accounts = request.env['security.demo.account'].sudo().get_demo_accounts()
        title = request.env['ir.config_parameter'].sudo().get_param(
            'security.demo.panel_title', 'Try the Live Demo'
        )
        return {
            'enabled': True,
            'title': title,
            'accounts': accounts,
        }
