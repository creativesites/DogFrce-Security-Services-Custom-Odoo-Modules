# Known Issues and Technical Debt

Transparent record of current limitations, bugs, specification gaps, and refactoring needs in the DogForce Security Suite. Updated from codebase analysis — not an exhaustive audit.

For architectural rationale behind some trade-offs, see [docs/adr/README.md](docs/adr/README.md).

---

## Known limitations

These affect users, integrators, or go-live readiness today.

### Platform and deployment

| Limitation | Impact |
|------------|--------|
| **No staging/production environment in repo** | Deploy procedures are documented ([DEPLOYMENT.md](DEPLOYMENT.md)) but not provisioned |
| **DogForce production runs Odoo Enterprise separately** | This repo targets Community; cutover path is undefined |
| **No database restore script** | Only `backup-db.sh` exists; restore is manual |
| **`docker-env.sh` may leave `COMPOSE_BIN` unset** | On Linux without `docker-compose` v1, scripts fail if Compose v2 plugin path differs from macOS defaults |
| **No `package-lock.json` in `mobile/`** | CI falls back to `npm install`; builds are not fully reproducible |
| **Docker Desktop must be running before Odoo ops** | Module installs and container restarts require Docker Desktop started manually on macOS |

### Mobile app

| Limitation | Impact |
|------------|--------|
| **Role routing uses heuristics** | `mobile/src/api/auth.ts` infers supervisor/manager/owner from username/name — not from Odoo groups |
| **`employee_id` stores `partner_id`** | Login profile may show wrong employee linkage |
| **No offline support** | All attendance actions require live network to Odoo |
| **PIN quick re-auth not implemented** | `security_mobile_pin_hash` field exists; no PIN endpoint |
| **FCM push notifications not wired** | `security_mobile_device_token` field exists; no push delivery |
| **Physical device requires LAN IP** | `localhost` in `client.ts` does not work on real phones |

### Mobile API (`security_mobile`)

| Limitation | Impact |
|------------|--------|
| **Wrong field name `batch_id` on attendance records** | Controllers query `batch_id`; model field is `attendance_batch_id` — posting sheet slots often empty |
| **Owner KPIs use invalid related path** | `batch_id.attendance_date` should be `attendance_batch_id.attendance_date` |
| **Overtime note field mismatch** | Manager endpoint writes `overtime_note`; model field is `overtime_approval_note` |
| **No `action_capture` on attendance batch** | Submit endpoint falls back to `state = captured` without full capture workflow |
| **No automated API tests** | Regressions only caught manually ([API.md](API.md)) |

### Payroll and statutory (Namibia)

| Limitation | Impact |
|------------|--------|
| **Saturday and night premiums not applied** | `saturday_multiplier` and `night_shift_multiplier` exist on rule set but payroll compute ignores them |
| **No shift split across midnight/holiday boundaries** | Spec requires splitting; single premium category per attendance record |
| **Payroll not signed off for production** | Tests exist but DogForce finance manual verification still required |
| **`security_payroll_core` depends on `security_l10n_na`** | Cannot install country-neutral payroll without Namibia pack |

### Payroll and statutory (Zambia)

| Limitation | Impact |
|------------|--------|
| **2026 PAYE brackets unconfirmed** | `security_l10n_zm/data/security_l10n_zm_data.xml` contains a 2026 rule set copied from 2025; update once the Zambia Revenue Authority publishes 2026 budget brackets |
| **WCF rate is per-company assessment** | Default rate is WCFCB Class IX (security industry); confirm and update `wcf_rate` per actual WCFCB assessment letter |
| **ZRA VSDC endpoint must be configured** | `ir.config_parameter` key `zra.vsdc_url` and `zra.api_key` must be set before submissions are live; no validation warning if left blank |
| **ZRA cancellation only voids locally if VSDC is unreachable** | `action_cancel` falls through to local void on network error; submission log will show `error` state for reconciliation |

### Operations and attendance

