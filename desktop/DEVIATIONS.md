# Deviations from the planned architecture (P2A pilot slice)

> Per the desktop build mission's §26: every deviation from `docs/deployguard/`
> is documented here, with rationale and the migration path back to the
> planned architecture. Nothing here is a silent redesign — each item below
> is a **known, temporary, bridged gap** that P1 (Odoo bridge) and later
> phases close.

---

## D-1. Login happens on Odoo's own page — no DeployGuard Platform backend yet

**Planned architecture:** `docs/deployguard/19-backend-architecture.md`,
[DG-ADR-007](../docs/deployguard/adr/DG-ADR-007-authentication.md) — the
desktop calls the DeployGuard Platform's `/v1/auth/exchange`, which
verifies a signed assertion from the Odoo bridge addon and issues its own
device-bound tokens.

**What's built instead (revised 2026-09-16, superseding the original D-1):**
there is no DeployGuard-branded login form at all. The "odoo" webview
(`src-tauri/src/windowing.rs`) loads Odoo's **own** `/odoo` entry point
directly — an unauthenticated visitor sees Odoo's real `/web/login` page
and types their DogForce credentials into it, exactly as they would in a
browser. Odoo's own persistent cookie store (kept by WebView2/WKWebView
across app restarts, like any browser profile) is what makes "stay signed
in" work — there is no separate session of ours to expire or restore.

After each page load, Rust checks whether the URL still looks
unauthenticated (`odoo::is_unauthenticated_path`); if not, it reads the
`session_id` cookie back out of that same webview
(`Webview::cookies()` — this is a **read**, never a write, and only of
the "odoo" webview's own cookie jar) and asks Odoo who it belongs to
(`/web/session/get_session_info`). That becomes the in-memory
`AppState.session` the "shell" overlay reads via `get_current_session`
and the `deployguard://session-changed` event.

**Why:** BUILD-ORDER P1 (the bridge addon + Platform backend) doesn't
exist yet. The user explicitly asked for single sign-on to be "controlled
by the Odoo instance" rather than a DeployGuard-branded form in front of
it — which happens to be an even simpler MVP path than the original D-1,
since there's no password ever touching this app's own code.

**Migration path:** once the bridge exists, the "odoo" webview still loads
Odoo directly (unchanged) — what changes is that a **successful** login
additionally triggers the bridge to mint a Platform session (assertion →
`/v1/auth/exchange`) so the Platform's own features (training, work,
adoption — everything the overlay panel currently shows as "Coming soon")
have an authenticated Platform identity to call, not just cached Odoo
identity fields. `state::SessionInfo` gains Platform-issued fields;
`get_current_session`'s shape is additive, not a rewrite.

**Tracking:** revisit when BUILD-ORDER P1 ships.

---

## D-2. Odoo renders in the SAME window as a corner overlay, not a second window

**Planned architecture:** `docs/deployguard/17-desktop-architecture.md` §2
described two separate native windows (the DeployGuard app window, and a
dedicated Odoo window opened on demand).

**What's built instead (revised 2026-09-16, per explicit user direction):**
one window, two sibling Tauri webviews (Tauri v2's `unstable` multi-webview
API, `Window::add_child`):

- **`odoo`** fills the entire window and is the primary, default-visible
  surface — this is where the user spends most of their time, in Odoo
  itself. It has **zero** Tauri IPC capabilities (see
  `src-tauri/capabilities/main.json`, scoped by `"webviews": ["shell"]`,
  not by window — both webviews share the "main" window label, so
  window-level scoping alone would have been wrong).
- **`shell`** is the DeployGuard overlay: collapsed to a small corner
  handle (`src/shell/Overlay.tsx`) by default, so Odoo is fully visible
  and usable everywhere else. Hovering, focusing (Tab), or clicking the
  handle resizes it (via `Webview::set_size`, called from the
  `overlay_expand`/`overlay_collapse` commands) into a 340px sidebar
  panel — DeployGuard's actual UI — layered on top of Odoo's left edge.
  It collapses again on Escape, a debounced mouseleave, or navigating
  into Odoo.

Both webviews are genuinely isolated: no preload script, no injected
bridge, no shared JS context. The overlay reads Odoo's session cookie
(D-1) but never writes to or scripts the Odoo webview.

**Why:** explicit user direction — Odoo should be the primary experience,
not something behind a second window the user has to alt-tab to; the
DeployGuard chrome should be a lightweight, dismissable overlay instead.

**Known limitation:** the corner-hover interaction is a first pass, not
final UX. It hasn't been through the accessibility/UX review
`docs/deployguard/05-ux-principles.md` calls for — Tab-to-focus and
Escape-to-collapse are implemented as a baseline, but this needs real
usability testing with pilot users before it's considered settled.

