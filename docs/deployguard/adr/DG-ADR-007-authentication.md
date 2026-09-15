# DG-ADR-007 — Authentication & Single Login

- **Status:** Accepted in principle (product decision R-7, 2026-09-15); technical details Proposed
- **Date:** 2026-09-15
- **Related:** [16-security-architecture](../16-security-architecture.md), [12-odoo-integration](../12-odoo-integration.md), [17-desktop-architecture](../17-desktop-architecture.md), [DG-ADR-015](DG-ADR-015-relationship-to-odoo-adrs.md), [DG-ADR-018](DG-ADR-018-odoo-bridge-addons.md), existing `docs/adr/0008-odoo-session-auth-for-mobile.md`

## Context

- **Product requirement (R-7):** users must have **one login from MVP day one**. The product owner's rationale: "multiple logins… we are already losing the users."
- **Where the work happens:** every Platform user also needs DeployGuard ERP (Odoo), because the Platform deep-links into Odoo screens for operational work.
- **Existing precedent:** DeployGuard Mobile already authenticates with Odoo sessions (ADR-0008).
- **What Odoo 19 Community provides:**
  - password authentication (`/web/session/authenticate`, `/web/login`);
  - TOTP two-factor (`auth_totp`);
  - password reset (`auth_signup`);
  - user API keys and the bearer-authenticated JSON-2 API.
- **What the Platform still needs:**
  - its own short-lived tokens for its API;
  - device binding;
  - revocation;
  - authorisation scopes independent of Odoo groups.
- **Security gaps to avoid repeating:** the existing mobile PIN endpoint is public, unthrottled and trusts a client-supplied `employee_id` ([00](../00-current-state.md) S-4).

## Decision

**Odoo is the identity provider for tenant users. The Platform is the session and authorisation authority.** A bridge addon (`security_deployguard_bridge`) connects the two with signed assertions and single-use tickets. The Platform never receives or stores end-user passwords.

### 1. Tenant discovery

On first run the desktop (or the web sign-in page) asks for a **company code**, e.g. `dogforce`. The Platform's public discovery endpoint returns the tenant's display name, theme font and branding tokens, the Odoo base URL, and the bridge's public signing key ID. The result is cached on the device.

### 2. Sign-in (credentials go directly to the tenant's Odoo)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant D as Desktop/Web app
    participant B as Odoo + bridge addon
    participant P as DeployGuard Platform

    U->>D: login + password
    D->>B: POST /api/deployguard/v1/auth/login {login, password, device_id, nonce}
    Note over B: rate limit (account, IP, device)<br/>request.session.authenticate(...)
    alt TOTP enrolled or required
        B-->>D: 200 {status: "mfa_required", challenge_id}
        U->>D: 6-digit code
        D->>B: POST /api/deployguard/v1/auth/totp {challenge_id, code}
    end
    Note over B: check user active, internal,<br/>DeployGuard access enabled
    B-->>D: 200 {assertion: JWS(EdDSA), expires_in: 60}
    D->>P: POST /v1/auth/exchange {assertion, device_proof}
    Note over P: verify signature with tenant bridge key,<br/>aud, exp, nonce, device_id; link identity;<br/>load roles/scopes
    P-->>D: {access_token (15 min), refresh_token (rotating, device-bound)}
