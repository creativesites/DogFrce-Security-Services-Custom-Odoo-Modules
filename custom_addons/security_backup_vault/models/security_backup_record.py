# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class SecurityBackupRecord(models.Model):
    _name = 'security.backup.record'
    _description = 'DeployGuard Backup Record & Audit Log'
    _order = 'created_date desc, id desc'

    name = fields.Char(
        string='Backup Reference',
        required=True,
        readonly=True,
        default=lambda self: _('New Backup'),
        copy=False,
    )
    backup_type = fields.Selection(
        selection=[
            ('full', 'Nightly Full (DB + Filestore)'),
            ('wal', 'Continuous WAL Segment'),
            ('pre_deploy', 'Pre-Deploy Staging Promotion Snapshot'),
            ('manual', 'Manual On-Demand Backup'),
        ],
        string='Backup Type',
        required=True,
        default='full',
        index=True,
    )
    retention_tier = fields.Selection(
        selection=[
            ('daily', 'Daily (30 Days)'),
            ('weekly', 'Weekly (6 Months)'),
            ('monthly', 'Monthly (2+ Years Statutory)'),
            ('yearly', 'Yearly Archive'),
            ('transient', 'Transient / Pre-Deploy Rollback'),
        ],
        string='Retention Tier',
        default='daily',
        required=True,
        index=True,
    )
    database_name = fields.Char(string='Target Database', required=True, index=True)
    db_snapshot_path = fields.Char(string='DB Snapshot File Path')
    filestore_snapshot_path = fields.Char(string='Filestore Snapshot File Path')
    checksum_sha256 = fields.Char(string='SHA-256 Checksum Verification', copy=False)
    file_size_bytes = fields.Integer(string='File Size (Bytes)')
    file_size_formatted = fields.Char(string='Formatted Size', compute='_compute_file_size_formatted', store=True)

    state = fields.Selection(
        selection=[
            ('draft', 'Initiated'),
            ('completed', 'Completed & Verified'),
            ('failed', 'Failed'),
            ('purged', 'Expired / Purged'),
        ],
        string='Status',
        default='draft',
        required=True,
        index=True,
    )
    error_log = fields.Text(string='Execution / Error Log', readonly=True)

    offsite_synced = fields.Boolean(string='Synced Offsite (Cloudflare R2)', default=False, index=True)
    offsite_synced_date = fields.Datetime(string='Offsite Sync Timestamp', readonly=True)
    offsite_url = fields.Char(string='Offsite Storage Reference', readonly=True)

    verified = fields.Boolean(string='Weekly Restore Verified', default=False, index=True)
    restore_tested_date = fields.Datetime(string='Last Restore Test Timestamp', readonly=True)

    created_date = fields.Datetime(string='Created Date', default=fields.Datetime.now, required=True, index=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New Backup')) == _('New Backup'):
                seq = self.env['ir.sequence'].next_by_code('security.backup.record') or 'BK'
                vals['name'] = f"{seq}-{fields.Date.today().strftime('%Y%m%d')}"
        return super().create(vals_list)

    @api.depends('file_size_bytes')
    def _compute_file_size_formatted(self):
        for rec in self:
            bytes_val = rec.file_size_bytes or 0
            if bytes_val >= 1073741824:
                rec.file_size_formatted = f"{bytes_val / 1073741824:.2f} GB"
            elif bytes_val >= 1048576:
                rec.file_size_formatted = f"{bytes_val / 1048576:.2f} MB"
            elif bytes_val >= 1024:
                rec.file_size_formatted = f"{bytes_val / 1024:.2f} KB"
            else:
                rec.file_size_formatted = f"{bytes_val} Bytes"

    def action_verify_offsite_sync(self):
        self.ensure_one()
        manager = self.env['security.backup.manager'].sudo()
        manager._sync_single_record_offsite(self)

    def action_trigger_restore_test(self):
        self.ensure_one()
        manager = self.env['security.backup.manager'].sudo()
        manager._test_single_backup_integrity(self)
