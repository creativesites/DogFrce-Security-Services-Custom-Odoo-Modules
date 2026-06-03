from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    license_key = fields.Char(
        string='License Key',
        config_parameter='security_licensing.license_key',
    )
    license_validation_endpoint = fields.Char(
        string='Validation Endpoint URL',
        config_parameter='security_licensing.validation_endpoint',
        help='Firebase HTTPS function URL for license validation.',
    )
    license_status_label = fields.Char(
        string='Current Status',
        compute='_compute_license_status_label',
    )

    @api.depends()
    def _compute_license_status_label(self):
        for rec in self:
            lic = self.env['security.license'].search([], limit=1, order='create_date desc')
            rec.license_status_label = lic.status_label if lic else 'No license configured'

    def action_validate_license_now(self):
        lic = self.env['security.license'].search([], limit=1, order='create_date desc')
        if not lic:
            key = self.env['ir.config_parameter'].sudo().get_param(
                'security_licensing.license_key', default=''
            )
            if not key:
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _('No License Key'),
                        'message': _('Enter a license key and save settings first.'),
                        'type': 'warning',
                        'sticky': False,
                    },
                }
            lic = self.env['security.license'].create({
                'license_key': key,
                'license_type': 'normal',
                'status': 'preview',
            })
        return lic.action_validate_now()
