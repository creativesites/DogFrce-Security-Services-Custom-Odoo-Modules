# ADR-0009: Thin Expo Mobile Client with REST API Layer

**Date:** 2026-05-28  
**Status:** Accepted

## Context

Supervisors need field tools for posting sheets, presence marking, and check-in/out. Managers need multi-site dashboards and overtime approval. Owners need KPIs.

Options:

- **Odoo responsive web UI only** — no offline, poor mobile UX for quick marking
- **Full offline-first mobile app with embedded business rules** — duplicate logic, sync conflicts
- **Thin client + server API** — business rules stay in Odoo; mobile handles UI and transport

Tech stack options for mobile: native iOS/Android, Flutter, React Native/Expo.

## Decision

Build a **thin Expo (React Native) client** in `mobile/` that:

- Contains **no business rules** — all validation and computation in Odoo models
- Calls custom JSON endpoints in `security_mobile` (`/api/security/mobile/*`)
- Uses Expo Router for role-based screens: `(supervisor)`, `(manager)`, `(owner)`
- Uses Zustand for UI state, TanStack Query patterns for server data, Axios for HTTP

Add `security_mobile` Odoo module with HTTP controllers returning `{ success, data | error }` envelope.

## Consequences

### Positive

- Single source of truth for attendance metrics, overtime rules, and KPI calculations
- Mobile releases can decouple from module upgrades if API stays stable
- Expo enables rapid UAT on physical devices via Expo Go

### Negative

- Requires network connectivity for all operations (no offline queue yet)
- API/controller bugs block mobile entirely — e.g. field name mismatches (`batch_id` vs `attendance_batch_id`)
- Two codebases to test (Python controllers + TypeScript UI)

### Neutral

- Dark theme via React Native Paper; not coupled to Odoo web styling
- EAS/production build pipeline documented in DEPLOYMENT.md separately from Odoo deploy
