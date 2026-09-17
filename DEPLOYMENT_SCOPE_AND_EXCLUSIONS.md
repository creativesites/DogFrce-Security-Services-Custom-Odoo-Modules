# DeployGuard Deployment Scope, Module Exclusions & Safeguards

**Target Deployment:** DogForce Security Services Namibia  
**Production Server:** Single Physical/VPS Host (12 GB RAM)  
**Production Database:** `dogforce_prod` (Port `8069`)  
**Staging Database:** `dogforce_staging` (Port `8070`)  
**Document Version:** 1.0 (July 2026)

---

## 1. Executive Summary & Policy

This document establishes the official operational boundaries and automated code isolation rules for the **DogForce Security Services Namibia** deployment stack. 

To prevent cross-regional data pollution, database schema collisions, and tax compliance errors, **Zambian localization, ZRA Smart Invoice modules, and Zambian demo datasets are strictly excluded from this server environment**.

All automated deployment and promotion scripts (`scripts/promote_staging_to_prod.sh`) enforce this policy automatically via strict module blocklists and pre-flight database audits.

---

## 2. Module Matrix: Included vs Excluded

### 🚫 **Prohibited & Excluded Modules (Blocklist)**

The following modules **MUST NOT** be installed or updated on `dogforce_prod` or `dogforce_staging`:

| Module Name | Purpose / Reason for Exclusion |
|---|---|
| `security_l10n_zm` | Zambian statutory tax rules (NAPSA, NHIMA, PAYE). *Excluded: Namibia uses SSC and Namibian PAYE thresholds (`security_l10n_na`).* |
| `security_zra_invoice` | Zambia Revenue Authority (ZRA) Smart Invoice fiscalization API. *Excluded: Not applicable to Namibian tax jurisdiction.* |
| `security_demo_data_zm` | Demo seed data for Sentinel Security Zambia Ltd. *Excluded: Production database must remain clean and Namibian-focused.* |
| `security_demo_zambia_site` | Alibaba Cloud Zambia Demo Suite Meta-Module. *Excluded: Intended exclusively for Alibaba Cloud Demo Server (`47.84.205.81`).* |

---

### ✅ **Approved Namibian Deployment Suite**

The following modules comprise the authorized DeployGuard Namibia suite:

| Module Name | Category / Description |
|---|---|
| `security_base` | Core Security Master Data (Guard Profiles, Ranks, Gear Issue) |
| `security_operations` | Operations Control (Site Profiles, Guard Posts, Shift Boards) |
| `security_compliance_roster` | Roster Planning & SLA Compliance Tracking |
| `security_attendance` | Attendance Sheet & Posting Logs |
| `security_leave` | Guard Leave Management & Balance Tracking |
| `security_payroll_core` | Base Payroll Engine |
| **`security_l10n_na`** | **Namibia Localization: Social Security Commission (SSC), NTA Levy, Namibian PAYE** |
| `security_loans` | Guard Salary Advances & Deduction Schedules |
| `security_discipline` | Disciplinary Offenses, Incidents & Fines |
| `security_equipment` | Uniform & Firearms Equipment Issuance |
| `security_billing` | Client Service Contracts & Monthly Guard Billing |
| `security_fleet` | Patrol Vehicle Fleet, Mileage & Fuel Tracking |
| `security_ai_engine` | AI Control Room Analytics |
| **`security_ai_whatsapp_bridge`** | **WhatsApp Control Room Assistant (`OWNER STATS`, Attendance Check-ins)** |
| **`security_backup_vault`** | **Automated WAL Backups, Filestore Tarballs & Cloudflare R2 Offsite Sync** |
| `security_suite` | All-In-One Suite Installer (Namibia Profile) |
| `security_client_onboarding` | Client/site/shift-requirement/billing onboarding wizard -- in active daily use (see docs/ROSTERING_SIMPLIFICATION_PLAN.md), but was missing from this list entirely until now |

