# DeployGuard Design System — Rollout Plan

Ordered plan for progressively applying `docs/DEPLOYGUARD_DESIGN_SYSTEM.md` to
the rest of the backend. Each phase is independently shippable — apply the
retrofit checklist, verify, ship, move to the next phase. Don't batch phases
together; that's how the original Command Center sprawl happened.

Sequencing logic: fix known regressions first, then retrofit by traffic
(what guards/supervisors/managers touch daily beats what an owner opens
monthly), then finance, then the long tail, then new modules.

---

## Phase 0 — Shell + Home (shipped)

`security_shell`: global rail + nav panel, role-aware Home dashboard, old
Command Center modal retired, app switcher polish, nav-coverage fixes (Full
Menu fallback, Help Centre + WhatsApp promoted into the curated tree), and
the mega-menu full-viewport overlay fix (`.rmm-overlay` now scoped to the
canvas instead of covering the rail/nav panel). See `HANDOFF-deployguard-shell.md`
for the original spec.

---

## Phase 1 — Daily operations screens

The screens guards, supervisors and dispatchers touch every shift. Highest
visibility, highest value from consistency.

| Screen | Module | Notes |
|---|---|---|
| Operations Dashboard | `security_operations` (`ops_dashboard.*`) | Already reachable as "Command Centre" in the nav tree; retrofit tokens + numerals. |
| Interactive Site Hub | `security_operations` (`site_hub.*`) | |
| Rostering Hub | `security_shift_planner` (`rostering_hub.*`) | Has its own mobile bottom-nav (`.rh-bottom-nav`) — audit for collision with the shell's <900px rail-as-bottom-bar before/while retrofitting. |
| Roster Board | `security_shift_planner` (`roster_board.*`) | |
| Attendance Grid / Posting Console | `security_attendance` | |
| WhatsApp Control Room + Dashboard | `security_ai_whatsapp_bridge` | Now first-class nav leaves (§ nav_catalog); visually still pre-shell. |

**Done when:** all six use `--ds-*`/`--dgs-*` tokens, numerals are mono, no
stray full-viewport overlays, and each reads correctly at 1280/900px.

---

## Phase 2 — Retire or restyle the mega menus

Five screens share the `.rmm-overlay`/`.rmm-container` pattern: Rostering
Mega Menu, Workforce Mega Menu, Fleet Mega Menu, Equipment Mega Menu,
Clients & Sites Mega Menu. They were built as fullscreen "quick launcher"
takeovers — the same job the curated nav tree and Home's Modules section now
do, natively, without a modal.

**Decision needed before this phase starts:** retire them the same way the
old Command Center was retired (keep the action xmlid/tag if anything still
points at it, delete the OWL component, remove the now-redundant menu
entries), or keep them as genuinely useful secondary "quick jump" panels and
restyle to `--dgs-*` tokens. Given the shell already covers this job, retiring
is the recommended default — flag any specific reason to keep one (e.g. a
workflow that genuinely benefits from a focused overlay) before keeping it.

---

## Phase 3 — Finance & payroll

Owner/finance-only, lower frequency than Phase 1, but high visual
inconsistency today (several ad hoc dashboards with their own color choices).

- Billing Command Center (`security_billing`)
- Payroll Command Center + Payslip Designer (`security_payroll_core`)
- ZRA Smart Invoice screens (`security_zra_invoice`)
- Reconciliation console (`security_reconciliation_core`)
- Accounting Controls (`security_accounting_controls`)
- Revenue Dashboard (`security_billing`)

---

## Phase 4 — People & compliance

- Workforce Dashboard (`security_base`)
- Equipment Dashboard (`security_equipment`)
- Documents & compliance screens (`security_documents`) — see the dedicated
  call-out below; this phase is a token retrofit of the *existing* screens,
  not the planned Documents module rebuild.
- Leave, Discipline screens

---

## Phase 5 — Reporting & analytics

- Executive Dashboard, Compliance Dashboard, Client Service Reports
  (`security_reporting`, `security_client_reports`)

---

## Phase 6 — Long tail

Everything else reachable only via Full Menu today: Help Centre, AI chat
widget, Notifications, Licensing, Backup Vault, Product Tour, White-label
theming settings, demo-site config, migration tools. Low traffic, fine to
leave stock-styled (they already inherit the base design system for their
list/form parts) until there's spare capacity.

---

