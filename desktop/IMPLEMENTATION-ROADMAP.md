# DeployGuard Desktop — Implementation Roadmap

> Companion to [`RECONCILIATION.md`](./RECONCILIATION.md). Priorities are
> strictly ordered; nothing from a later bucket is pulled forward unless a
> NOW item needs it.
>
> **The test for every item:** does it make DogForce's four office users
> actually do their work through DeployGuard, and give the manager and owner
> peace of mind? If not, it waits.

Users today (see `docs/deployguard/dogforce-roles-and-pipeline.md`):
**4 office staff**: Operations Supervisor, Admin, HR and Finance. They work in
Odoo at a Windows PC in one sequential pipeline: roster → register attendance →
confirm → verify → payroll audit → payroll approval → payment. On top of them
are the **General Manager** and the **Managing Director (owner)**. Guards stay
on mobile/WhatsApp and are not desktop users.

---

## NOW — DogForce pilot

### A. Stabilize (this recovery)
- [x] Reconciliation and roadmap (this file)
- [ ] Odoo webview navigation restricted to the Odoo origin; external links open in the system browser
- [ ] `navigate_odoo` path validation; cookie read scoped to the Odoo URL
- [ ] `odoo_call_kw` identifier validation and admin-model denylist; tracebacks kept out of logs
- [ ] `AppError` always carries a human message
- [ ] Honest connectivity: `connecting` / `online` / `odoo_unreachable` / `offline` / `auth_expired`
- [ ] Session-expired state that asks the user to sign in again, instead of silently failing
- [ ] Single owner of native view state (Odoo / App / Guide dock)
- [ ] Shared UI primitives (Modal, EmptyState, ErrorState, SafeHtml, Badge, Spinner)
- [ ] Server HTML sanitised
- [ ] Missing CSS classes defined on tokens; raw hex removed; token check in lint
- [ ] Page bugs: assessment attempt on open, inbox modifier keys, number fields, UTC times, adoption role check
- [ ] Component tests (jsdom + Testing Library) for session, onboarding, capability gating, modal, SafeHtml
- [ ] CI builds without a signing key; tag-driven signed release job; `RELEASING.md`
- [ ] `security_support` rebuilt

### B. First V2 vertical slice: Roster → guided, measured work
- [ ] `security.work.responsibility`: who owns which pipeline step; tasks generated from the **roster** (register → confirm → verify, one task per rostered site-day per step, each showing "waiting for …" until its input is ready)
- [ ] Task knows *why it matters*, its required training, and its guidance flow
- [ ] Overdue tasks become Exceptions (`task_overdue`), with owner, evidence and next action
- [ ] `get_my_today()` and `get_team_today()` server APIs; the desktop renders and computes nothing
- [ ] `security_guidance`: server-side guided-task sessions, state-aware steps, an Odoo-side highlight runner, and evidence events
- [ ] AI explanation of the current step (Gemini via `security_ai_engine`), grounded in approved content, labelled as AI, never auto-acting
- [ ] Desktop: Home "Today", Guide dock (Odoo + side panel), Team Today for the manager, "Practice it now" from a lesson
- [ ] Course: *Daily Attendance Posting* + media prompt pack
- [ ] Adoption attributes `attendance.post` to the responsibility owner

### C. Before handing out installers (owner: Winston)
- [ ] Rotate previously committed credentials
- [ ] Back up the updater key; add `TAURI_SIGNING_PRIVATE_KEY` and `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` to CI secrets
- [ ] Create the `creativesites/dogforce-desktop-releases` repo and a `RELEASES_TOKEN` secret
- [ ] Staging walkthrough of the slice (RELEASING.md §Manual QA)
- [ ] Configure responsibilities for the 4 office users; confirm required courses
- [ ] Record screenshots and generate lesson clips from the media pack
- [ ] Clean-VM Windows install, sign-in, and N→N+1 update test

## NEXT — Pilot intelligence

Things that raise real adoption once people are using it.

1. **Second and third guided flows** chosen from pilot evidence (likely roster sign-off and leave approval). Each is data only: a flow XML plus a responsibility.
2. **Guidance insights for the manager:** "Where do people get stuck?" from `security.guidance.event` (deviation and help counts per step). This points at training gaps, not at people.
3. **Notifications that close the loop:** only for a task due soon and not started, an exception assigned to me, or a guided task finished by a direct report. Each says what happened, why it matters and what to do.
4. **Payroll and payment slices:** payroll audit (HR), payroll approval (GM), financial audit and payment approval (Finance), using the same responsibility and guidance pattern.
5. **Evidence on tasks:** photo and attachment upload from the desktop (checklist `photo` items), and enforcing required boolean and photo items on submit.
6. **Server-side consent gate for adoption:** do not score employees who have not acknowledged the monitoring notice.
7. **Manager AI summary:** "Today's attention", a Gemini summary over `get_team_today()` and open exceptions, with each line linking to its records.
8. **Owner "How are we doing?"**: the same pattern over `security.owner.digest` and 7-day trends, evidence-cited.
9. **Code-signing certificate** (removes the SmartScreen warning).
10. Accessibility pass (WCAG 2.2 AA contrast from AGENT-FINDINGS, focus return, keyboard-only walkthrough).
11. Sentry, or equivalent crash reporting, if the local log proves insufficient.

## LATER — DeployGuard Platform

Only after the DogForce workflow is proven with real usage data.

- Fastify `/v1` API and Platform Postgres; the Odoo bridge becomes the adapter.
- Auth exchange per DG-ADR-007 (assertion → device-bound tokens), brokered Odoo SSO, device registration and revocation.
- Swap `src/api/*.ts` internals from `odoo_call_kw` to `/v1`. Components do not change.
- Event bus/outbox consumers for adoption and exceptions; SSE for live updates.
- Offline per DG-ADR-011 (SQLCipher + command outbox) **if** a field use case appears.
- Extract `packages/ui` / `packages/app` when the web client exists.
- Release channels (`pilot` / `stable`) and `min_supported_version`.

## FUTURE — Multi-tenant SaaS

Only when a second customer needs it.

- Tenant discovery (company code), RLS tenancy, per-tenant branding within the token system.
- Per-tenant AI provider configuration and data-residency controls.
- Guided-flow and course marketplace/templates across tenants.
- Billing, licensing and self-serve onboarding.
