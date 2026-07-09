# DogForce / DeployGuard — Claude Code Guide

Quick reference for working on this repo with Claude Code. Everything Claude needs to understand the stack, deploy changes, and build the mobile app without asking questions.

---

## Stack overview

| Layer | Tech |
|---|---|
| Backend | Odoo 17 Community, Python 3.12, PostgreSQL |
| Custom modules | `custom_addons/` — all prefixed `security_*` |
| Mobile app | Expo SDK 54, React Native 0.81, expo-router v6 |
| Mobile API | Odoo JSON-RPC + custom REST endpoints in `security_mobile` |
| Build system | EAS (Expo Application Services) — Android APK internal distribution |

---

## Demo server

| | |
|---|---|
| **IP / URL** | `http://47.84.205.81:8069` |
| **SSH** | `ssh root@47.84.205.81` |
| **Odoo admin password** | `admin123` |
| **Database name** | `dogforce-demo` |
| **DB host (Render PG)** | `dpg-d8hu5gtdt1ts73enc480-a.singapore-postgres.render.com` |
| **DB user** | `odoo` |
| **DB password** | `umDKFz8bHRvq7ZGy7nJlYznWoZq1ZW7l` |
| **Docker container** | `dogforce-demo-odoo-1` |
| **Remote addons path** | `/opt/dogforce/custom_addons` |

### Demo user accounts (Odoo)

All demo accounts use password **`Demo2026!`**

| Role | Display name | Login | Password | Access |
|---|---|---|---|---|
| System Admin (Owner) | Demo Admin | `demo.admin@dogforce.demo` | `Demo2026!` | Full platform — settings, payroll, billing, AI assistant |
| Operations Manager | Demo Manager | `demo.manager@dogforce.demo` | `Demo2026!` | Rosters, attendance, leave approvals, client sites |
| Field Operator (Supervisor) | Demo Operator | `demo.operator@dogforce.demo` | `Demo2026!` | Posting console, guard records, incidents, equipment |
| Read-Only Viewer | Demo Viewer | `demo.viewer@dogforce.demo` | `Demo2026!` | View dashboards, reports, attendance — no edits |
| Odoo superadmin | — | `admin` | `admin123` | Full Odoo backend incl. technical menus |

> Demo accounts are seeded by `custom_addons/security_demo_site/data/demo_accounts.xml`.
> To reset a demo account password: `Settings → Users → [user] → Save` (Odoo re-hashes on save).

### Mobile app role mapping

The mobile app maps Odoo users to roles by checking the login/name string:

| Odoo account | Mobile role | App section |
|---|---|---|
| `demo.admin@dogforce.demo` | `owner` | Owner dashboard tabs |
| `demo.manager@dogforce.demo` | `manager` | Manager dashboard tabs |
| `demo.operator@dogforce.demo` | `supervisor` | Supervisor tabs |

---

## Deploying / updating Odoo modules

### Update specific modules (most common)

```bash
bash scripts/update_modules.sh security_mobile security_reporting
```

This rsyncs the module(s) to the server, restarts the Docker container, waits 20 s, and does a health check.

### Update all modules at once

```bash
bash scripts/update_modules.sh --all
```

### Sync without restart (e.g. static files only)

```bash
bash scripts/update_modules.sh security_theme --no-restart
```

### Force schema migration (new fields / models)

SSH into the server and run the module update inside the container:

```bash
ssh root@47.84.205.81
docker exec dogforce-demo-odoo-1 odoo -d dogforce-demo -u security_mobile --stop-after-init
docker restart dogforce-demo-odoo-1
```

### Check container logs

```bash
ssh root@47.84.205.81 'docker logs dogforce-demo-odoo-1 --tail 100 -f'
```

Or use the helper script:

```bash
bash scripts/logs.sh
```

### Health check

```bash
curl -s -o /dev/null -w "%{http_code}" http://47.84.205.81:8069/web/health
# expect: 200
```

---

## Mobile app (DeployGuard)

