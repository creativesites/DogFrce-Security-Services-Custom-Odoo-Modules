# DeployGuard Alibaba Cloud Demo Site — Deployment Scope, Module Exclusions & Safeguards

**Target Deployment:** Sentinel Security Services Zambia & Regional Demo Server  
**Server Host IP:** `47.84.205.81` (Alibaba Cloud Singapore Node)  
**Primary Demo Database:** `zambia-demo` (Port `8069`)  
**Staging/Dev Database:** `dogforce_dev` (Port `8069`)  
**Document Version:** 1.0 (July 2026)

---

## 1. Scope & Module Isolation Policy

This document establishes the official operational boundaries and automated code isolation rules for the **Alibaba Cloud Demo Site Server**.

To present an authentic Zambian demonstration environment and prevent database schema collisions, **Namibian statutory localization (`security_l10n_na`) and Namibian demo datasets (`security_demo_data`) are strictly excluded from this server environment**.

---

## 2. Module Matrix: Included vs Excluded

### 🚫 **Prohibited & Excluded Modules (Blocklist for Alibaba Demo Server)**

The following modules **MUST NOT** be activated or updated on `zambia-demo` or `dogforce_dev`:

| Module Name | Purpose / Reason for Exclusion |
|---|---|
| `security_l10n_na` | Namibian statutory tax rules (SSC, NTA Levy, Namibian PAYE). *Excluded: Demo server is configured for Zambian Tax Jurisdiction (`security_l10n_zm`).* |
| `security_demo_data` | Namibian DogForce demo data. *Excluded: Demo server uses Sentinel Security Zambia demo dataset (`security_demo_data_zm`).* |

---

### ✅ **Approved Zambian Demo Suite (`security_demo_zambia_site`)**

The following modules comprise the authorized suite for the Alibaba Cloud Demo Server:

| Module Name | Category / Description |
|---|---|
| `security_base` | Master Data (Guard Profiles, Ranks, Gear Issue) |
| `security_operations` | Operations Control (Site Profiles, Guard Posts, Shift Boards) |
| `security_shift_planner` | Interactive Rostering Hub, Roster Board & Command Center |
| `security_compliance_roster` | SLA & Compliance Monitoring |
| `security_attendance` | Attendance Sheet & Posting Logs |
| `security_leave` | Guard Leave Management & Balance Tracking |
| `security_payroll_core` | Base Payroll Engine |
| **`security_l10n_zm`** | **Zambia Localization: NAPSA, NHIMA, Zambian PAYE Thresholds** |
| **`security_zra_invoice`** | **Zambia Revenue Authority (ZRA) Smart Invoice API Integration** |
| **`security_demo_data_zm`** | **Sentinel Security Zambia Sample Seed Dataset** |
| **`security_demo_site`** | **Interactive Demo Login Panel & Quick Role Switcher** |
| **`security_demo_zambia_site`** | **Master Demo Suite Meta-Installer** |
| `security_loans` | Guard Salary Advances & Deduction Schedules |
| `security_discipline` | Disciplinary Offenses, Incidents & Fines |
| `security_equipment` | Uniform & Firearms Equipment Issuance |
| `security_billing` | Client Service Contracts & Monthly Guard Billing |
| `security_fleet` | Patrol Vehicle Fleet, Mileage & Fuel Tracking |
| `security_ai_engine` | AI Control Room Analytics |
| **`security_ai_whatsapp_bridge`** | **WhatsApp Control Room Assistant (`OWNER STATS`, Attendance Check-ins)** |

---

## 3. Automated System Safeguards

Our deployment automation enforces these exclusions programmatically:

### **Safeguard 1: Automated Deployment Script Blocklist**
The `scripts/deploy_alibaba_demo.sh` script scans the database before running updates against a blocklist:
```bash
EXCLUDED_MODULES=("security_l10n_na" "security_demo_data")
```
If a prohibited module is detected as installed on the database, execution **immediately aborts** with an error alert.

### **Safeguard 2: Atomic Update via `security_demo_zambia_site`**
All module updates are run using the meta-module `security_demo_zambia_site`. This ensures that all dependencies are re-evaluated and loaded in a single transaction.

---

## 4. Deployment Workflow

1. **Local Development & Validation**: Test changes on local workspace.
2. **Execute Deployment Script**:
   ```bash
   ./scripts/deploy_alibaba_demo.sh
   ```
3. **Verification**: Confirm live status at `http://47.84.205.81:8069/web`.
