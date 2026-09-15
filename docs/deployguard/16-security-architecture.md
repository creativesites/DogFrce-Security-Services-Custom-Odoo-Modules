# 16 — Security Architecture

> Status: Draft · Owner: Platform architecture + security
>
> Related: [DG-ADR-007](adr/DG-ADR-007-authentication.md) (single login), [DG-ADR-008](adr/DG-ADR-008-multi-tenancy.md) (isolation), [DG-ADR-018](adr/DG-ADR-018-odoo-bridge-addons.md) (bridge), [23-audit-system](23-audit-system.md). Target: OWASP ASVS L2 (NFR-05).

---

## 1. Assets and adversaries

| Asset | Why it matters |
|---|---|
| Employee work behaviour and adoption data (P1) | Personal data; misuse could harm employment relationships |
| Training, competency and certification records | Feed operational eligibility decisions |
| Odoo integration credentials and SSO ticket minting | Compromise implies broad ERP access for a tenant |
| Platform tokens, device keys, bridge signing keys | Impersonation |
| Evidence files (site photos, signatures) | Client-sensitive operational detail |
| Exception and incident metadata | Reveals security posture of client sites |

| Adversary | Capability assumed |
|---|---|
| External attacker | Internet access to Platform and Odoo endpoints; credential stuffing; phishing |
| Malicious or curious insider (tenant) | Valid low-privilege account, wants other people's data |
| Malicious platform insider | Infrastructure access — constrained by break-glass and audit |
| Compromised desktop | Malware on a supervisor's Windows machine |
| Compromised tenant Odoo | Could feed false events or attempt SSRF into Platform |

## 2. Threat model (abbreviated STRIDE)

| Threat | Vector | Mitigation |
|---|---|---|
| Spoofing | Forged Odoo assertion | Ed25519 signature verified by `kid`, `aud`, `exp` ≤ 60 s, single-use `jti`, device proof |
| Spoofing | Stolen refresh token | Device-bound proof, rotation with reuse detection (family revocation) |
| Tampering | Forged webhook | HMAC-SHA256 with timestamp window and secret rotation; contract validation |
| Tampering | Client asserting another actor | Server stamps `tenant_id`/`actor` from the token; client-supplied identity fields ignored |
| Repudiation | "I didn't approve that" | Audit log with actor, device, correlation, before/after digests |
| Information disclosure | Cross-tenant leakage | RLS + forced policies + CI conformance tests |
| Information disclosure | Over-broad ERP reads | Facade methods with field allowlists; integration user least privilege |
| Information disclosure | Telemetry leakage | PII scrubbing; no event `data` in logs; no free text in client telemetry |
| DoS | Login/ticket flooding | Rate limits per account/IP/device; Cloud Armor/WAF; per-tenant quotas |
| Elevation | SSO ticket for an admin account | Tickets refuse `base.group_system` and require DeployGuard access flag |
| Elevation | Scope bypass | Central policy evaluation; deny-by-default; tests per role/scope |
| SSRF | Tenant-configured Odoo URL | HTTPS only, DNS resolution allowlist, private/link-local ranges blocked, redirects not followed |
| Supply chain | Malicious dependency | Lockfiles, `pnpm audit`/`cargo audit` in CI, Dependabot, pinned Tauri plugins, SBOM per release |

## 3. Authentication

Per [DG-ADR-007](adr/DG-ADR-007-authentication.md): Odoo credentials + TOTP → signed assertion → Platform tokens (15-minute access, rotating device-bound refresh, 14-day idle / 30-day absolute). Re-verification of credentials is required for sensitive actions (12-hour freshness) and after absolute expiry.

Hardening requirements for the bridge endpoints:

