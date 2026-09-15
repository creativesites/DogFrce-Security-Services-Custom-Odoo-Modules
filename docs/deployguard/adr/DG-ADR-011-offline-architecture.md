# DG-ADR-011 — Offline Architecture

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [20-offline-strategy](../20-offline-strategy.md), [17-desktop-architecture](../17-desktop-architecture.md), [DG-ADR-001](DG-ADR-001-desktop-framework.md), [DG-ADR-007](DG-ADR-007-authentication.md)

## Context

Supervisors work partly from vehicles and sites with intermittent connectivity (A-3). The existing DeployGuard Mobile offline queue shows the anti-pattern to avoid: it returns a **fabricated HTTP 200** for queued writes, has no conflict handling, and drops items after 5 retries (S-5).

The brief warns against making everything offline "because we can". Management, AI and admin features have little value without fresh data.

## Decision

1. **Desktop only.** The web app is online-only and keeps no sensitive data at rest in the browser.
2. **Minimum offline set (MVP):**
   - **Read:** Home, my assigned tasks and checklist instances (today plus the next 7 days), templates for those instances, my sites' basic projection, my training assignments and **explicitly downloaded** lessons (text, documents, small videos up to a configurable cap), knowledge articles I have opened recently.
   - **Write:** complete checklist items, capture evidence (photos, files, signatures), mark "couldn't complete", add task comments, submit post-task feedback, draft a problem report, queue client telemetry events.
   - **V1:** lesson completion and quiz attempts offline.
   - **Never offline:** verification and approvals, exception resolution, assignments, admin, adoption and analytics views, AI, and opening Odoo.
3. **Local store.**
   - SQLite in the app data directory, encrypted with SQLCipher. The database key is generated on first run and stored in the OS keychain (Windows Credential Manager).
   - Access is exclusively through typed Tauri commands; the WebView never opens the database directly.
4. **Outbox of commands, not HTTP replays.**
   - Each offline write is stored as a domain command, e.g. `SubmitChecklistItemAnswer`, with a client UUIDv7 `command_id` (idempotency key), `base_version` (server version the user saw), payload and created time.
   - Commands sync in order per aggregate once online, through dedicated sync endpoints.
5. **Honest UI.** Items show `Pending sync`, `Synced` or `Needs attention`. **No success state is shown for work the server has not accepted.**
6. **Conflict policy** (server-authoritative):

   | Situation | Resolution |
   |---|---|
   | Instance still open, same assignee | Apply; answers merge per item (last write per item wins with timestamp; evidence is additive). |
   | Instance reassigned, cancelled or already submitted by someone else | Reject command with `conflict` reason; the local draft is preserved and shown in "Needs attention", with options to discard or send as a comment to the new owner. |
   | Template version changed | Accept answers for items that still exist; flag removed items. |
   | Command validation failure (e.g. required evidence missing) | Surface to the user; never silently drop. |

7. **Offline session limits.**
   - Offline use continues with cached data while the last successful token refresh is **≤ 72 hours** old. After that, cached screens lock until the user is online and re-authenticated.
   - Queued commands are only transmitted with a valid online session.
   - A revoked device wipes its local store on the next contact.
8. **Evidence files.**
   - Compressed client-side (images max 1600 px long edge, quality ~0.8).
   - Encrypted at rest locally.
   - Uploaded via pre-signed object-storage URLs with retry, then linked by `attachment_id` in the command.

## Alternatives

| Option | Why not |
|---|---|
| Service-worker PWA offline | Storage eviction; weak secret storage; no device key. |
| Full local-first sync engine (CRDTs, replicated DB such as ElectricSQL/PowerSync) | Powerful but heavy for a narrow offline set; server-authoritative domain rules conflict with free-form merging; extra infrastructure. |
| Replay raw HTTP requests (like the mobile queue) | Loses intent, can't resolve conflicts meaningfully, encourages fake success. |
| No offline at all | Supervisors at sites would fall back to paper, directly harming adoption. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Useful field capability with understandable conflict rules | Sync endpoints and command handlers to build and test per offline-capable aggregate |
| Encrypted local data bound to the device | Lost keychain entry means lost unsynced drafts (warned in UI when a backlog exists) |

## Consequences

- Offline-capable aggregates (MVP: checklist instance, task comment, feedback, problem-report draft, client events) implement `sync` command handlers with idempotency and conflict responses ([24](../24-api-design.md) §7).
- Test suite includes network-fault injection and conflict scenarios in Playwright plus Rust tests ([25](../25-testing-strategy.md)).