| Limitation | Impact |
|------------|--------|
| **No auto-roster generation** | Manual roster only ([ADR-0012](docs/adr/0012-manual-roster-before-auto-roster.md)) |
| **Missing roster validations from spec** | No 12-hour rest rule, consecutive-day limit, or understaffing alert automation |
| **`override_reason` on roster slot does not bypass constraints** | Supervisor override audit field exists; hard validation still blocks assignment |
| **Grade comparison uses `sequence` field** | Higher sequence = lower grade — implicit, not documented in UI |
| **Certification expiry not tracked per employee** | `expiry_required` on certification master only; no expiry dates on guard records |
| **GPS / device clock-in deferred** | Phase 1 uses supervisor manual marking only |

### Leave

| Limitation | Impact |
|------------|--------|
| **No automatic accrual engine** | `accrual_rule_note` is text only; balances updated manually |
| **No de-duplication with attendance absence** | Approved leave vs AWOL/absence overlap not fully reconciled in payroll |

### Billing and accounting

| Limitation | Impact |
|------------|--------|
| **No Odoo Accounting / GL integration** | Custom `security.billing.invoice` does not post to `account.move` |
| **Bank statement import not implemented** | Spec item deferred |
| **Reconciliation is manual reference matching** | No bank feed; `action_match_bank_reference` is clerk-driven |
| **Amount-in-words is simplified** | `{amount} {currency} Only` — not full Namibian legal wording |
| **Auto-invoicing from roster/attendance incomplete** | Partial generation logic; not full contract automation |
| **2FA for accounting roles not implemented** | Backlog item |

### Missing modules and migration

| Limitation | Impact |
|------------|--------|
| **Outdated user/technical guides** | `docs/CURRENT_MODULES_*` files have been superseded; refer to [ARCHITECTURE.md](ARCHITECTURE.md) for current module coverage |

### Documentation drift

| Limitation | Impact |
|------------|--------|
| **Guides partially superseded** | [ARCHITECTURE.md](ARCHITECTURE.md), [API.md](API.md), and module manifests are current source of truth |

---

## Technical debt and refactoring priorities

Developer-facing items ranked by risk and effort. Use for sprint planning and PR scoping.

### P0 — Fix before mobile or production go-live

| Item | Location | Refactor |
|------|----------|----------|
| Mobile API field names | `security_mobile/controllers/*.py` | Replace `batch_id` → `attendance_batch_id`; fix owner KPI domain |
| Overtime note field | `manager.py` | Write `overtime_approval_note` not `overtime_note` |
| Attendance batch submit workflow | `security_attendance` + `supervisor.py` | Implement `action_capture()` aligned with `action_generate_from_roster()` |
| Mobile role detection | `mobile/src/api/auth.ts` | Fetch Odoo groups from session or dedicated `/me` endpoint |

### P1 — Payroll and compliance correctness

| Item | Location | Refactor |
|------|----------|----------|
| Unused premium multipliers | `security_payroll_core`, `security_attendance` | Categorize Saturday/night hours; apply `saturday_multiplier`, `night_shift_multiplier` |
| Midnight/holiday shift split | `security_attendance` / payroll | Split attendance records or earning lines at boundary times |
| Decouple payroll from Namibia | `security_payroll_core/__manifest__.py` | Depend on abstract rule interface; `security_l10n_na` supplies data only |
| Expand payroll tests | `tests/` | Bracket boundaries, Saturday/night, split scenarios per backlog |

### P1 — Billing and finance bridge

| Item | Location | Refactor |
|------|----------|----------|
| Accounting integration | New bridge module | Sync `security.billing.invoice` → `account.move` when Accounting installed |
| Amount-in-words | `security_billing` | Proper NAD legal text generator |
| Bank import | New module or OCA | Statement import per spec |

### P2 — Operations completeness

| Item | Location | Refactor |
|------|----------|----------|
| Roster rest/consecutive rules | `security_operations` | Add `@api.constrains` for labour rules |
| Understaffing alerts | `security_operations` | Compare rostered vs `required_guard_count` / contract |
| Supervisor override flow | `security.roster.slot` | Allow override with reason to bypass selected constraints |
| Employee certification expiry | `security_base` | `security.employee.certification` with expiry date + roster block |
| Explicit grade rank | `security.grade` | Replace sequence proxy with `rank` integer |

