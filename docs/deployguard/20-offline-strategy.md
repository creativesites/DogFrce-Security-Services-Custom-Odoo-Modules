# 20 — Offline Strategy

> Status: Draft · Owner: Platform engineering · Decision: [DG-ADR-011](adr/DG-ADR-011-offline-architecture.md)

---

## 1. Principle

Offline capability exists to keep **field work** flowing, not to duplicate the product. Anything that requires fresh organisational context (verification, assignment, analytics, AI, admin) stays online. The client never lies about success (the mobile "fake 200" pattern, S-5, is prohibited).

## 2. Scope

| Capability | Offline (MVP) | Offline (V1) | Always online |
|---|---|---|---|
| View Home, my tasks, checklist instances (today + 7 days) | ✓ | ✓ | |
| Run a checklist, answer items, capture evidence | ✓ | ✓ | |
| Mark "couldn't complete" with reason | ✓ | ✓ | |
| Comment on a task | ✓ | ✓ | |
| Post-task feedback, draft a problem report | ✓ | ✓ | |
| Read downloaded lessons and recently opened articles | ✓ | ✓ | |
| Complete lessons, take assessments | | ✓ | |
| Verify others' work, resolve exceptions, assign | | | ✓ |
| Adoption, analytics, inbox triage, admin, AI | | | ✓ |
| Open Odoo | | | ✓ |

## 3. What is cached, and for how long

| Data | Refresh | Retention offline |
|---|---|---|
| My work (today + 7 days) and their templates | Each sync, plus on change via SSE | 7 days rolling |
| Site and shift projections in my scope | Hourly | 7 days |
| My training assignments; explicitly downloaded lessons | On assignment; user-initiated download | Until course version retires or user removes |
| Knowledge articles opened in the last 30 days | On open | 30 days |
| My profile, roles, scopes | On sign-in and refresh | Session lifetime |

Cached screens display "Showing data from HH:MM" whenever the device is offline or the cache is older than 15 minutes.

## 4. Writes: the command outbox

Each offline write is a **domain command**, not an HTTP replay:

```json
{
  "command_id": "0192f0f1-aaaa-7bbb-8ccc-dddd00000003",
  "type": "work.checklist.submit",
  "aggregate": { "type": "checklist_instance", "id": "0192f0e0-…" },
  "base_version": 4,
  "created_at": "2026-09-16T07:10:22Z",
  "payload": { "responses": [ … ], "attachments": [ "att_0192…" ] }
}
```

- Ordered per aggregate; independent aggregates sync in parallel.
- `command_id` is the idempotency key; retries are safe.
- Attachments upload first (resumable, signed URLs); the command references `attachment_id`s.
- Status per item in the UI: `Pending sync` → `Synced`, or `Needs attention` with the reason.

## 5. Conflict handling

| Case | Server behaviour | Client experience |
|---|---|---|
| Aggregate unchanged or compatible | Apply; per-item last-write-wins by timestamp; evidence additive | Item shows `Synced` |
| Instance already submitted/verified by someone else | Reject `conflict.already_completed`; keep draft | "This checklist was completed by X at 10:04. Keep your notes?" → discard or send as comment |
| Instance reassigned | Reject `conflict.reassigned` | Offer to send the draft to the new owner |
| Template version changed | Apply matching items; report removed/added | "3 questions changed. Review before resubmitting." |
| Validation failure (missing required evidence) | Reject `validation_failed` with item references | Item marked `Needs attention`, deep-linked to the failing question |
| Command older than retention (> 30 days queued) | Reject `expired` | Draft preserved read-only, user prompted to redo or discard |

Nothing is ever discarded silently, and a backlog that cannot sync produces a persistent banner plus a support prompt after 48 hours.

## 6. Session and security while offline

- Cached data is usable while the last successful token refresh is ≤ 72 hours old; afterwards the app locks to a sign-in screen (drafts are retained).
- Commands only transmit with a valid online session.
- The local database and evidence files are encrypted ([16](16-security-architecture.md) §7); device revocation wipes them on next contact.

## 7. Event capture offline

Client telemetry events queue locally with their original `occurred_at` and sync in batches. The server stamps `recorded_at` and flags `clock_suspect` when the offset exceeds 24 hours ([13](13-event-architecture.md) §5), so adoption scoring is not distorted by a wrong device clock.

## 8. Testing

- Fault injection: offline during submit, during upload, mid-batch; airplane-mode soak test with 50 queued commands.
- Conflict scenarios scripted end-to-end (each row in §5).
- Clock-skew tests (device ±2 days).
- Storage-pressure test: cache eviction never deletes unsynced commands or their attachments.
