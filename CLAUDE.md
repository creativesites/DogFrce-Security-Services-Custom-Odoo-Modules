# CLAUDE.md — DogForce Security Services Odoo Modules

Quick-reference for AI assistants and developers working in this repo.

---

## Project identity

| Key | Value |
|-----|-------|
| Product | DogForce Security Services Suite |
| Odoo version | 19.0 (Community) |
| Language | Python 3.12, OWL/JS, XML |
| Repo | `creativesites/dogfrce-security-services-custom-odoo-modules` |
| Main branch | `main` |

---

## Live server — Alibaba Cloud ECS

> **This is the only server. Always work against these containers.**

| Detail | Value |
|--------|-------|
| Provider | Alibaba Cloud ECS, Ubuntu 22.04 LTS |
| Internal IP | `172.21.166.25` |
| Project root | `/opt/dogforce` |
| Compose file | `/opt/dogforce/docker-compose.yml` |
| Compose project name | `dogforce-demo` |

### Active containers

| Container | Role | Ports |
|-----------|------|-------|
| `dogforce-demo-odoo-1` | **Active Odoo (use this one)** | `0.0.0.0:8069→8069`, `0.0.0.0:8072→8072` |
| `dogforce-demo-db-1` | **Active PostgreSQL** | internal only |
| `dogforce-odoo-1` | Old/backup Odoo — not serving anything | none |
| `dogforce-db-1` | Old PostgreSQL (paired with above) | internal only |

### Active database

| Detail | Value |
|--------|-------|
| Database name | `dogforce-demo-two` |
| DB user | `odoo` |
| DB password | `odoo_secure_2026` |
| DB host (inside container) | `db` |
| DB port | `5432` |

### Volume mounts (`dogforce-demo-odoo-1`)

| Host path | Container path | Purpose |
|-----------|---------------|---------|
| `/opt/dogforce/conf/odoo.conf` | `/etc/odoo/odoo.conf` | Odoo config |
| `/opt/dogforce/custom_addons` | `/mnt/extra-addons` | All custom modules |
| `/opt/dogforce/filestore` | `/var/lib/odoo` | Attachments / filestore |

### `odoo.conf` (active)

```ini
[options]
admin_passwd = DogForce@2026!
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo_secure_2026
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons
data_dir = /var/lib/odoo
proxy_mode = True
list_db = True
without_demo = False
workers = 2
```

---

## Common server commands

### Pull latest code

```bash
cd /opt/dogforce && git pull origin main
```

### Install all custom modules (fresh DB)

```bash
docker exec dogforce-demo-odoo-1 odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce-demo-two \
  -i security_base,security_operations,security_attendance,security_accounting_controls,security_ai_engine,security_billing,security_client_reports,security_demo_data,security_demo_site,security_discipline,security_documents,security_dogforce_migration,security_equipment,security_fleet,security_help,security_leave,security_licensing,security_loans,security_mobile,security_notifications,security_payroll_core,security_reporting,security_shift_planner,security_suite,security_theme,security_zra_invoice \
  --stop-after-init \
  --no-http \
  --workers 0 2>&1 | tee /tmp/install.log
```

> Excludes `security_l10n_na` and `security_l10n_zm` (Zambian/Namibian localisation — install separately if needed).

### Upgrade specific modules after a code change

```bash
docker exec dogforce-demo-odoo-1 odoo \
  -c /etc/odoo/odoo.conf \
  -d dogforce-demo-two \
  -u security_operations,security_shift_planner \
  --stop-after-init \
  --no-http \
  --workers 0
```

### Restart Odoo container

```bash
docker restart dogforce-demo-odoo-1
```

### Tail live Odoo logs

```bash
docker logs -f dogforce-demo-odoo-1
```

### Check all container status

```bash
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

---

## Module list

All custom modules live in `/opt/dogforce/custom_addons/` on the server and `custom_addons/` in this repo.

| Module | Description |
|--------|-------------|
| `security_base` | Shared models and config |
| `security_operations` | Sites, posts, roster batches, slots, shift requirements |
| `security_attendance` | Guard attendance tracking |
| `security_accounting_controls` | Accounting controls |
| `security_ai_engine` | AI scoring / suggestions |
| `security_billing` | Client billing and invoicing |
| `security_client_reports` | Excel/PDF roster, attendance, billing exports |
| `security_demo_data` | Demo guard/site data (not for production) |
| `security_demo_site` | Demo site config |
| `security_discipline` | Disciplinary module |
| `security_documents` | Document management |
| `security_dogforce_migration` | One-time data migration utilities |
| `security_equipment` | Equipment & asset tracking |
| `security_fleet` | Fleet & guard transport |
| `security_help` | Help centre |
| `security_leave` | Leave management |
| `security_licensing` | Guard licensing & certification |
| `security_loans` | Guard loans |
| `security_mobile` | Mobile API layer |
| `security_notifications` | In-app notification system |
| `security_payroll_core` | Payroll computation |
| `security_reporting` | Reporting dashboards |
| `security_shift_planner` | Rostering Hub, Roster Board, Weekly Check-in OWL views |
| `security_suite` | Meta-module bundling the suite |
| `security_theme` | White-label branding |
| `security_zra_invoice` | ZRA Smart Invoice (Zambia) |
| `security_l10n_na` | Namibia localisation _(install separately)_ |
| `security_l10n_zm` | Zambia localisation _(install separately)_ |

---

## Architecture notes

- **OWL components** (Odoo 19) are registered via `registry.category("actions").add()` — no legacy widget class.
- **Roster Board** (`security_shift_planner`): kanban-style drag-and-drop assignment view.
- **Rostering Hub** (`security_shift_planner`): primary scheduling workspace — sidebar nav, weekly grid, suggestions panel, mobile bottom-nav.
- **Weekly Check-in** (`security_shift_planner`): lightweight attendance confirmation view.
- Client actions registered in `views/security_shift_planner_client_actions.xml`.

---

## Key files

| File | Purpose |
|------|---------|
| `custom_addons/security_operations/models/security_operations.py` | Core models: `SecurityRosterBatch`, `SecurityRosterSlot`, `SecurityPost`, etc. |
| `custom_addons/security_shift_planner/static/src/js/rostering_hub.js` | Rostering Hub OWL component |
| `custom_addons/security_shift_planner/static/src/xml/rostering_hub.xml` | Rostering Hub template |
| `custom_addons/security_shift_planner/static/src/css/rostering_hub.css` | Rostering Hub styles |
| `DEPLOYMENT.md` | Full deployment, rollback, backup procedures |
| `ARCHITECTURE.md` | System component map |
| `API.md` | Mobile API reference |
