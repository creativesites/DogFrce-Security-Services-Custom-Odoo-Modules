from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class SecurityZraConfig(models.Model):
    _name = "security.zra.config"
    _description = "ZRA Smart Invoice Configuration"
    _rec_name = "name"
    _order = "company_id, id"

    name = fields.Char(required=True, default="ZRA Smart Invoice")
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    environment = fields.Selection(
        [("sandbox", "Sandbox / Test"), ("production", "Production")],
        required=True,
        default="sandbox",
        help=(
            "Select Sandbox during ZRA certification testing. "
            "Switch to Production only after ZRA approves your go-live."
        ),
    )
    base_url = fields.Char(
        string="VSDC Base URL",
        help=(
            "ZRA VSDC root URL (no trailing slash).\n"
            "Sandbox:    https://sandbox.zra.org.zm:38083/sandboxvsdc\n"
            "Production: https://vsdc.zra.org.zm:38085/vsdc"
        ),
    )
    tpin = fields.Char(
        string="Company TPIN",
        size=10,
        help="10-digit Taxpayer Identification Number as registered with ZRA.",
    )
    bhf_id = fields.Char(
        string="Branch ID",
        default="000",
        size=3,
        help="ZRA 3-character branch code. Use '000' for head office or single-branch companies.",
    )
    dvc_srl_no = fields.Char(
        string="Device Serial Number",
        help="Virtual Sales Device serial number issued by ZRA during onboarding.",
    )
    active = fields.Boolean(default=True)

    @api.constrains("tpin")
    def _check_tpin(self):
        for rec in self:
            if rec.tpin and (not rec.tpin.isdigit() or len(rec.tpin) != 10):
                raise ValidationError("TPIN must be exactly 10 digits.")

    def _get_client(self):
        from .security_zra_client import ZRAApiClient
        if not all([self.base_url, self.tpin, self.dvc_srl_no]):
            raise UserError(
                "ZRA configuration is incomplete. "
                "Set the Base URL, TPIN, and Device Serial Number before submitting."
            )
        return ZRAApiClient(
            self.base_url, self.tpin, self.bhf_id or "000", self.dvc_srl_no
        )

    def action_test_connection(self):
        self.ensure_one()
        from .security_zra_client import ZRAApiError
        try:
            client = self._get_client()
            result = client.get_info()
            msg = result.get("resultMsg") or "Connected successfully."
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "ZRA Connection OK",
                    "message": msg,
                    "type": "success",
                    "sticky": False,
                },
            }
        except (ZRAApiError, UserError) as exc:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Connection Failed",
                    "message": str(exc),
                    "type": "danger",
                    "sticky": True,
                },
            }

    @api.model
    def get_active_config(self, company_id=None):
        """Return the active ZRA config for the given company, or the first active one."""
        domain = [("active", "=", True)]
        if company_id:
            domain.append(("company_id", "=", company_id))
        return self.search(domain, limit=1, order="id asc")
