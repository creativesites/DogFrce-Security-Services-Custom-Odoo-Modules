# 18 — Web Architecture

> Status: Draft · Owner: Platform engineering · Decision: [DG-ADR-016](adr/DG-ADR-016-web-framework.md)

---

## 1. Purpose

The web app is the **same application** as the desktop client, built from `packages/app`, deployed as static assets. It exists because:

- owners and managers want access from any machine or a tablet without installing anything;
- tenant admins and platform staff perform configuration work that suits a browser;
- content authoring (courses, templates, articles) benefits from a large screen and no install friction;
- it is the fallback when a desktop install is blocked.

## 2. What is web-only, desktop-only and shared

| Capability | Web | Desktop |
|---|---|---|
| Home, Work, Learn, Team, Inbox, Insights, Help | ✓ | ✓ |
| Admin (tenant configuration, integrations, rules) | ✓ (primary) | ✓ |
| Content authoring | ✓ (primary) | ✓ |
| Platform staff console | ✓ (only) | ✗ |
| Offline work, local cache | ✗ | ✓ |
| OS notifications, tray, autostart | ✗ (browser notifications only, opt-in) | ✓ |
| Device-bound sessions | Cookie-based, no device key | ✓ |
| Open in Odoo | New browser tab via SSO ticket | Dedicated window |
| Evidence capture from camera | Browser file/camera input | Native capture with compression |

## 3. Composition

```
apps/web (Vite entry)
 └── packages/app  (routes, screens, state, platform adapter → web implementation)
      └── packages/ui (tokens, shell, components)
      └── packages/api-client (generated from OpenAPI)
```

The web platform adapter implements the same interface as the Tauri adapter: `secureStorage` (memory + cookie-backed session), `notifications` (Web Notifications API, opt-in), `openOdoo` (new tab), `fileCapture` (input elements), `offline` (disabled, always-online guards).

## 4. Session handling

- Sign-in follows [DG-ADR-007](adr/DG-ADR-007-authentication.md): the browser posts credentials **directly to the tenant bridge** (CORS-allowlisted), receives the assertion, exchanges it with the Platform.
- The refresh token is stored as an `HttpOnly; Secure; SameSite=Strict` cookie on the Platform API origin; the access token lives in memory only.
- CSRF protection (double-submit token) on cookie-authenticated endpoints.
- No tenant data is persisted in the browser; a page reload re-fetches.

## 5. Delivery

- Static assets on CDN, immutable content hashes, `index.html` never cached.
- Route-level code splitting; the shell plus Home stays within the performance budget (NFR: ≤ 250 KB gzip initial JS).
- A build-time `min_supported_version` is enforced by the API; the SPA refreshes itself when it detects a newer deployment (version endpoint + SSE hint).
- Browser support: current Chrome, Edge, Firefox and Safari; no IE/legacy shims.

## 6. Accessibility and responsiveness

- Same WCAG 2.2 AA requirements as the desktop ([05](05-ux-principles.md) §9).
- Breakpoints mirror `security_shell`: below 1280 px the nav panel becomes an overlay; below 900 px the rail becomes a bottom bar. Management tables gain horizontal scroll containers rather than shrinking text.
- Tablet (owner use case) is a first-class layout; phones get a reduced read-only experience (digest, exceptions, approvals) rather than full parity.