**Migration path:** unaffected by the Platform backend arriving (D-1) —
this is a UI-shell decision, independent of how auth is brokered. If it
doesn't hold up in pilot testing, the fallback is the originally planned
two-window design; `windowing.rs` isolates the change to one module.

**Tracking:** revisit when BUILD-ORDER P1 ships and the bridge's
`sso/ticket` + `sso/consume` endpoints exist.

---

## D-3. No device registration, no session revocation via the Platform

**Planned architecture:** `docs/deployguard/17-desktop-architecture.md` §5,
PR-IAM-05/10 — desktop installs register a device keypair with the
Platform; the Platform can revoke a device or session, which the app
respects within 5 minutes.

**What's built instead:** nothing. The app has no device identity beyond
whatever the OS keychain entry represents. Signing out on one machine
doesn't affect a session on another.

**Why:** device registration is a Platform-backend feature (P1). Building
it against nothing to call would be scaffolding without substance.

**Migration path:** add a device keypair generated on first run (`ed25519`
via a small addition to `keychain.rs`), registered at
`POST /v1/auth/exchange` per DG-ADR-007. The `AuthSession` shape already
has room for this — `commands.rs` and the frontend types don't need
restructuring, only extending.

**Tracking:** BUILD-ORDER P1–P2.

---

## D-4. No offline support

**Planned architecture:** `docs/deployguard/20-offline-strategy.md`,
[DG-ADR-011](../docs/deployguard/adr/DG-ADR-011-offline-architecture.md).

**What's built instead:** nothing. There is no local SQLite cache, no
command outbox. The app requires connectivity to sign in and to reach
Odoo; it reports "can't reach DeployGuard ERP" honestly when offline
(`connectivity.rs`) rather than pretending to work.

**Why:** offline work management (checklists, evidence capture) doesn't
exist yet in this pilot slice — there's no "work" module to make offline
in the first place (that's BUILD-ORDER P4). Building the offline
infrastructure before there's anything to make offline would be
speculative.

**Migration path:** unchanged from the plan — SQLCipher-encrypted local
store, command outbox, conflict handling per DG-ADR-011 §4–5, built
alongside P4 (work management).

**Tracking:** BUILD-ORDER P4.

---

## D-5. Auto-update is scaffolded but disabled

**What's built:** the `tauri-plugin-updater` is wired into `lib.rs`, and
`tauri.conf.json` has an `updater` block, but `"active": false` and an
empty `pubkey`. No update server exists yet.

**Why:** shipping unsigned or unverifiable auto-updates would be worse
than no auto-updates. Per mission §10, the *architecture* should exist so
this is a config flip, not a rewrite, once signing infrastructure
(§26-deployment-strategy.md, OQ-7) is in place.

**Migration path:** generate a real updater keypair, set `pubkey`, stand
up the update-manifest endpoint (or a static one on the same CDN as the
installer per [DG-ADR-013](../docs/deployguard/adr/DG-ADR-013-deployment.md)),
flip `"active": true`.

---

## D-6. No notifications, no work/training/adoption features

**What's built:** the Home screen shows honest "Coming soon" empty states
for My Work and Training (mission §6, §17 — explicitly: no fake data).
There is no notification wiring beyond the `tauri-plugin-notification`
dependency being present for later use.

**Why:** these are BUILD-ORDER P3–P9 features with no backend to source
real data from yet. Mocking them would violate mission §17 directly.

**Migration path:** as each Platform module ships (training in P3, work in
P4, notifications alongside P2's later increments, adoption in P5), the
corresponding Home tile in `src/home/HomeScreen.tsx` gets a real data
source instead of its empty-state copy. The tile layout and shell
structure don't need to change.

---

## What was *not* deviated from

To be explicit about what stayed true to the plan, unchanged:

- **Tauri v2 + Rust (thin) + React/TypeScript** — as decided.
- **`security_shell` design-token parity** — `src/styles/ds.css` and
  `dgs.css` are verbatim copies of the Odoo repo's token files (see their
  file headers for the source commit), per
  [DG-ADR-017](../docs/deployguard/adr/DG-ADR-017-design-system-and-shell-parity.md).
- **Single login, Odoo credentials** — preserved exactly as a product
  decision (R-7); only *how* the backend brokers it is deferred (D-1/D-2).
- **No credentials in git, logs, or source** — see `.env.example` (no
  secrets, only the same non-secret base URL already public in
  `mobile/.env` and `CLAUDE.md`), and `errors.rs`/`diagnostics.rs` (never
  serialize a password, token or cookie).
- **Odoo window isolation** — zero IPC, no injected bridge, exactly as
  specified, even though the *mechanism* for signing it in differs (D-2).
- **Modular monolith direction, no throwaway infra** — no Kubernetes, no
  microservices, no new servers stood up; this pilot slice adds zero
  infrastructure beyond the existing production Odoo.
