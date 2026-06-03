# ADR-0008: Odoo Session Authentication for Mobile

**Date:** 2026-05-28  
**Status:** Accepted

## Context

The mobile app (`mobile/`) needs authenticated access to Odoo for supervisors, managers, and owners. Options:

| Approach | Pros | Cons |
|----------|------|------|
| **Odoo JSON-RPC session** (`/web/session/authenticate`) | Reuses user/password, groups, session invalidation | Cookie/session handling on mobile |
| **Custom JWT/OAuth service** | Mobile-native token flow | Extra auth server, duplicate user store |
| **API keys per device** | Simple for M2M | Poor fit for human supervisors, rotation pain |

`security_mobile` controllers use `auth="user"` — standard Odoo session enforcement.

## Decision

Authenticate mobile clients via **standard Odoo session authentication**:

1. `POST /web/session/authenticate` with `{ db, login, password }`
2. Store `session_id` in Expo Secure Store
3. Send `X-Openerp-Session-Id` header and cookie on `/api/security/mobile/*` requests
4. Enforce roles with `@require_group()` against `security_base` security groups

PIN quick re-auth is **planned** (`security_mobile_pin_hash` on `hr.employee`) but not implemented as a separate token system — it would re-validate within the Odoo session model.

## Consequences

### Positive

- No parallel identity system; Odoo ACLs and groups apply uniformly to web and mobile
- Logout via `/web/session/destroy` invalidates server session
- Implementation in `mobile/src/api/auth.ts` and `client.ts` is minimal

### Negative

- Mobile must handle Odoo session expiry (401/403) and re-login UX
- CSRF disabled on API routes (`csrf=False`) — acceptable for session header auth but requires HTTPS in production
- Role detection in mobile app uses heuristics (username/name) — real enforcement is server-side only

### Neutral

- Documented in [API.md](../../API.md) and [docs/security_mobile.md](../security_mobile.md)
- Future FCM push (`security_mobile_device_token`) does not change auth model