### P2 — Leave engine

| Item | Location | Refactor |
|------|----------|----------|
| Worked-time accrual | `security_leave` | Scheduled job from attendance payable hours |
| Leave vs attendance dedup | `security_payroll_core` | Skip no-work-no-pay when approved leave covers absence |

### P3 — Quality, tooling, and hygiene

| Item | Location | Refactor |
|------|----------|----------|
| Test coverage gaps | Modules without tests | Operations, leave, mobile HttpCase; attendance now implemented in `security_attendance/tests/` |
| No Python/TS linters in CI | repo root | Add ruff/pylint-odoo, ESLint; gate in `.github/workflows/ci.yml` |
| `scripts/restore-db.sh` | `scripts/` | Mirror backup script |
| Root scratch files | `eq.xml`, `fl.xml` | Remove or move into proper module views |
| Equipment module author metadata | `security_equipment/__manifest__.py` | Correct author field |
| `docker-env.sh` Linux Compose detection | `scripts/docker-env.sh` | Default to `docker compose` when plugin available |
| `mobile/package-lock.json` | `mobile/` | Commit lockfile; use `npm ci` in CI |
| Demo data hook maintenance | `security_demo_data/hooks.py` | Keep aligned with model changes; consider XML fixtures for CI |

### P3 — Architecture evolution

| Item | Notes |
|------|-------|
| Enterprise adapter modules | Optional `security_payroll_enterprise`, `security_billing_account` without forking core |
| Auto-roster optimizer | Phase 3 — separate module to avoid bloating `security_operations` |
| Offline mobile queue | Requires sync protocol and conflict resolution design |

---

## Specification coverage snapshot

High-level gap vs DogForce functional specification:

| Area | Status |
|------|--------|
| Guard profiles, grades, certs | **Mostly implemented** — expiry per employee missing |
| Manual roster + basic validation | **Implemented** — rest/consecutive/understaffing missing |
| Attendance posting sheet | **Implemented** — mobile API bugs affect field use |
| Leave accrual/deduction | **Partial** — manual balances, no accrual engine |
| Namibia PAYE/SSC/premiums | **Partial** — Sunday/holiday/OT; Saturday/night/split missing |
| Zambia NAPSA/NHIMA/WCF/PAYE | **Implemented** — `security_l10n_zm`; 2026 PAYE brackets pending budget confirmation |
| ZRA Smart Invoice (Zambia fiscal) | **Implemented** — VSDC submit/cancel, bulk wizard, exponential backoff retry |
| Loans, discipline, equipment deductions | **Basic** — payslip integration present |
| Client invoicing | **Partial** — custom invoices, no GL |
| Bank reconciliation | **Minimal** — payment records only |
| Compliance reports (SSC, PAYE exports) | **Not implemented** |
| In-app Help Centre | **Implemented** — country-aware articles; Namibia and Zambia content seeded |
| Migration from DogForce Enterprise | **Module exists** (`security_dogforce_migration`); cutover tooling ongoing |
| Auto-roster | **Deferred** (ADR-0012) |
| Mobile field app | **Scaffold** — API + UI; production blockers above |

---

## How to report new issues

1. Confirm the issue is not already listed here
2. Open a GitHub issue with reproduction steps
3. For mobile API bugs, include curl example from [API.md](API.md)
4. For payroll bugs, attach expected vs actual amounts and test period
5. Submit PR with regression test when fixing P0/P1 items ([TESTING.md](TESTING.md))

When an item is fixed, remove or strike it from this document in the same PR.

---

## Related documentation

| Document | Description |
|----------|-------------|
| [docs/adr/README.md](docs/adr/README.md) | Why intentional trade-offs were made |
| [API.md](API.md) | Mobile API known implementation notes |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Architectural debt callouts |
| [TESTING.md](TESTING.md) | Test gaps |
