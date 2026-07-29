# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    backup_storage_path = fields.Char(
        string='Backup Storage Path',
        config_parameter='security_backup.storage_path',
        default='/var/lib/odoo/backups',
    )
    backup_disk_alert_threshold = fields.Float(
        string='Low Disk Space Alert Threshold (%)',
        config_parameter='security_backup.disk_alert_threshold',
        default=15.0,
    )
    backup_alert_whatsapp_number = fields.Char(
        string='WhatsApp Alert Phone Number',
        config_parameter='security_backup.alert_whatsapp_number',
    )

    r2_endpoint = fields.Char(
        string='Cloudflare R2 S3 Endpoint URL',
        config_parameter='security_backup.r2_endpoint',
        placeholder='https://<account_id>.r2.cloudflarestorage.com',
    )
    r2_bucket = fields.Char(
        string='R2 Bucket Name',
        config_parameter='security_backup.r2_bucket',
        placeholder='dogforce-production-backups',
    )
    r2_access_key = fields.Char(
        string='R2 Access Key ID',
        config_parameter='security_backup.r2_access_key',
    )
    r2_secret_key = fields.Char(
        string='R2 Secret Access Key',
        config_parameter='security_backup.r2_secret_key',
    )
