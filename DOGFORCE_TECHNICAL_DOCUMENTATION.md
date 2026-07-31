# DogForce Security Services — DeployGuard Platform Technical Documentation & Architecture Reference

**Client Organization:** DogForce Security Services Namibia  
**System Name:** DeployGuard Enterprise Security OS (Odoo 19)  
**Primary Production Domain:** https://dogforcesecurityservices.com  
**Staging / UAT Domain:** http://staging.dogforcesecurityservices.com  
**Server IP Address:** 199.192.23.46 (12 GB RAM Dedicated VPS)  
**Document Version:** 1.0 (July 2026)

---

## 1. Executive Summary & Management Philosophy

This document serves as the authoritative technical reference for the **DeployGuard Platform** powering DogForce Security Services Namibia. 

To guarantee 99.99% operational uptime for 24/7 control room rosters, payroll processing, and client billing, the system is architected around **managed infrastructure automation**:

1. **Zero-Risk Production Updates**: No changes land on Production without prior UAT validation on an isolated Staging stack.
2. **Automated Rollback Guarantees**: Every update automatically captures a pre-deploy snapshot. If an upgrade encounters an error, the system rolls back to the stable state within seconds.
3. **Continuous Disaster Recovery**: Database changes are continuously recorded via Write-Ahead Log (WAL) archiving, paired with encrypted offsite backups to Cloudflare R2.
4. **Scope & Compliance Protection**: Non-Namibian tax and localization modules are programmatically blocked from installation to prevent database pollution.

---

## 2. Infrastructure Architecture & Dual-Stack Layout

The server utilizes Docker container isolation to run two completely separate environment stacks on a single high-performance host:

```
                               ┌──────────────────────────────────────────────┐
                               │             Nginx Reverse Proxy              │
                               │        (SSL / Port 80 / Port 443)            │
                               └──────┬────────────────────────┬──────────────┘
                                      │                        │
               dogforcesecurityservices.com         staging.dogforcesecurityservices.com
                                      │                        │
                                      ▼                        ▼
                       ┌────────────────────────┐    ┌────────────────────────┐
                       │    PRODUCTION STACK    │    │     STAGING STACK      │
                       │    (dogforce_prod)     │    │   (dogforce_staging)   │
                       ├────────────────────────┤    ├────────────────────────┤
                       │ Odoo 19 (Port 8069)    │    │ Odoo 19 (Port 8070)    │
                       │ Postgres 16 (1GB RAM)  │    │ Postgres 16 (Lean)     │
                       │ WhatsApp Bridge (3000) │    │ (Isolated Filestore)   │
                       └────────────────────────┘    └────────────────────────┘
```

### **Resource Budget Allocation (12 GB RAM Host)**

| Service Component | Environment | Allocated RAM | Configuration / Role |
|---|---|---|---|
| **Production Odoo** | Production | ~3.5 GB | 2 Worker Threads + 1 Cron Thread (`--workers=2`) |
| **Production Postgres** | Production | ~2.5 GB | `shared_buffers=1GB`, Continuous WAL Archiving Enabled |
| **WhatsApp AI Bridge** | Production | ~0.5 GB | Node.js 20 Baileys Transport Container |
| **Staging Odoo** | Staging | ~1.5 GB | 1 Worker Thread (`--workers=1`) for UAT Testing |
| **Staging Postgres** | Staging | ~1.5 GB | Isolated UAT Database (`dogforce_staging`) |
| **Backup Vault Engine** | Host / Cron | ~0.5 GB | Scheduled snapshots & offsite Cloudflare R2 sync |
| **OS & Docker Overhead** | Host OS | ~1.5 GB | AlmaLinux 9, Nginx, Docker Engine |
| **Buffer / Headroom** | Host OS | **~0.5 GB** | Unallocated slack for peak traffic spikes |

---

## 3. Automated Promotion & Deployment Pipeline

Code changes move through a 5-step automated validation pipeline before entering Production:

```
[ Developer Code ] ➔ [ Deploy to Staging ] ➔ [ Operational UAT Sign-Off ] 
                                                        │
                                                        ▼
[ Production Live ] ◄─ [ Health Check ] ◄─ [ Upgrade ] ◄─ [ Pre-Deploy Snapshot ]
```

