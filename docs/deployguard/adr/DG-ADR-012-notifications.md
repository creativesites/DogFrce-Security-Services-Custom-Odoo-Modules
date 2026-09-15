# DG-ADR-012 — Notifications

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [21-notification-system](../21-notification-system.md), [10-exception-engine](../10-exception-engine.md), [DG-ADR-009](DG-ADR-009-event-architecture.md)

## Context

The Platform must reach people through several channels:

- in-app;
- desktop OS notifications;
- email;
- later WhatsApp and SMS.

It must escalate intelligently and avoid spam, since notification fatigue is itself an adoption killer.

DeployGuard ERP already has:

- `security.notification` (in-Odoo alerts with email);
- Expo push for mobile;
- a WhatsApp link built on **Baileys**, an unofficial WhatsApp Web client whose use carries account-ban and terms-of-service risk for customer-facing production messaging.

## Decision

1. **Single notifications module** in the Platform. Other modules never call channels directly; they emit **notification intents** (`recipient selector`, `category`, `severity`, `template`, `data`, `dedupe_key`, `action route`).
2. **Policy engine** turns intents into deliveries:
   - resolve recipients from roles, scopes and reporting lines;
   - apply the tenant's mandatory rules (critical severity cannot be muted);
   - apply user preferences per category and channel;
   - apply quiet hours (tenant timezone), except critical;
   - dedupe on `dedupe_key` within a window;
   - batch non-urgent items into **digests** (hourly, daily);
   - rate-limit per user (default max 6 immediate non-critical per hour).
3. **Channels (adapters):**

   | Channel | Mechanism | Release |
   |---|---|---|
   | In-app | `notification` rows + SSE push to connected clients | MVP |
   | Desktop OS | Tauri notification plugin, triggered by the running app (SSE or poll). The app can autostart minimised to tray (tenant default on for supervisors and managers; user can change). | MVP |
   | Email | Transactional email provider via adapter (provider per OQ-10); DKIM/SPF/DMARC on the sending domain | MVP |
   | Mobile push | Expo push service via adapter (guards/supervisors in V2) | V2 |
   | WhatsApp | **Official WhatsApp Business Platform (Cloud API)** through Meta or an approved BSP, with pre-approved templates; **not** the Baileys bridge | V2 |
   | SMS | Local-coverage SMS provider adapter (Namibia, Zambia, South Africa) | V2 |

4. **Escalation ladders** are data (`escalation_policy`): steps with delay, audience and channel, e.g.
   - T+0: assignee in-app + desktop;
   - T+2h: assignee email + supervisor in-app;
   - T+4h: manager inbox Critical.

   Steps are scheduled as pg-boss jobs and cancelled on acknowledgement or resolution. Every step is recorded on the exception timeline.
5. **Every notification deep-links** to an actionable route and records `delivered`, `opened` and `acted` where observable; these feed notification-effectiveness analytics.
6. **Templates** are versioned, localisable (ICU) and tenant-overridable for wording, never for data access.

## Alternatives

| Option | Why not |
|---|---|
| Reuse `security.notification` in Odoo as the delivery engine | Per-tenant Odoo coupling; no desktop, SSE or escalation ladder; the Platform owns recipients outside Odoo's model. |
| Third-party notification infrastructure (e.g. Novu, Knock, Courier) | Useful, but adds a vendor holding employee data and another tenancy model; our routing is domain-specific (scopes, reporting lines, escalation). Could replace channel adapters later. |
| Reuse the Baileys WhatsApp bridge for Platform notifications | Unofficial API; ban risk; no delivery guarantees; unsuitable for escalations. |
| Firebase Cloud Messaging for desktop | Unnecessary; the desktop app is online-connected via SSE when running. |

## Tradeoffs

| We gain | We accept |
|---|---|
| One place for anti-spam, preferences and escalation logic | Building the policy engine ourselves |
| Channel independence; official WhatsApp path | WhatsApp template approval and per-conversation costs (V2) |
| Deliverability control (DMARC-aligned email) | Desktop notifications only while the app runs (tray autostart mitigates; email covers escalation) |

## Consequences

- P2 delivers in-app + desktop + email channels and preferences; P6 delivers escalation ladders with exceptions.
- DeployGuard ERP's Baileys bridge remains an ERP feature for its current internal uses; migrating it to the official API is a separate ERP decision.