> **`security_deployguard_bridge` is explicitly NOT in this list.** It is
> scaffolded in the repository (see docs/deployguard/BUILD-STATUS-AND-PHASE-
> PLAN.md Phase 2) but per the cowork ground rules stays uninstalled on every
> database, staging included, until the desktop app has something to talk to
> it about.
>
> **`security_adoption` is also explicitly NOT in this list**, for a
> different and more serious reason: docs/deployguard/09-adoption-engine.md
> itself gates everything past §5.2 on a privacy/legal review and an
> employment-contract notice that do not exist yet. It was built anyway on
> an explicit, logged product-owner override that accepts that risk (see
> BUILD-STATUS-AND-PHASE-PLAN.md Phase 5's decisions section) -- the module
> is real and tested, but installing it on `dogforce_prod` or `dogforce_
> staging` before that review happens would mean measuring and scoring real
> employees' work without the legal groundwork the spec's own author
> required. Do not add it to this list, or to any deployment script's
> module argument, until that review exists and someone updates this note
> to say so.
>
> **Known gap, not fixed by this note:** `security_shell`, `security_theme`
> and `security_notifications` are also missing from this approved list
> despite being production-critical (`security_shell` especially -- see
> [00-current-state.md](docs/deployguard/00-current-state.md) §3.1), and
> `security_suite` is still listed as the baseline installer here and in
> `scripts/setup_staging.sh` even though the cowork board (`docs/deployguard/
> cowork/README.md`) records this as fixed ("T-6... Done"). It is not fixed
> in this file. This is the same pattern as the `security_deployguard_bridge`
> discrepancy in BUILD-STATUS-AND-PHASE-PLAN.md §4.1: work marked Done on
> that board that isn't reflected in the repository. Treat T-6 as unverified
> until someone actually edits this file and `scripts/setup_staging.sh`.



---

## 3. Automated System Safeguards

Our deployment automation enforces these exclusions programmatically at every layer:

### **Safeguard 1: Automated Promotion Script Blocklist**
The `scripts/promote_staging_to_prod.sh` script scans all requested upgrade arguments against a hardcoded blocklist:
```bash
EXCLUDED_MODULES=("security_l10n_zm" "security_zra_invoice" "security_demo_data_zm")
```
If an excluded module name is detected in the upgrade string, the script **immediately aborts execution with exit code 1** before touching the production container.

### **Safeguard 2: Pre-Flight Database Audit**
Before running any upgrade, `scripts/promote_staging_to_prod.sh` executes a live ORM query against `ir.module.module` in `dogforce_prod`:
```python
excluded = ['security_l10n_zm', 'security_zra_invoice', 'security_demo_data_zm']
installed_excluded = env['ir.module.module'].search([('name', 'in', excluded), ('state', '=', 'installed')])
```
If any excluded module is found installed in the database, promotion halts immediately.

### **Safeguard 3: Pre-Deploy Rollback Snapshot**
Seconds before any production code promotion:
1. `security_backup_vault` triggers an automatic pre-deploy snapshot (`pg_dump` + filestore tarball).
2. The checksum is verified.
3. If the module upgrade fails or raises an error, the script **automatically restores the pre-deploy snapshot** and restarts the stable container.

---

## 4. Server Layout & Port Allocation

| Environment | Database | Container Name | Port | Compose File |
|---|---|---|---|---|
| **Production** | `dogforce_prod` | `dogforce-prod-odoo` | **8069** | `deploy/docker-compose.prod.yml` |
| **Staging (UAT)** | `dogforce_staging` | `dogforce-staging-odoo` | **8070** | `deploy/docker-compose.staging.yml` |
| **WhatsApp Bridge** | — | `dogforce-prod-whatsapp-bridge` | **3000** | `deploy/docker-compose.prod.yml` |

Both `prod` and `staging` stacks mount the exact same `./custom_addons` directory on disk, ensuring **zero code drift** between UAT testing and production promotion.

---

## 5. Promotion Workflow (Staging ➔ Production)

1. **Test on Staging**: Deploy and test changes on `http://localhost:8070` (`dogforce_staging`).
2. **User Acceptance Sign-Off**: Confirm operational correctness (rosters, payroll calculations, billing).
3. **Run Automated Promotion**:
   ```bash
   ./scripts/promote_staging_to_prod.sh security_suite
   ```
4. **Verification**: Post-deploy health checks verify system status at `https://dogforcesecurityservices.com`.
