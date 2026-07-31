# DogForce Security Services — Alibaba Cloud Demo Site Technical Documentation & Architecture Reference

**Client Organization:** Sentinel Security Services Zambia & Regional Demo Prospective Clients  
**System Name:** DeployGuard Enterprise Security OS Demo Instance (Odoo 19)  
**Demo Server Domain/IP:** `http://47.84.205.81:8069`  
**Server Hosting Provider:** Alibaba Cloud (Singapore / Regional Gateway Node)  
**Document Version:** 1.0 (July 2026)

---

## 1. Executive Summary & Demo Philosophy

This document serves as the authoritative technical and operational reference for the **DeployGuard Demo Platform** hosted on Alibaba Cloud (`47.84.205.81`).

The Alibaba Cloud Demo environment provides an interactive, full-featured demonstration platform of the DeployGuard Security OS configured for **Zambian Tax & Statutory Operations** (NAPSA, NHIMA, PAYE, ZRA Smart Invoice fiscalization) and control room WhatsApp AI assistant workflows.

### **Core Operational Directives:**
1. **Zambian Localization Focus**: Configured for Zambian Kwacha (ZMW) currency, NAPSA pensions, NHIMA health insurance, ZRA tax tiers, and Sentinel Security Zambia sample datasets.
2. **Automated Continuous Deployment**: Local developer workspace updates are automatically deployed to the Alibaba Cloud server via standardized sync and update scripts (`scripts/deploy_alibaba_demo.sh`).
3. **Strict Regional Isolation**: Namibian localization modules (`security_l10n_na`) and Namibian demo data (`security_demo_data`) are programmatically excluded from installation on this server.
4. **Dual-Database Architecture**: Maintains two isolated PostgreSQL databases (`zambia-demo` for clean client demonstrations and `dogforce_dev` for staging/dev checks).

---

## 2. Infrastructure & Docker Container Topology

The server uses Docker containerization running on an Alibaba Cloud ECS instance:

```
                               ┌──────────────────────────────────────────────┐
                               │           Alibaba Cloud Public IP            │
                               │               47.84.205.81                    │
                               └──────┬────────────────────────┬──────────────┘
                                      │                        │
                               Port 8069 / HTTP         Port 3000 / HTTP
                                      │                        │
                                      ▼                        ▼
                       ┌────────────────────────┐    ┌────────────────────────┐
                       │   ODOO APPLICATION     │    │  WHATSAPP AI BRIDGE    │
                       │  (dogforce-demo-odoo)  │    │ (dogforce-demo-wb)     │
                       ├────────────────────────┤    ├────────────────────────┤
                       │ Odoo 19 Enterprise     │    │ Node.js 20 Baileys     │
                       │ Mounted /extra-addons  │    │ WhatsApp Web Socket    │
                       └───────────┬────────────┘    └────────────────────────┘
                                   │
                                   ▼
                       ┌────────────────────────┐
                       │  POSTGRESQL DATABASE   │
                       │   (dogforce-demo-db)   │
                       ├────────────────────────┤
                       │ Postgres 16 Engine     │
                       │ Databases:             │
                       │ - zambia-demo          │
                       │ - dogforce_dev         │
                       └────────────────────────┘
```

---

## 3. Server Access & Login Reference

### **Web Access URLs:**
- **Primary Demo Portal:** `http://47.84.205.81:8069/web`
- **Database Selector / Manager:** `http://47.84.205.81:8069/web/database/manager`

### **Database Credentials & System Secrets:**
* **Master Admin Password:** `admin123`
* **PostgreSQL Host:** `dogforce-demo-db` (Port `5432`)
* **PostgreSQL User:** `odoo`
* **PostgreSQL Password:** `odoo_secure_2026`

### **Active Databases:**
1. **`zambia-demo`**: Primary Zambian demo database with Sentinel Security Zambia Ltd master records, client sites, shift templates, and sample rosters.
2. **`dogforce_dev`**: Secondary development/staging database.

---

## 4. Demo Meta-Module (`security_demo_zambia_site`)

To streamline updates and guarantee that all required Zambian demo components are installed atomically, a dedicated meta-module is maintained:

* **Module Name:** `security_demo_zambia_site`
* **Location:** `custom_addons/security_demo_zambia_site`
* **Dependencies:**
  - `security_suite` (Core Security OS)
  - `security_l10n_zm` (Zambian Statutory Taxes: NAPSA, NHIMA, PAYE)
  - `security_zra_invoice` (ZRA Smart Invoice Fiscalization)
  - `security_demo_data_zm` (Sentinel Security Zambia Sample Records)
  - `security_demo_site` (Interactive Demo Login Panel & Portal)
  - `security_shift_planner` (Rostering Hub, Roster Board, Weekly Check-in)
  - `security_ai_whatsapp_bridge` (Control Room WhatsApp AI Assistant)

Single-command update execution on any demo database:
```bash
docker exec -i dogforce-demo-odoo odoo -d zambia-demo -u security_demo_zambia_site --stop-after-init
```

---

## 5. Scope & Module Isolation Policy

### ✅ **Approved Zambian Demo Suite**
* `security_base`: Master Data (Guards, Ranks, Equipment)
* `security_operations`: Post Roster Scheduling & Site Hub
* `security_shift_planner`: Interactive Rostering Hub & Command Center
* `security_compliance_roster`: SLA Compliance Monitoring
* `security_attendance`: Posting Sheets & Check-In Verification
* `security_payroll_core`: Base Payroll Engine
* **`security_l10n_zm`**: **Zambia Localization (NAPSA, NHIMA, Zambian PAYE)**
* **`security_zra_invoice`**: **ZRA Smart Invoice Integration**
* **`security_demo_data_zm`**: **Sentinel Security Zambia Seed Data**
* **`security_demo_site`**: **Demo Site Login Panel & Role Shortcuts**
* **`security_demo_zambia_site`**: **Master Demo Suite Meta-Installer**

### 🚫 **Prohibited & Excluded Modules (Blocklist)**
* `security_l10n_na` *(Namibia Statutory Localisation)*
* `security_demo_data` *(Namibian DogForce Demo Data)*
* *Future non-Zambian regional localizations (e.g. Botswana, South Africa)*

---

## 6. Automated Deployment & Update Pipeline

Updates to the Alibaba Cloud Demo Server are executed using the automated deployment script (`scripts/deploy_alibaba_demo.sh`).

### **Deployment Execution Steps:**
```bash
# 1. Execute Automated 1-Click Deployment Script
./scripts/deploy_alibaba_demo.sh
```

### **What the Script Does Automatically:**
1. **Clean Rsync**: Transfers updated `custom_addons/` code to `/opt/dogforce/custom_addons/` on `47.84.205.81`.
2. **Exclusion Pre-Flight Audit**: Scans active modules on `zambia-demo` and `dogforce_dev` to verify no Namibian modules (`security_l10n_na`, `security_demo_data`) are activated.
3. **Atomic Suite Upgrade**: Upgrades both `zambia-demo` and `dogforce_dev` databases using `security_demo_zambia_site`.
4. **Container Restart**: Restarts `dogforce-demo-odoo` container to reload minified web client assets.
5. **Health Verification**: Performs live HTTP query against `http://47.84.205.81:8069/web`.

---

*Document prepared by Engineering for DogForce / Sentinel Security Systems Management.*
