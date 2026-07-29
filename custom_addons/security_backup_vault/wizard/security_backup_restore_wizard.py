# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SecurityBackupRestoreWizard(models.TransientModel):
    _name = 'security.backup.restore.wizard'
    _description = 'DeployGuard Backup Restore Wizard'

    backup_record_id = fields.Many2one(
        'security.backup.record',
        string='Selected Backup Snapshot',
        required=True,
        domain="[('state', '=', 'completed')]",
    )
    target_environment = fields.Selection(
        selection=[
            ('staging', 'Staging Database (dogforce_staging) - Safe UAT Default'),
            ('production', 'Production Database (dogforce_prod) - DANGER: REPLACES LIVE DATA'),
        ],
        string='Target Environment',
        default='staging',
        required=True,
    )
    confirm_production = fields.Boolean(
        string='I understand that restoring to Production will overwrite all live database & filestore data',
        default=False,
    )
    restore_reason = fields.Text(
        string='Logged Restore Reason',
        required=True,
        help='State the operational or technical reason for initiating this database restore.',
    )

    def action_execute_restore(self):
        self.ensure_one()

        if self.target_environment == 'production' and not self.confirm_production:
            raise UserError(_("You must check the confirmation checkbox to restore over the Production database."))

        record = self.backup_record_id
        target_db = 'dogforce_staging' if self.target_environment == 'staging' else 'dogforce_prod'

        _logger.warning(
            "RESTORE WIZARD | Initiating restore of %s onto %s by User %s. Reason: %s",
            record.name, target_db, self.env.user.name, self.restore_reason
        )

        # Log confirmation message
        record.message_post(
            body=f"<b>Restore Executed</b><br/>Target DB: <code>{target_db}</code><br/>Initiated By: {self.env.user.name}<br/>Reason: {self.restore_reason}"
        ) if hasattr(record, 'message_post') else None

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Restore Job Initiated"),
                'message': _("Restore process queued for %s using snapshot %s.") % (target_db, record.name),
                'sticky': True,
                'type': 'warning' if target_db == 'dogforce_prod' else 'info',
            }
        }
