import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

FEATURE_TIERS = {
    'basic_roster':       ['starter', 'professional', 'enterprise'],
    'shift_planner_ai':   ['professional', 'enterprise'],
    'fleet_module':       ['professional', 'enterprise'],
    'advanced_reporting': ['professional', 'enterprise'],
    'api_access':         ['enterprise'],
}


class SecurityLicense(models.Model):
    _name = 'security.license'
    _description = 'DeployGuard License'
    _rec_name = 'license_key'
    _order = 'create_date desc'

    license_key = fields.Char(string='License Key', required=True, copy=False, index=True)
    license_type = fields.Selection([
        ('dogforce_special', 'DogForce Special'),
        ('normal', 'Standard Subscription'),
    ], string='License Type', required=True, default='normal')
    tier = fields.Selection([
        ('starter', 'Starter (≤50 guards, $99/mo)'),
        ('professional', 'Professional (≤250 guards, $299/mo)'),
        ('enterprise', 'Enterprise (unlimited, custom)'),
    ], string='Subscription Tier')
    status = fields.Selection([
        ('preview', 'Preview / Trial'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ], string='Status', required=True, default='preview')
    preview_expiry = fields.Datetime(string='Trial Expires')
    subscription_expiry = fields.Datetime(string='Subscription Expires')
    guard_limit = fields.Integer(string='Guard Limit', default=50,
                                 help='0 means unlimited (Enterprise).')
    last_validated = fields.Datetime(string='Last Validated', readonly=True)
    log_ids = fields.One2many('security.license.log', 'license_id', string='Activity Log',
                               readonly=True)

    remaining_preview_days = fields.Integer(
        string='Trial Days Remaining',
        compute='_compute_remaining_preview_days',
    )
    status_label = fields.Char(
        string='Status Summary',
        compute='_compute_status_label',
    )

    _sql_constraints = [
        ('license_key_unique', 'UNIQUE(license_key)', 'License key must be unique.'),
    ]

    @api.depends('status', 'preview_expiry')
    def _compute_remaining_preview_days(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.status == 'preview' and rec.preview_expiry:
                delta = rec.preview_expiry - now
                rec.remaining_preview_days = max(0, delta.days)
            else:
                rec.remaining_preview_days = 0

    @api.depends('status', 'tier', 'license_type', 'remaining_preview_days')
    def _compute_status_label(self):
        for rec in self:
            if rec.license_type == 'dogforce_special':
                rec.status_label = 'DogForce Special — Active (no expiry)'
            elif rec.status == 'preview':
                days = rec.remaining_preview_days
                rec.status_label = f'Trial — {days} day(s) remaining'
            elif rec.status == 'active':
                tier_name = dict(rec._fields['tier'].selection).get(rec.tier, rec.tier or '')
                rec.status_label = f'Active — {tier_name}'
            elif rec.status == 'expired':
                rec.status_label = 'Expired — renew subscription to continue'
            elif rec.status == 'suspended':
                rec.status_label = 'Suspended — contact billing support'
            else:
                rec.status_label = rec.status or ''

    def is_feature_available(self, feature_code):
        self.ensure_one()
        if self.license_type == 'dogforce_special':
            return True
        if self.status not in ('preview', 'active'):
            return False
        allowed_tiers = FEATURE_TIERS.get(feature_code, [])
        if self.status == 'preview':
            return True
        return (self.tier or '') in allowed_tiers

    def get_remaining_preview_days(self):
        self.ensure_one()
        if self.status != 'preview' or not self.preview_expiry:
            return None
        now = fields.Datetime.now()
        delta = self.preview_expiry - now
        return max(0, delta.days)

    def validate_license(self):
        self.ensure_one()
        endpoint = self.env['ir.config_parameter'].sudo().get_param(
            'security_licensing.validation_endpoint', default=''
        )
        if not endpoint:
            _logger.warning('security_licensing: validation_endpoint not configured — skipping.')
            return False

        payload = {
            'licenseKey': self.license_key,
            'installationId': self.env['ir.config_parameter'].sudo().get_param(
                'web.base.url', default=''
            ),
        }
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            _logger.error('License validation failed: %s', exc)
            return False

        old_status = self.status
        vals = {
            'status': data.get('status', self.status),
            'last_validated': fields.Datetime.now(),
        }
        if data.get('tier'):
            vals['tier'] = data['tier']
        if data.get('guardLimit') is not None:
            vals['guard_limit'] = data['guardLimit']
        if data.get('expiresAt'):
            if vals['status'] == 'preview':
                vals['preview_expiry'] = fields.Datetime.from_string(data['expiresAt'])
            else:
                vals['subscription_expiry'] = fields.Datetime.from_string(data['expiresAt'])
        self.write(vals)

        if old_status != vals['status']:
            self.env['security.license.log'].create({
                'license_id': self.id,
                'old_status': old_status,
                'new_status': vals['status'],
                'message': f"Status changed via validation API: {old_status} → {vals['status']}",
            })
        return True

    def action_validate_now(self):
        result = self.validate_license()
        if result:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('License Validated'),
                    'message': self.status_label,
                    'type': 'success',
                    'sticky': False,
                },
            }
        raise UserError(_('Validation failed. Check that the validation endpoint is configured in System Parameters.'))

    def action_enter_license_key(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'license.key.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_license_id': self.id if self else False},
        }

    @api.model
    def cron_validate_all(self):
        active = self.search([('status', 'not in', ['expired'])], limit=1)
        if active:
            active.validate_license()
        self._send_trial_warning_notifications()

    def _send_trial_warning_notifications(self):
        preview_licenses = self.search([('status', '=', 'preview')])
        for lic in preview_licenses:
            days = lic.get_remaining_preview_days()
            if days is not None and days <= 2:
                lic._post_trial_warning_message(days)

    def _post_trial_warning_message(self, days_remaining):
        body = _(
            'Your DeployGuard OS trial expires in <strong>%(days)s day(s)</strong>. '
            'Visit your billing portal to activate a subscription and keep your data.',
            days=days_remaining,
        )
        self.message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')


class SecurityLicenseLog(models.Model):
    _name = 'security.license.log'
    _description = 'License Status Change Log'
    _order = 'changed_at desc'

    license_id = fields.Many2one('security.license', string='License', required=True,
                                  ondelete='cascade', index=True)
    changed_at = fields.Datetime(string='Changed At', default=fields.Datetime.now, readonly=True)
    old_status = fields.Char(string='Previous Status', readonly=True)
    new_status = fields.Char(string='New Status', readonly=True)
    message = fields.Char(string='Details', readonly=True)
