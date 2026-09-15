# DG-ADR-001 — Desktop Framework

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [17-desktop-architecture](../17-desktop-architecture.md), [DG-ADR-016](DG-ADR-016-web-framework.md), [DG-ADR-017](DG-ADR-017-design-system-and-shell-parity.md)

## Context

DeployGuard Platform needs an installed Windows desktop client for office staff and supervisors (MVP), built by a developer working on macOS, with a path to macOS/Linux later.

The client must:

- store credentials securely;
- hold a device identity;
- show OS notifications;
- work offline for a limited set of features;
- update itself safely;
- open DeployGuard ERP (Odoo) screens;
- look like the `security_shell` design system;
- reuse as much React/TypeScript as possible with the web app and, conceptually, the Expo mobile app.

Constraints: small team (A-7), mixed-quality Windows machines (A-2), adoption-sensitive users (installer size, startup time and SmartScreen warnings all matter).

## Decision

Use **Tauri v2** (Rust core, system WebView — WebView2 on Windows) with a **React + TypeScript** UI shared with the web app (`packages/app`, `packages/ui`).

Keep the Rust layer **thin**. It owns only:

- secure storage (OS keychain);
- device keypair and identity;
- the local SQLite cache and offline outbox;
- OS notifications;
- the updater;
- deep-link handling;
- the Odoo window.

All business logic stays in the backend ([DG-ADR-002](DG-ADR-002-backend-architecture.md)).

## Alternatives evaluated

Scores 1 (poor) – 5 (excellent) for *this* project's constraints.

| Criterion | Tauri v2 | Electron | .NET WPF | .NET MAUI | Flutter Desktop | Web / PWA |
|---|---|---|---|---|---|---|
| Windows deployment (MSI/NSIS, per-user install, WebView2 bootstrap) | 4 | 5 | 5 | 3 | 4 | 5 (no install) |
| macOS development experience | 5 | 5 | 1 (no WPF on macOS) | 3 | 4 | 5 |
| Installer / app size | 5 (≈5–15 MB) | 2 (≈80–150 MB) | 4 | 3 | 3 | 5 |
| Memory / performance | 4 | 2 | 4 | 3 | 4 | 3 |
| Security model | 5 (capability ACLs, no Node in renderer, Rust core) | 3 (secure only if hardened: context isolation, sandbox) | 4 | 4 | 4 | 3 (browser sandbox; weak local secret storage) |
| Auto-update | 4 (official updater plugin, signed artefacts) | 5 (mature ecosystem) | 3 (ClickOnce/MSIX) | 3 | 3 | 5 |
| Offline capability | 5 (SQLite, file system) | 5 | 5 | 5 | 5 | 3 (service worker, storage eviction risk) |
| OS integration (keychain, notifications, deep links, tray) | 4 | 5 | 5 | 4 | 3 | 2 |
| Long-term maintainability for a TS team | 4 | 4 | 2 | 2 | 2 | 5 |
| Developer productivity | 4 | 5 | 3 | 2 | 3 | 5 |
| React/TS reuse with web | 5 | 5 | 1 | 1 (Blazor Hybrid is C#) | 1 | 5 |
| Packaging the Odoo experience (separate native window, own session) | 4 | 4 | 3 (WebView2 control) | 3 | 2 | 2 (tab only) |
| macOS/Linux later | 4 (Linux WebKitGTK variance) | 5 | 1 | 3 (no Linux) | 4 | 5 |
| Professional production-grade client | 4 | 5 | 4 | 3 | 4 | 3 |
| **Total** | **61** | **60** | **45** | **42** | **46** | **56** |

**Why Tauri is chosen over Electron despite similar scores:**

- The weighted concerns for DogForce-class users are **installer size, memory on older PCs, and a smaller attack surface** for a client that stores tokens and device keys. Electron's advantages (identical Chromium everywhere, most mature updater) matter less on Windows-only MVP, where WebView2 *is* Chromium.
- Electron remains the **fallback** if Tauri blocks us (see Consequences). Because UI code lives in `packages/app` with no Tauri imports outside a small adapter (`packages/app/src/platform/`), switching costs are bounded.

**Why not PWA only:**

- No reliable secure token or key storage.
- Storage eviction threatens offline data.
- Weaker notification and deep-link behaviour.
- No device identity.
- A "browser tab" does not create the "company app" habit we need for adoption.

The same SPA is still deployed to the web for owners and admins ([DG-ADR-016](DG-ADR-016-web-framework.md)).

**Why not .NET or Flutter:** they give up React/TS reuse and the macOS-based development flow, and add a second UI technology to maintain.

## Tradeoffs

| We gain | We accept |
|---|---|
| Small, fast, low-memory client; strong capability-based security | WebView rendering differences on future macOS (WKWebView) and Linux (WebKitGTK); WebView2 must exist on Windows (the installer can bootstrap it) |
| One UI codebase for desktop and web | Some Rust knowledge required for the native layer |
| Signed updater, OS keychain, SQLite locally | A younger plugin ecosystem than Electron; we pin plugin versions and keep the native surface small |

## Consequences

- `apps/desktop` contains the Tauri shell only: `src-tauri/` (Rust) plus a thin Vite entry that renders `packages/app`.
- Tauri capability files define an allowlist of IPC commands. The WebView has no general file-system or shell access ([16](../16-security-architecture.md) §7).
- Windows builds are produced in CI on Windows runners; code signing is required before pilot (OQ-7). macOS local builds are for development only.
- **Exit criteria to revisit this ADR (switch to Electron):** a blocking WebView2 defect on target machines; an updater or signing limitation we cannot work around; or more than 20 % of native-layer effort going into plugin workarounds by the end of P2.