## Phase 7 — New modules (build with tokens from day one)

These are the `soon: true` leaves in `nav_catalog.js` — **do not build them
against ad hoc CSS and retrofit later; start on `--ds-*`/`--dgs-*` tokens.**

### Armed Response — shipped (dispatch board, live map, armoury)
`security_armed_response` is live: `security.response.unit` (commander,
members, assigned `security.vehicle`, status) and `security.response.dispatch`
(source, site, priority, state machine new → acknowledged → dispatched →
on scene → resolved/cancelled, response-time compute). The dispatch board
is a kanban grouped by state, styled on `--ds-*`/`--dgs-*` tokens
(`dispatch_board.css`).

Live Callout Map uses Google Maps (JS API key set in Settings → Armed
Response — `security_armed_response.gmaps_api_key`, no default, shows a
clear empty state until one is added). Marker colors are read from the
same `--ds-success/-warning/-danger/-info` tokens at runtime, not
hardcoded, so the legend and the pins can never drift apart. Positions
come from `security.response.unit.last_lat/last_lng`, updated either
manually on the unit form or by POSTing to
`/api/armed_response/units/<id>/ping` with that unit's own `gps_token`
(rotatable per-unit, not a single shared module secret). **No GPS/fleet-
tracking provider is wired up yet** — that endpoint is the only thing that
changes once one is chosen; the map, the data model, and the dispatch
workflow are already done and don't need to change.

Armoury did **not** get a new model — `security_equipment` already modeled
serialized, license-tracked items (`requires_license` on
`security.equipment.type`, `license_number`/`license_expiry` on
`security.equipment.item`) generically enough to cover firearms. The
"Armoury Ledger" nav leaf is a filtered `ir.actions.act_window` over the
existing `security.equipment.allocation` register
(`domain=[("equipment_type_id.requires_license", "=", True)]`), reusing
its stock kanban/list/form views — zero duplication, zero risk to the
existing equipment data. A `group_armoury_custodian` role exists for when
tighter row-level access is wanted; no record rule was added yet (deferred
deliberately — see the module's own notes — to avoid touching access on a
model with live production data without a dedicated review).

Not done: telephony-linked call capture (`caller_name`/`caller_number` are
plain manual fields for now, matching the Telephony leaf's own `soon: true`
status).

### Documents — current module is certification tracking, not a document register
`security_documents` today is guard certification/expiry tracking
(`security.document.type`, `security.employee.document` — a binary
attachment field, issue/expiry dates, verification workflow). It is *not* a
general document register (no categorization beyond guard certs, no
versioning, no bulk upload, no non-employee documents like contracts or
site SOPs). This matches the original shell brief exactly: "Documents" is
one of the six explicitly out-of-scope planned modules, hence
`nav_catalog.js`'s `People → Compliance → Document register (soon)` leaf.
Two separate tracks going forward:
- **Phase 4 retrofit** (above): re-skin the existing certification-tracking
  screens with shell tokens — no scope change, just visual consistency.
  Already reachable via the curated tree as "Documents & certifications."
- **Future module**: a proper document register (contracts, site SOPs,
  client-facing documents, versioning, richer categorization) — scope this
  as its own module when prioritized, wire it to the existing `soon: true`
  "Document register" leaf, and build it on shell tokens from the start.

### Also `soon: true` today (unchanged from the original brief)
Armoury ledger, Fleet & tracking map, Client portal, Recruitment
(applicant pipeline, vacancies), Telephony, CRM bridge (no action exists
anywhere in the repo for this one — not even a stub).

---

## Cross-cutting, do anytime

- **Menu-coverage audits**: whenever a new module or menu item ships, add it
  to `nav_catalog.js` (curated) if it's a primary workflow, or trust Full
  Menu to cover it automatically (it always does — Full Menu reads Odoo's
  live menu service, not a hardcoded list). Never let a new screen exist
  only behind raw XML with no curated or fallback path — Full Menu already
  guarantees this, but a genuinely important screen deserves a curated leaf
  too.
- **Emoji in menu labels**: only `security_base`'s menu labels were cleaned
  up in Phase 0 (that was the original brief's stated scope). Several other
  modules still have `⚡` in menu names (`security_fleet`, `security_equipment`,
  `security_operations`, `security_shift_planner` mega-menu action names).
  Sweep these opportunistically as each module comes up in its rollout phase
  rather than as a standalone pass.