```

**Assertion claims** (JWS, EdDSA/Ed25519, signed by the tenant's bridge private key):

| Claim | Meaning |
|---|---|
| `iss` | Tenant bridge identifier (Odoo base URL + tenant ID) |
| `aud` | `deployguard-platform` |
| `sub` | Odoo `res.users` ID |
| `emp` | Linked `hr.employee` ID (if any) |
| `login`, `name`, `email` | Profile hints (not authorisation) |
| `groups` | Relevant Odoo group XML IDs (drift detection and role suggestion only) |
| `amr` | `["pwd"]` or `["pwd","otp"]` |
| `auth_time` | When credentials were verified |
| `device_id`, `nonce` | Replay protection and device binding |
| `iat`, `exp` (≤ 60 s), `jti` | Freshness; `jti` recorded for single use |

The bridge **does not** create a long-lived Odoo web session for this call (`save_session` disabled). Credentials are verified, the assertion is minted, and the request ends.

### 3. Platform tokens

| Token | Lifetime | Storage | Notes |
|---|---|---|---|
| Access token (JWT, EdDSA, Platform key) | 15 min | Memory only | Claims: `tenant_id`, `user_id`, `device_id`, `session_id`, `scp` (role-scope set hash), `amr` |
| Refresh token (opaque, 256-bit) | Idle 14 days, absolute 30 days | Desktop: OS keychain via Rust. Web: `HttpOnly; Secure; SameSite=Strict` cookie on the Platform origin | **Rotates on every use.** Reuse of an old token revokes the whole session family. Refresh requires a device proof (signature with the device private key, desktop) |
| Device key (Ed25519) | Life of installation | Generated in Rust; private key in OS keychain | Registered at first exchange; revocable by admin |

**Step-up and re-verification:**

- The Platform requires fresh Odoo credential verification (`auth_time`) after the absolute session lifetime, and for sensitive Platform actions: approving AI actions with consequences, changing tenant integration settings, exporting audit data. The window is 12 hours for these actions.
- Tenant policy can require `amr` to include `otp` for manager, HR, owner and admin roles (OQ-20).

### 4. Opening Odoo without a second login (brokered tickets)

```mermaid
sequenceDiagram
    autonumber
    participant D as Desktop/Web app
    participant P as Platform
    participant B as Odoo + bridge addon
    participant W as Odoo window (webview/tab)

    D->>P: POST /v1/odoo/open {target: action/record}
    Note over P: valid session? user linked?<br/>not an Odoo admin account?<br/>auth_time within policy?
    P->>B: POST /api/deployguard/v1/sso/ticket {odoo_uid, target, device_id}<br/>(integration API key + HMAC)
    B-->>P: {ticket (single-use, 60 s), url}
    P-->>D: {url: https://odoo/deployguard/sso/consume?ticket=…}
    D->>W: open url in dedicated Odoo window
    W->>B: GET /deployguard/sso/consume?ticket=…
    Note over B: validate & burn ticket; bind to uid;<br/>create normal Odoo web session;<br/>redirect to target
    B-->>W: 303 → /odoo/action-…/<id> (session cookie set)
```

Ticket constraints enforced by the bridge:

- single use, TTL ≤ 60 s, bound to `odoo_uid`;
- target path limited to `/odoo/*` and `/web#*` routes;
- **never issued for users in `base.group_system`** or with the settings/technical role;
- requires the user's DeployGuard access flag;
- audited in both systems;
- per-user rate limited.

The Odoo session in the Odoo window follows Odoo's normal lifetime. When it expires, the app silently brokers a new ticket.

### 5. Revocation and lifecycle

- The bridge emits signed events `identity.user.deactivated`, `identity.user.password_changed`, `identity.user.totp_changed` and `identity.access.revoked`. The Platform revokes all matching sessions and refresh families.
- Polling reconciliation (every 5 min) compares linked users' `active` and `write_date` in case a webhook is missed (PR-IAM-10).
- Platform admins can revoke a device, a session or all sessions of a user; this also blocks ticket brokering immediately.

### 6. Platform-native identities (non-tenant)

Only internal staff (`platform_admin`, `support_agent`) have Platform-native accounts: Argon2id passwords plus mandatory WebAuthn (V1; TOTP acceptable until then). They cannot sign in to tenant Odoo through tickets. Tenant data access requires break-glass ([16](../16-security-architecture.md) §5).

## Alternatives

| Option | Why not |
|---|---|
| **Platform as identity provider (OIDC) + Odoo `auth_oauth`** | More standard for SaaS long term, but more MVP work (a full OIDC provider), and Community `auth_oauth` is limited to simple OAuth2 flows with provider-specific validation. It would also force a password migration away from Odoo credentials that users already have. It remains a future option if tenants without Odoo are ever supported. |
| **Two separate logins (Platform + Odoo)** | Rejected by product decision R-7. |
| **Platform backend proxies credentials to Odoo** | Puts every tenant's passwords in transit through Platform infrastructure; larger blast radius; no benefit over a direct client → bridge call. |
| **Reuse the existing mobile `/auth/login` and `/auth/pin` endpoints** | No rate limiting, trusts client `employee_id`, sets sessions manually, no signed output. The bridge endpoints are new and hardened; mobile migrates to them in V2. |
| **Store the Odoo session cookie in the desktop and inject it into the webview** | Depends on webview cookie APIs that vary by platform; long-lived Odoo sessions at rest on disk. Tickets avoid both. |
| **External IdP (Entra ID, Google Workspace, Auth0)** | DogForce staff do not have a common corporate directory; it adds cost and yet another account for field-adjacent staff. Could be added later as an Odoo login method, transparently to the Platform. |

## Tradeoffs

| We gain | We accept |
|---|---|
| **One login** using credentials people already have; no password migration | Platform availability for sign-in depends on the tenant's Odoo being reachable (offline mode uses the existing refresh session, [20](../20-offline-strategy.md)) |
| The Platform never handles end-user passwords | The bridge addon becomes security-critical code and needs a security review and tests before pilot |
| Odoo's TOTP, password reset and deactivation apply everywhere | Every Platform tenant user must be an Odoo internal user (A-5, OQ-8) |
| Device-bound, revocable Platform sessions | A key-management burden: per-tenant bridge Ed25519 keypair (rotation supported via `kid`) plus integration API key and HMAC secret |

## Consequences

- **`security_deployguard_bridge` must ship in P1** with:
  - `auth/login`, `auth/totp`, `sso/ticket`, `sso/consume`;
  - signing-key management (keypair generated in Odoo, public key registered with the Platform, private key encrypted at rest in Odoo using a server-side secret outside the DB);
  - rate limiting;
  - audit;
  - CORS allowlist for the Platform web origin;
  - security tests.
- **ADR-0008 is extended, not superseded:** Odoo sessions remain the authentication primitive in DeployGuard ERP ([DG-ADR-015](DG-ADR-015-relationship-to-odoo-adrs.md)).
- **Odoo must be served over HTTPS** for every tenant before pilot; plain-HTTP demo patterns are not allowed for Platform tenants.
- **Stage 0 of the DogForce rollout adds:** create Odoo internal users for all pilot staff, confirm email delivery for Odoo password resets, and decide the TOTP policy (OQ-20).
- **V2:** DeployGuard Mobile moves from `security_mobile` auth endpoints to the bridge flow, removing the PIN weaknesses (S-4).
