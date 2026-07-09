from odoo import http
from odoo.http import request
from odoo.addons.web.controllers.home import Home


class DemoSiteHome(Home):

    @http.route('/web/login', type='http', auth='none', sitemap=False)
    def web_login(self, redirect=None, **kw):
        # GET — always render our custom login page
        if request.httprequest.method == 'GET':
            return self._render_demo_login(redirect=redirect)

        # POST — let Odoo handle authentication
        try:
            response = super().web_login(redirect=redirect, **kw)
        except Exception:
            return self._render_demo_login(
                redirect=redirect,
                error="An error occurred during sign-in. Please try again.",
                login=kw.get('login', ''),
            )

        if request.session.uid:
            # Successful login — redirect to configured URL
            redirect_url = request.env['ir.config_parameter'].sudo().get_param(
                'security.demo.redirect_url', '/odoo/security-suite'
            )
            if redirect_url and not redirect:
                return request.redirect(redirect_url)
            return response

        # Authentication failed — extract error and re-render our page
        error = "Wrong login or password."
        if hasattr(response, 'qcontext') and response.qcontext:
            error = response.qcontext.get('error', error)

        return self._render_demo_login(
            redirect=redirect,
            error=error,
            login=kw.get('login', ''),
        )

    def _render_demo_login(self, redirect=None, error='', login=''):
        demo_accounts = []
        demo_title = 'Try the Live Demo'
        panel_enabled = request.env['ir.config_parameter'].sudo().get_param(
            'security.demo.panel_enabled', 'True'
        )
        if panel_enabled in ('True', '1', 'true'):
            demo_title = request.env['ir.config_parameter'].sudo().get_param(
                'security.demo.panel_title', 'Try the Live Demo'
            )
            demo_accounts = request.env['security.demo.account'].sudo().search_read(
                [('active', '=', True)],
                ['name', 'login', 'password_hint', 'description'],
                order='sequence asc',
            )
        return request.render('security_demo_site.login_page', {
            'login': login,
            'error': error,
            'redirect': redirect or '',
            'demo_accounts': demo_accounts,
            'demo_title': demo_title,
        })

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