### **Promotion & Rollback Automation Script (`scripts/promote_staging_to_prod.sh`)**

When an update is initiated, the automated promotion engine executes the following safeguards:

1. **Module Exclusion Audit**: Scans the update request against a strict blocklist (`security_l10n_zm`, `security_zra_invoice`, `security_demo_data_zm`). If a prohibited module is detected, execution halts immediately.
2. **Pre-Deploy Snapshot**: Executes `security.backup.manager.run_pre_deploy_snapshot()` to create a matched database dump (`pg_dump`) and filestore tarball. Computes a SHA-256 checksum.
3. **Database Upgrade**: Stops the live Odoo worker and executes `odoo -u <modules> -d dogforce_prod`.
4. **Post-Deploy Health Check**: Performs HTTP/RPC health checks against `/web/health`.
5. **Automated Rollback**: If step 3 or 4 fails, the script automatically restores the pre-deploy snapshot taken in step 2 and brings production back up on the stable state.

---

## 4. Disaster Recovery & Backup Vault Architecture

Backups are managed by the custom **`security_backup_vault`** Odoo module, operating across a two-tier strategy:

### **Tier 1: Continuous Point-in-Time Recovery (WAL Archiving)**
* PostgreSQL Write-Ahead Logs (WAL) are streamed continuously to `/var/lib/odoo/backups/wal/` every 5 minutes.
* Allows restoring the database to *any exact timestamp* (e.g. "30 seconds before an accidental deletion").

### **Tier 2: Matched Base Backups & Filestore Snapshots**
* **Nightly Full Backup (2:00 AM)**: Pairs a full PostgreSQL dump with an archived tarball of Odoo's attachment filestore (guard photos, PDF payslips, contract documents).
* **SHA-256 Checksum Matching**: Guarantees that a restored database record will always point to its matching PDF attachment on disk.
* **Encrypted Offsite Cloudflare R2 Sync (2:30 AM)**: Nightly backups are encrypted client-side and uploaded to Cloudflare R2 S3 storage (zero egress cost, 100% S3 compatible).
* **Weekly Integrity Restore Test (Sundays 3:00 AM)**: Automatically restores the latest backup into a throwaway test database to confirm data readability.
* **Hourly Disk Space Monitor**: Checks server storage hourly and sends an alert message directly to the executive WhatsApp channel if free disk space drops below 15%.

---

## 5. Scope & Module Isolation Policy

To maintain zero cross-jurisdiction data pollution, the module suite is partitioned:

### **Approved Namibian Production Suite (`security_suite`)**
* `security_base`: Master Data (Guard Profiles, Ranks, Gear)
* `security_operations`: Post Roster Scheduling & Shift Boards
* `security_compliance_roster`: SLA & Compliance Monitoring
* `security_attendance`: Posting Sheets & Check-In Verification
* `security_payroll_core`: Base Payroll Engine
* **`security_l10n_na`**: **Namibia Localization (Social Security Commission, NTA Levy, PAYE)**
* `security_billing`: Client Service Contracts & Billing
* `security_fleet`: Vehicle Patrol & Fuel Logs
* `security_ai_whatsapp_bridge`: Control Room WhatsApp Assistant
* `security_backup_vault`: Automated Backups & Offsite Sync

### **Prohibited / Blocked Modules**
* `security_l10n_zm` *(Zambian Tax & Statutory Localization)*
* `security_zra_invoice` *(Zambia Revenue Authority API)*
* `security_demo_data_zm` *(Sentinel Security Zambia Demo Data)*

---

## 6. Technical Operations Quick Reference

```bash
# 1. View Live Container Logs
docker logs -f dogforce-prod-odoo

# 2. Access Staging Database CLI
docker exec -it dogforce-staging-odoo odoo shell -c /etc/odoo/odoo.conf -d dogforce_staging

# 3. Promote Tested Staging Changes to Production
cd /opt/dogforce
./scripts/promote_staging_to_prod.sh security_suite

# 4. Trigger Manual Offsite Backup Sync
docker exec -it dogforce-prod-odoo odoo shell -c /etc/odoo/odoo.conf -d dogforce_prod -c "env['security.backup.manager'].sudo().run_nightly_full_backup()"
```

---

*Document prepared by Engineering for DogForce Security Services Management.*
