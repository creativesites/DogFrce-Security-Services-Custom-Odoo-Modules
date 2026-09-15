# 17 — Desktop Architecture

> Status: Draft · Owner: Platform engineering · Decisions: [DG-ADR-001](adr/DG-ADR-001-desktop-framework.md) (Tauri v2), [DG-ADR-007](adr/DG-ADR-007-authentication.md), [DG-ADR-011](adr/DG-ADR-011-offline-architecture.md), [DG-ADR-017](adr/DG-ADR-017-design-system-and-shell-parity.md)

---

## 1. Responsibility split

| Layer | Owns | Does **not** own |
|---|---|---|
| **Rust core** (`apps/desktop/src-tauri`) | Secure storage (keychain), device keypair, encrypted SQLite, offline outbox, token refresh, OS notifications, tray/autostart, updater, deep links, Odoo window management, crash reporting, file capture and encryption | Business rules, UI, any domain decision |
| **WebView app** (`packages/app` + `packages/ui`) | All screens and interactions, API calls with access tokens, rendering, local UI state | Long-term secrets, refresh tokens, direct DB access |
| **Platform backend** | Every business rule, authorisation and derived value | — |

This keeps ADR-0009's "thin client" principle: the desktop never decides whether work is overdue, who must verify, or what a score is.

## 2. Windows and processes

| Window | Origin | Capabilities |
|---|---|---|
| `main` | Platform app assets (`tauri://localhost`) | Full IPC allowlist, strict CSP |
| `odoo` (single, reused) | Tenant Odoo HTTPS origin | **No IPC**, no injected scripts; navigation restricted to the tenant's Odoo host |
| `updater` dialogs | Native | — |

Rules:

- The Odoo window is created lazily on first "Open in Odoo" and reused for subsequent targets.
- Navigation outside the tenant Odoo host is blocked and opened in the system browser instead.
- Closing the Odoo window does not affect the Platform session; its Odoo session lives until Odoo expires it, after which a fresh ticket is brokered silently.

## 3. IPC command surface (allowlist)

| Command | Purpose | Notes |
|---|---|---|
| `auth.signIn(companyCode, login, password, totp?)` | Calls the tenant bridge, then Platform exchange | Password never crosses into JS storage; handled in Rust |
| `auth.currentSession()` / `auth.accessToken()` | Returns claims / a short-lived access token | Refresh handled transparently in Rust |
| `auth.signOut(wipe?)` | Revokes session, clears keychain and optionally local data | Warns when unsynced work exists |
| `device.info()` | Device ID, app version, OS build | |
| `db.query(namespace, params)` | Typed reads from the local cache | No raw SQL from JS |
| `outbox.enqueue(command)` / `outbox.status()` | Offline command queue | Returns pending/failed counts |
| `sync.run(reason)` | Triggers sync | Also runs on connectivity regain and a timer |
| `files.capture(kind)` / `files.attach(path)` | Image/file capture, compression, encryption | Returns `attachment_id` |
| `notify.show(payload)` | OS notification | Rate-limited in Rust as a backstop |
| `odoo.open(target)` | Requests a ticket and opens/navigates the Odoo window | Target validated server-side |
| `app.setAutostart(bool)` / `app.setTrayMode(bool)` | Background behaviour | |
| `updater.check()` / `updater.install()` | Update flow | Signature verified before install |
| `telemetry.event(batch)` | Queues client events | Stamped server-side ([13](13-event-architecture.md)) |
| `support.diagnostics()` | Redacted diagnostics bundle for support | User sees contents before sending |

Everything else is denied by capability configuration.

## 4. Storage

| Data | Location | Protection |
|---|---|---|
| Refresh token, device private key, DB key | OS keychain (Windows Credential Manager) | Per-user OS protection |
| Cached work, training, projections | SQLite (SQLCipher) in app data dir | Encrypted with keychain-held key |
| Evidence files pending upload | App data dir | Encrypted; deleted after confirmed upload |
| UI preferences (nav state) | SQLite settings table | Namespaced `dgp.nav.v1`, mirrors shell behaviour |
| Logs | Rolling file, 7 days | Redacted; included in diagnostics only with consent |

No sensitive data is written to `localStorage` in the WebView.

## 5. Authentication flow (desktop specifics)

1. First run: company code → discovery → tenant branding cached.
2. Sign-in form (Platform UI) → `auth.signIn` → Rust posts credentials to the tenant bridge over TLS → assertion → Platform exchange with device proof → tokens stored.
3. The WebView receives claims and an access token; refresh happens in Rust before expiry, and on 401 with a single retry.
4. Offline: the app opens with cached data while the last refresh is ≤ 72 h old, showing an offline banner; writes queue.
5. Sign-out or admin revocation wipes local data on next contact.

## 6. Opening Odoo

```
User clicks "Open in Odoo" → odoo.open(target)
 → Platform validates session, link, policy (not an Odoo admin account)
 → bridge mints single-use 60 s ticket
 → Rust navigates the `odoo` window to /deployguard/sso/consume?ticket=…&redirect=…
 → Odoo sets its own session cookie and redirects to the record
```

Failure handling: if ticket minting fails (Odoo down, policy refusal), the UI explains why and offers "Copy link" so the user can sign in manually.

## 7. Background behaviour

- Optional autostart (tenant default on for supervisors/managers), minimised to tray.
- While running, an SSE connection receives notifications and inbox updates; on disconnect it falls back to polling with backoff.
- Idle lock: the app locks after 15 minutes of inactivity (configurable), requiring re-verification with the user's Odoo credentials (TOTP where enrolled) through the normal sign-in flow; because devices are personal (R-9), this is a convenience lock, not a kiosk control.

## 8. Updates and release channels

- Channels `pilot` and `stable`; a tenant admin can pin a channel per device group.
- Update checks on start and every 6 hours; download in the background; install on next restart, or immediately on user request.
- Mandatory minimum version: the API rejects clients below `min_supported_version` with a clear upgrade screen (protects against incompatible contracts).

## 9. Performance budgets (NFR-01, NFR-02)

| Metric | Budget |
|---|---|
| Installer size | ≤ 20 MB (excluding WebView2 bootstrapper) |
| Cold start to interactive Home (cached) | ≤ 3 s on a 4 GB Windows machine |
| Warm Home render | ≤ 1.5 s |
| Idle RSS | ≤ 200 MB (app window; the Odoo window is additional while open) |
| Sync of a typical offline backlog (20 commands, 10 photos) | ≤ 60 s on 1 Mbps |

## 10. Platform support and packaging

- Windows 10 22H2+ and Windows 11, x64 (ARM64 build later if needed).
- WebView2: Evergreen runtime; the installer bootstraps it when missing.
- Per-user installation by default (no administrator rights), machine-wide optional for managed fleets.
- macOS and Linux builds exist for development only; distribution is FUT.

## 11. Testing

- Rust unit tests for storage, outbox, token refresh, ticket handling.
- Playwright (WebDriver for Tauri) end-to-end tests for sign-in, checklist completion offline → sync, Odoo open, update prompt.
- Manual test matrix per release on a low-spec Windows VM.
