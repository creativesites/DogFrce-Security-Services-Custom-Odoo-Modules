# 21 — Notification System

> Status: Draft · Owner: Platform engineering · Decision: [DG-ADR-012](adr/DG-ADR-012-notifications.md)

---

## 1. Pipeline

```
module emits NotificationIntent
  → recipient resolution (roles, scopes, reporting lines, on-leave substitution)
  → policy engine (mandatory rules, preferences, quiet hours, dedupe, rate limit, digest)
  → channel adapters (in-app, desktop, email; V2 mobile push, WhatsApp, SMS)
  → delivery records (+ open/act tracking)
  → escalation scheduler (cancel on acknowledge/resolve)
```

Modules never call a channel directly.

## 2. Categories and defaults

| Category | Examples | Default channels | Mutable? |
|---|---|---|---|
| `work.assigned` | New task or checklist assigned to me | In-app + desktop | Yes |
| `work.due_soon` | Due within 2 hours | Desktop (digest-able) | Yes |
| `work.overdue_own` | My work is overdue | In-app + desktop + email after 2 h | Partially (email can be off) |
| `work.verification` | Something awaits my verification | In-app + desktop | Yes |
| `exception.assigned` | An exception I own | In-app + desktop | No (severity-dependent) |
| `exception.critical` | Critical in my scope | All available channels immediately | **No** |
| `training.assigned` / `training.due` | Mandatory training | In-app + email digest | Yes |
| `adoption.checkin` | "We noticed X stopped — what happened?" | In-app + desktop, gentle tone | Yes |
| `support.update` | Reply on my support request | In-app + email | Yes |
| `digest.daily` / `digest.weekly` | Summary; owner weekly brief | Email (+ in-app) | Yes |
| `system.security` | New device, session revoked, password changed | Email + in-app | **No** |

## 3. Recipient resolution

- **Direct**: a specific user (assignee, requester).
- **Role at scope**: e.g. `ops_manager@tenant`, `site_supervisor@site:123` — resolved at send time so staffing changes are respected.
- **Reporting line**: escalation steps walk `ReportingLine` upward, skipping users on approved leave (from the leave projection) or deactivated, and recording the substitution on the timeline.
- **Deduplication of people**: a user appearing through several paths receives one notification.

## 4. Anti-spam rules

| Control | Default |
|---|---|
| Dedupe window | 4 h per `dedupe_key` (rule + subject) |
| Rate limit | ≤ 6 immediate non-critical notifications per user per hour; the rest fold into the next digest |
| Quiet hours | 20:00–06:00 tenant timezone; critical only |
| Digests | Daily 07:30 (work + training), weekly Monday 07:00 (owner brief) |
| Batch collapse | "4 reports awaiting review" instead of four notifications |
| Escalation suppression | A notification is not re-sent to someone who already acknowledged the underlying item |

Effectiveness is measured (delivered → opened → acted). Categories with a low act rate are reviewed rather than sent more often.

## 5. Escalation ladders

Defined per exception rule as an `EscalationPolicy`:

| Step | Delay | Audience | Channel | Severity |
|---|---|---|---|---|
| 1 | 0 | Owner | In-app + desktop | unchanged |
| 2 | +2 h (business hours) | Owner | Email | unchanged |
| 3 | +4 h | Owner's supervisor | In-app + desktop | unchanged |
| 4 | +8 h | Operations manager | Inbox `Critical` + email | bump |

Cancelled by acknowledgement, resolution or dismissal. Every step is written to the exception timeline, so "who was told, when, and how" is auditable. Business-hours math uses the tenant working calendar.

## 6. Channels

| Channel | Implementation notes |
|---|---|
| In-app | `notification` rows; SSE push; badge counts per rail item |
| Desktop OS | Tauri notification from the running app; deep link into the route; rate-limited in Rust as a backstop |
| Email | Provider adapter (OQ-10); DKIM/SPF/DMARC on the sending domain; templates in ICU with plain-text alternatives; unsubscribe only for optional categories |
| Mobile push (V2) | Expo push service for guard/supervisor app |
| WhatsApp (V2) | Official WhatsApp Business Cloud API with approved templates — not the Baileys bridge |
| SMS (V2) | Regional provider for critical escalations where data is unreliable |

## 7. Templates and localisation

- Versioned templates per category and channel, with ICU placeholders.
- Tenants may override wording (not data scope) — for example calling an "occurrence report" by the local term.
- Every template renders in English at minimum; missing translations fall back without breaking sends.

## 8. Preferences UX

- Per category × channel: Immediate / Digest / Off (Off disabled where mandatory).
- Quiet hours with a per-user override within tenant bounds.
- A single "Pause non-critical for 2 hours" control for focused work.
- Preferences are auditable; changing another user's preferences is not possible for managers.