All mobile code lives in `mobile/`.

### Environment variables (`mobile/.env`)

```
EXPO_PUBLIC_ODOO_BASE_URL=http://47.84.205.81:8069
EXPO_PUBLIC_ODOO_DB=dogforce-demo
```

These are baked in at build time by Expo. EAS reads the `.env` file automatically during builds.

### EAS project details

| | |
|---|---|
| **EAS account** | `wzulu` |
| **Project slug** | `deployguard-mobile` |
| **EAS project ID** | `49cdb70c-319f-4b20-8d8e-aab4cc3a02a0` |
| **Android package** | `com.deployguard.security.mobile` |

### Run in Expo Go (dev, no build needed)

```bash
cd mobile
npx expo start
```

Scan the QR code with Expo Go. This uses the local dev server.

### Build a new APK for the demo (EAS preview)

```bash
cd mobile
eas build --platform android --profile preview --non-interactive
```

- Builds a release APK via EAS cloud (~10–15 min)
- Outputs a QR code + download link on `expo.dev`
- Install directly on any Android device — no Play Store needed

### Build profiles (`eas.json`)

| Profile | Use |
|---|---|
| `preview` | Demo APK — release-signed, internal distribution |
| `production` | Same as preview (internal dist, not Play Store) |
| `development` | Dev client — requires `expo-dev-client`, not normally used |

### After making mobile code changes

1. `cd mobile && eas build --platform android --profile preview --non-interactive`
2. Wait for build link, download APK, install on device
3. No need to touch the Odoo server unless you also changed backend endpoints

### Bypass login (demo mode)

The login screen has **Demo access** chips (Owner / Manager / Supervisor) that skip the Odoo API entirely and inject a mock session. Use these when backend auth is unavailable. Real login uses Odoo's `/web/session/authenticate`.

---

## Session / auth architecture

- Login POSTs to `/web/session/authenticate` (Odoo JSON-RPC)
- `session_id` from the JSON response is stored in SecureStore and injected on every request as `Cookie: session_id=...` and `X-Openerp-Session-Id: ...`
- This bypasses the native Android cookie jar (which is unreliable in release builds)
- On app restart, `loadSessionId()` in `client.ts` restores the session from SecureStore

---

## Network / Android release gotcha

Expo Go (debug) allows all HTTP traffic. Release APKs on Android 9+ block plain HTTP by default. We handle this via:

1. `"usesCleartextTraffic": true` in `app.json` → `android`
2. `plugins/withNetworkSecurityConfig.js` — custom config plugin that writes `network_security_config.xml` with `cleartextTrafficPermitted="true"`. This takes precedence over any plugin that might override the manifest attribute.

---

## Key file locations

| Path | What it is |
|---|---|
| `custom_addons/security_mobile/` | All mobile API endpoints (Python) |
| `custom_addons/security_mobile/controllers/owner.py` | Owner dashboard endpoints |
| `custom_addons/security_mobile/controllers/notifications.py` | Push notification helpers |
| `mobile/src/api/client.ts` | Axios client, session injection, offline handling |
| `mobile/src/api/auth.ts` | Login / logout, session_id capture |
| `mobile/src/stores/authStore.ts` | Zustand auth state, bootstrap |
| `mobile/app/(owner)/` | Owner tab screens |
| `mobile/app/(manager)/` | Manager tab screens |
| `mobile/app/(supervisor)/` | Supervisor tab screens |
| `mobile/plugins/withNetworkSecurityConfig.js` | Android cleartext traffic config plugin |
| `scripts/update_modules.sh` | Deploy Odoo modules to demo server |

---

## Common tasks

### Add a new Odoo module

```bash
bash scripts/scaffold-module.sh security_mymodule
# edit manifest, models, controllers
bash scripts/update_modules.sh security_mymodule
```

### Open an Odoo shell on the demo server

```bash
bash scripts/odoo-shell.sh
```

### Backup the demo database

```bash
bash scripts/backup-db.sh
```
