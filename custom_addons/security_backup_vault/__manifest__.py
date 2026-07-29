# -*- coding: utf-8 -*-
{
    'name': 'DeployGuard Backup Vault & Offsite Sync',
    'version': '19.0.1.0.0',
    'summary': 'Automated WAL point-in-time recovery, filestore snapshotting, Cloudflare R2 encrypted offsite backups, and disk alerts.',
    'description': """
        DeployGuard Enterprise Backup Vault & Offsite Sync Module.
        Features:
        - Continuous WAL point-in-time archiving logging.
        - Matched Database + Filestore nightly tarball snapshots with SHA-256 verification.
        - Client-side encrypted Cloudflare R2 offsite backup sync (S3 compatible).
        - Automated pre-deployment snapshots for zero-downtime rollback safety.
        - Weekly throwaway DB integrity restore validation.
        - Disk space monitoring with WhatsApp control room alerts.
    """,
    'category': 'Administration',
    'author': 'Winston Zulu / DogForce Security Services',
    'license': 'LGPL-3',
    'depends': ['base', 'security_base', 'security_ai_whatsapp_bridge'],
    'data': [
        'security/security_backup_security.xml',
        'security/ir.model.access.csv',
        'data/security_backup_cron.xml',
        'wizard/security_backup_restore_wizard_views.xml',
        'views/security_backup_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
