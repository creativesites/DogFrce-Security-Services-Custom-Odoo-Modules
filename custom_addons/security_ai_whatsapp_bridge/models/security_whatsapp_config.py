import requests
from odoo import _, api, fields, models


class SecurityWhatsAppConfig(models.Model):
    _name = "security.whatsapp.config"
    _description = "WhatsApp AI Bridge Configuration"

    name = fields.Char(string="Name", default="WhatsApp Service Settings", required=True)
    service_url = fields.Char(
        string="Service URL",
        required=True,
        default="http://whatsapp-bridge:3000",
        help="The local or public address of the Node.js Baileys service.",
    )
    connection_status = fields.Selection(
        [
            ("connected", "Connected"),
            ("connecting", "Scanning / Connecting"),
            ("disconnected", "Disconnected"),
        ],
        string="Link Status",
        compute="_compute_connection_status",
        store=False,
    )
    qr_code_image = fields.Html(
        string="Pairing QR Code",
        compute="_compute_qr_code_image",
        sanitize=False,
    )
    restrict_authorized_numbers = fields.Boolean(
        string="Restrict to Authorized Numbers",
        default=False,
        help="If enabled, only messages sent from whitelisted phone numbers will be processed.",
    )
    authorized_numbers = fields.Text(
        string="Allowed Phone Numbers",
        help="Comma-separated or line-separated list of authorized phone numbers (e.g., +260971234567, 260965000111).",
    )
    ignore_unrelated_messages = fields.Boolean(
        string="Ignore Unrelated / Spam Messages",
        default=True,
        help="If checked, general chitchat or unrelated messages are logged as ignored without sending a reply.",
    )

    @api.model
    def get_config_action(self):
        """
        Returns an action to open the singleton configuration record.
        """
        record = self.search([], limit=1)
        if not record:
            record = self.create({"service_url": "http://whatsapp-bridge:3000"})
        return {
            "type": "ir.actions.act_window",
            "name": "WhatsApp AI Bridge Settings",
            "res_model": "security.whatsapp.config",
            "res_id": record.id,
            "view_mode": "form",
            "target": "current",
        }

    def _compute_connection_status(self):
        """
        Pings the local WhatsApp service status endpoint to check link state.
        """
        config_parameter = self.env["ir.config_parameter"].sudo()
        for rec in self:
            service_url = config_parameter.get_param("security_whatsapp.service_url", rec.service_url or "http://whatsapp-bridge:3000")
            url = f"{service_url.rstrip('/')}/status"
            try:
                res = requests.get(url, timeout=2)
                data = res.json()
                rec.connection_status = data.get("status", "disconnected")
            except Exception:
                rec.connection_status = "disconnected"

    def _compute_qr_code_image(self):
        """
        Renders a dynamic HTML image card pointing to the proxy endpoint or connected success badge.
        """
        for rec in self:
            if rec.connection_status == "connected":
                rec.qr_code_image = """
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 28px; background: #f0fdf4; border: 1.5px solid #bbf7d0; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); width: 340px; margin: 20px auto;">
                        <div style="width: 64px; height: 64px; border-radius: 50%; background: #22c55e; display: flex; align-items: center; justify-content: center; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(34, 197, 94, 0.3);">
                            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                        </div>
                        <div style="font-size: 18px; color: #15803d; font-weight: 700; text-align: center; margin-bottom: 6px;">WhatsApp Linked &amp; Active</div>
                        <div style="font-size: 13px; color: #166534; font-weight: 500; text-align: center; line-height: 1.5;">DeployGuard AI Bridge is live.<br/>Send <b>STATUS</b> or <b>AWOL [Name]</b> from your phone.</div>
                    </div>
                """
            else:
                rec.qr_code_image = """
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03); width: 320px; margin: 20px auto;">
                        <img src="/web/whatsapp/qr?t=%s" style="width: 270px; height: 270px; border-radius: 12px; margin-bottom: 16px; object-fit: contain;" alt="WhatsApp Link QR Code"/>
                        <div style="font-size: 14px; color: #1e293b; font-weight: 600; text-align: center; margin-bottom: 4px;">Link DeployGuard</div>
                        <div style="font-size: 12px; color: #64748b; font-weight: 400; text-align: center; line-height: 1.4;">Scan this QR with your phone's WhatsApp: Settings &gt; Linked Devices</div>
                    </div>
                """ % fields.Datetime.now().timestamp()

    def action_refresh(self):
        """
        Triggers a fresh session restart on the bridge service and forces view recalculation.
        """
        config_parameter = self.env["ir.config_parameter"].sudo()
        for rec in self:
            service_url = config_parameter.get_param("security_whatsapp.service_url", rec.service_url or "http://whatsapp-bridge:3000")
            try:
                requests.post(f"{service_url.rstrip('/')}/restart", timeout=3)
            except Exception:
                pass
        return True

    @api.model_create_multi
    def create(self, vals_list):
        records = super(SecurityWhatsAppConfig, self).create(vals_list)
        for rec in records:
            if rec.service_url:
                self.env["ir.config_parameter"].sudo().set_param("security_whatsapp.service_url", rec.service_url)
        return records

    def write(self, vals):
        res = super(SecurityWhatsAppConfig, self).write(vals)
        if "service_url" in vals:
            self.env["ir.config_parameter"].sudo().set_param("security_whatsapp.service_url", vals["service_url"])
        return res
