from odoo import _, fields, models
from odoo.exceptions import UserError


class LicenseKeyWizard(models.TransientModel):
    _name = 'license.key.wizard'
    _description = 'Enter or Replace License Key'

    license_key = fields.Char(string='License Key', required=True)
    license_type = fields.Selection([
        ('dogforce_special', 'DogForce Special'),
        ('normal', 'Standard Subscription'),
    ], string='License Type', required=True, default='normal')

    def action_apply(self):
        self.ensure_one()
        existing = self.env['security.license'].search([], limit=1, order='create_date desc')
        if existing:
            existing.write({
                'license_key': self.license_key.strip(),
                'license_type': self.license_type,
            })
            lic = existing
        else:
            lic = self.env['security.license'].create({
                'license_key': self.license_key.strip(),
                'license_type': self.license_type,
                'status': 'preview' if self.license_type == 'normal' else 'active',
            })

        self.env['ir.config_parameter'].sudo().set_param(
            'security_licensing.license_key', self.license_key.strip()
        )

        lic.validate_license()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('License Key Saved'),
                'message': lic.status_label,
                'type': 'success',
                'sticky': False,
            },
        }