- progressive throttling and lockout, with alerts on bursts;
- constant-time credential comparisons (delegated to Odoo's own check);
- no user enumeration in error messages;
- TOTP challenge IDs are single-use and expire in 5 minutes;
- all outcomes audited (success, failure reason class, IP, device).

## 4. Authorisation

- **Permissions are code-defined constants** (e.g. `work.task.verify`, `training.course.publish`, `adoption.view.team`).
- **Roles** map to permission sets; tenants may create custom roles from the same set.
- **Scope** is evaluated for every decision: `tenant`, `site`, `team`, `self`, plus `reporting_line` for people-related reads.
- **Policy function** `can(actor, action, resource)` lives beside each module and is the only authorisation path; there are no ad-hoc role string checks in handlers.
- **Deny by default**: unknown action or missing scope → deny, logged at debug with the reason code.
- **Row-level filters** are derived from scope (e.g. supervisor sees exceptions where `site_id ∈ assigned sites`), applied in queries *and* re-checked on mutation.
- **Sensitive reads** (another person's adoption factors, support content, audit) require explicit permissions and are themselves audited.

## 5. Platform staff and break-glass

| Control | Rule |
|---|---|
| Default access | Platform staff see tenant metadata and health only |
| Break-glass | Time-boxed (60 min default), reason required, tenant admin notified, auto-expiry, full audit of every record viewed |
| Production access | No direct database console access for routine work; scripted, reviewed runbooks; all sessions recorded |
| Separation | Deploy permissions and data-access permissions are different roles |

## 6. Secrets and key management

| Secret | Storage | Rotation |
|---|---|---|
| Tenant Odoo API key | Envelope-encrypted, KMS-wrapped | On demand; tested by connection test |
| Webhook HMAC secret | Same, with previous-secret window | 90 days; 24-hour dual-secret window |
| Bridge signing keypair | Private key in Odoo (encrypted with a server-side key outside the DB); public key in Platform by `kid` | 180 days with overlap |
| Platform token signing keys | KMS or secret manager, versioned `kid` | 90 days, overlapping validation |
| Device private key | OS keychain on the device | Regenerated on re-install; revocable centrally |
| Local DB encryption key | OS keychain | Per install |
| Email/AI provider keys | Secret manager | Per provider policy |

**Never** in: git, `ir.config_parameter` plaintext, container images, logs, error messages, AI context.

## 7. Desktop client security

- **Tauri capabilities**: an explicit allowlist of IPC commands; no general filesystem, shell or HTTP proxy capability exposed to the WebView.
- **Two isolated webviews**:
  1. the Platform app (our origin, strict CSP, IPC capabilities);
  2. the **Odoo window** (tenant Odoo origin, **zero IPC capabilities**, no preload injection).
  They share no JavaScript context.
- **CSP** for the app window: `default-src 'self'; connect-src 'self' https://api.<domain>; img-src 'self' data: blob: https://<storage>; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; object-src 'none'`.
- **Token handling**: the refresh token and device key live in Rust/keychain; the WebView receives only short-lived access tokens in memory. Renewal happens through an IPC command.
- **Local data**: SQLCipher-encrypted SQLite; evidence files encrypted at rest; wiped on device revocation or sign-out (with a warning if unsynced work exists).
- **Updates**: Tauri updater with signed manifests and artefacts; signature verification before install; downgrade prevention; code-signed installers (OQ-7).
- **Deep links**: `deployguard://` payloads are validated and treated as untrusted input; they can only navigate to known routes, never execute commands.
- **Anti-tamper posture**: we do not attempt DRM-style protection; the threat model assumes a compromised endpoint means that user's data is exposed, which is why tokens are short-lived and device-revocable.

## 8. API and web security

- TLS 1.2+ (prefer 1.3), HSTS, secure cookies (`HttpOnly`, `Secure`, `SameSite=Strict`) for the web refresh cookie, CSRF double-submit for cookie-authenticated endpoints.
- Input validation by Zod at every boundary; strict content types; request size limits; file type and size validation plus server-side image re-encoding.
- Output encoding by React; rich text (lessons, articles) sanitised server-side and again client-side (DOMPurify) with an allowlist.
- Rate limits: global, per tenant, per user, per endpoint class; stricter for auth, ticket minting, exports and AI.
- CORS: explicit origin allowlist (Platform web origins; the bridge allows only the Platform origin).
- Security headers on the web app: CSP, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`.
- Object storage: no public buckets; time-limited signed URLs; server-side encryption; antivirus scan of uploads before they are downloadable.

## 9. Employee privacy by design

| Principle | Implementation |
|---|---|
| Purpose limitation | Adoption data is used for support, training and operational management only; export to HR/discipline systems is blocked (PR-ADO-07) |
| Data minimisation | Client telemetry records workflow keys and outcomes, never content, keystrokes, screenshots or location |
| Transparency | A monitoring notice is shown at first sign-in and acknowledged (`PolicyAcknowledgement`); employees can see what is collected about them |
| Access | Employees can view their own training status and (per OQ-13) their own adoption factors |
| Proportionality | Scores are non-disciplinary by policy and labelled as such in the UI |
| Retention | Per class ([13](13-event-architecture.md) §8); automated deletion |
| Legal | OQ-6 must be closed before pilot (contract clauses, Namibian obligations; Zambia DPA 2021 for later tenants) |

## 10. Inherited ERP findings (prerequisites)

These exist in DeployGuard ERP today ([00](00-current-state.md) §7) and must be resolved before or during the pilot, because the Platform's security depends on the same environment:

| ID | Action | When |
|---|---|---|
| S-1 | Rotate every credential exposed in repo docs and `odoo.conf`; remove secrets from the image and docs | Stage 0 (before pilot) |
| S-2 | Replace the tokenised git remote with a credential helper | Stage 0 |
| S-3 | Authenticate the WhatsApp webhook and stop publishing the sidecar port on the host | Stage 0 |
| S-4 | Rate-limit and harden mobile PIN/login endpoints; migrate mobile to bridge auth | V2 (mitigate now with rate limiting) |
| S-5 | Remove the fabricated-200 offline pattern in mobile | V2 (Platform never repeats it) |
| S-6 | Reduce `sudo()` use and add record rules in ERP modules the bridge exposes | Ongoing; bridge facade limits exposure meanwhile |
| — | HTTPS for every tenant Odoo; verified before connection is accepted | Stage 0 |

## 11. Assurance activities

| Activity | Cadence |
|---|---|
| Threat-model review | Per phase with new external surface (P1, P2, P7, P9) |
| Dependency scanning and SBOM | Every CI run / every release |
| Secret scanning (repo + CI) | Every push |
| Authorisation test matrix (role × scope × action) | Every CI run |
| RLS conformance tests | Every CI run |
| Bridge security tests (signature, replay, ticket single-use, throttle) | Every CI run |
| Independent security review of auth + bridge | Before pilot |
| Penetration test | Before onboarding the second tenant |
| Restore and key-rotation drills | Quarterly |
| Incident response runbook exercise | Before pilot, then annually |
