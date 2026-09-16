from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    security_armed_response_gmaps_api_key = fields.Char(
        string="Google Maps API Key",
        config_parameter="security_armed_response.gmaps_api_key",
        help="JS API key for the Live Callout Map (Maps JavaScript API enabled). "
             "Restrict it to this database's domain(s) in Google Cloud Console — "
             "the key is visible in the page source by design, same as any "
             "browser-side Google Maps embed.",
    )
