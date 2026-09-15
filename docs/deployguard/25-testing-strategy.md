# 25 — Testing Strategy

> Status: Draft · Owner: Platform engineering
>
> Principle: the rules that decide what people are told to do (expected work, scoring, exceptions, escalation) are **pure and heavily tested**; everything else is tested where failure is most likely — boundaries and integrations.

---

## 1. Layers

| Layer | Tool | Scope | Gate |
|---|---|---|---|
| Unit (domain) | Vitest | `packages/domain`: recurrence, expected work, scoring, exception conditions, escalation timing, redaction | Every PR; **≥ 95 % line coverage in this package** |
| Unit (modules) | Vitest | Command/query logic with fakes | Every PR |
| Integration (DB) | Vitest + real PostgreSQL (Testcontainers) | Repositories, migrations, RLS, partitions, event dispatch, job handlers | Every PR |
| Contract (API) | Vitest + OpenAPI schema validation | Request/response conformance; N-1 client compatibility | Every PR |
| Contract (Odoo) | Odoo 19 container + bridge addons | Facade methods, webhook signing/format, SSO ticket flow, event payloads vs vendored schemas | Every PR touching bridge or adapter; nightly full run |
| Odoo addon tests | Odoo test framework | Bridge models, outbox, throttling, ticket single-use, permissions | ERP repo CI |
| Desktop native | `cargo test` | Keychain, SQLCipher store, outbox ordering, token refresh, deep-link validation | Every PR touching `src-tauri` |
| E2E | Playwright (web) + WebDriver (Tauri) | Critical journeys (§3) | Every PR (smoke), nightly (full) |
| Visual parity | Playwright screenshots vs `security_shell` references | Rail, nav panel, cards, tiles, pills, chips, coverage bar | Nightly + release |
| Accessibility | axe in component catalogue + E2E checks | WCAG 2.2 AA rules | Every PR |
| Performance | k6 (API), Lighthouse (web), startup timing (desktop) | NFR-01/02 budgets | Nightly + release |
| Security | ASVS checklist, authz matrix, RLS conformance, dependency and secret scanning | [16](16-security-architecture.md) §11 | Every PR + release |
| AI evals | Vitest + fixture datasets | Capability output schema, citation integrity, refusal behaviour, regression on prompt change | On change to prompts/capabilities |

## 2. Test data

- **Fixture tenant** generator: sites, shifts, users, roles, templates, courses, and a scripted month of events, seeded deterministically from a fixed random seed.
- **No production data** in any environment other than production. DogForce data is never copied into staging; staging connects to ERP **staging**.
- Odoo fixtures use the ERP repo's demo modules (isolated demo data, ADR-0014) plus a bridge-specific fixture set.

## 3. Critical journeys (must pass before every release)

1. First run: company code → sign-in with Odoo credentials + TOTP → device registered → Home loads.
2. Supervisor completes a site-visit checklist with a photo, submits, supervisor-manager verifies.
3. Attendance expectation: `odoo.attendance.batch.submitted` auto-completes the expected item; missing it raises an exception and escalates on schedule.
4. Offline: complete a checklist offline, queue, reconnect, sync; then the conflict variants in [20](20-offline-strategy.md) §5.
5. Training: assignment → lesson → assessment fail → retry → pass → practical sign-off → competency evidence.
6. Exception lifecycle: raise → notify → acknowledge → resolve, with the timeline and audit correct.
7. Open in Odoo: ticket brokered, Odoo window lands on the right record; refusal path for an Odoo admin account.
8. Revocation: deactivate the user in Odoo → sessions revoked within 5 minutes → desktop locked.
9. Adoption: a seeded month produces expected snapshots, and the explanation screen cites the right events.
10. Feedback → support request → knowledge article link → resolution.

## 4. Non-functional gates

| Gate | Threshold |
|---|---|
| API p95 read latency under pilot-scale load | ≤ 300 ms |
| Event dispatcher lag p95 at 50 events/s | ≤ 5 s |
| Desktop cold start (cached) on 4 GB VM | ≤ 3 s |
| Initial web JS (shell + Home) | ≤ 250 KB gzip |
| Migration run time on a pilot-size dataset | ≤ 60 s |
| Zero `high`/`critical` dependency advisories | required |

## 5. Practices

- Rules change → fixture test first (test-driven, in the spirit of ADR-0015).
- Every bug fix adds a regression test naming the defect.
- Flaky tests are quarantined with an owner and a deadline, never silently retried.
- Each PR states which journeys it could break; release checklists run the full set.
- Seeded fixtures are used for screenshots in documentation, so docs and behaviour stay aligned.
