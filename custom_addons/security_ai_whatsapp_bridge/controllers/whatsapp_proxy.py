import logging
import requests
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class WhatsAppProxyController(http.Controller):

    @http.route("/web/whatsapp/qr", type="http", auth="user")
    def get_qr_code(self):
        """
        Fetches the live QR code image or status SVG from the backend Node service on port 3000,
        serving it to Odoo administrators. This acts as a reverse proxy, bypassing firewall issues.
        """
        config_parameter = request.env['ir.config_parameter'].sudo()
        service_url = config_parameter.get_param('security_whatsapp.service_url', 'http://whatsapp-bridge:3000')
        url = f"{service_url.rstrip('/')}/qr"

        try:
            res = requests.get(url, timeout=5)
            content_type = res.headers.get("Content-Type", "image/png")
            return request.make_response(res.content, headers=[("Content-Type", content_type)])
        except Exception as e:
            _logger.error("WhatsApp Proxy | Error proxying QR code: %s", str(e))
            error_svg = """
            <svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
                <rect width="100%" height="100%" fill="#ffffff" rx="12" stroke="#e1e4e6" stroke-width="2"/>
                <circle cx="150" cy="115" r="45" fill="#ffebee"/>
                <path d="M135 100 l30 30 M165 100 l-30 30" stroke="#f44336" stroke-width="5" stroke-linecap="round"/>
                <text x="150" y="195" font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="700" fill="#f44336" text-anchor="middle">CONNECTION ERROR</text>
                <text x="150" y="225" font-family="system-ui, -apple-system, sans-serif" font-size="13" fill="#606770" text-anchor="middle">Service at port 3000 unreachable</text>
            </svg>
            """
            return request.make_response(error_svg.encode("utf-8"), headers=[("Content-Type", "image/svg+xml")])

    @http.route("/web/whatsapp/status", type="json", auth="user")
    def get_status(self):
        """
        Queries the current link status of the WhatsApp socket.
        """
        config_parameter = request.env['ir.config_parameter'].sudo()
        service_url = config_parameter.get_param('security_whatsapp.service_url', 'http://whatsapp-bridge:3000')
        url = f"{service_url.rstrip('/')}/status"

        try:
            res = requests.get(url, timeout=3)
            return res.json()
        except Exception as e:
            _logger.error("WhatsApp Proxy | Error fetching status: %s", str(e))
            return {
                "status": "disconnected",
                "hasQr": False,
                "error": str(e)
            }
