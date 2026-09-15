# DG-ADR-016 — Web Application Framework

- **Status:** Proposed
- **Date:** 2026-09-15
- **Related:** [18-web-architecture](../18-web-architecture.md), [DG-ADR-001](DG-ADR-001-desktop-framework.md), [DG-ADR-005](DG-ADR-005-monorepo.md), [DG-ADR-017](DG-ADR-017-design-system-and-shell-parity.md)

## Context

The brief proposed Next.js. The Platform UI is:

- an **authenticated** application (no public SEO pages);
- rendered inside **Tauri** on the desktop (static assets served by the Tauri asset protocol, no Node server);
- also served on the web for owners and admins.

We want one application codebase for both surfaces. Real-time inbox updates come from the Platform API (SSE); data fetching needs caching, offline-aware reads (desktop) and optimistic updates for checklists.

## Decision

A **client-rendered single-page application** built with **Vite**, shared between desktop and web:

| Concern | Choice |
|---|---|
| UI | React 19 + TypeScript (strict) |
| Build | Vite |
| Routing | TanStack Router (type-safe routes, search-param validation with Zod) |
| Server state | TanStack Query (cache, retries, offline persistence adapter on desktop) |
| Client/UI state | Zustand (shell state, drafts) |
| Forms | React Hook Form + Zod resolvers from `packages/contracts` |
| Styling | Tailwind CSS with the token-only preset + CSS custom properties from `packages/ui` ([DG-ADR-017](DG-ADR-017-design-system-and-shell-parity.md)) |
| Accessible primitives | Headless primitives (e.g. Radix UI) styled with DeployGuard tokens |
| i18n | ICU message format library (e.g. FormatJS), strings externalised from P0 |
| Tests | Vitest + Testing Library; Playwright for E2E and visual parity |

**Surface differences** are isolated in `packages/app/src/platform/{web,tauri}.ts`: secure storage, notifications, deep links, open Odoo window, offline cache, updater hooks.

**Web hosting:** static assets on a CDN at `app.<domain>`. The API lives at `api.<domain>` with strict CORS, or the same origin under `/api` via the edge proxy (decided in [DG-ADR-013](DG-ADR-013-deployment.md)).

**Next.js is reserved** for the public marketing and licensing website, a separate project outside this scope.

## Alternatives

| Option | Why not |
|---|---|
| **Next.js (App Router)** | SSR and React Server Components need a Node runtime that Tauri doesn't provide. Static export disables core features and complicates dynamic routing. SEO benefits are irrelevant behind authentication. It adds server-rendering concerns (auth cookies, caching) to a product whose API is already separate. |
| React Router v7 framework mode / Remix | Same server-rendering mismatch with Tauri; its SPA mode is viable, but TanStack Router gives stronger type-safe search params for dense management filters. |
| Vue / Svelte / Angular | Lose React reuse with the Expo app skills and ecosystem; no team advantage. |
| Two separate apps (desktop UI vs web UI) | Duplicate screens and divergence; contradicts the one-product principle. |

## Tradeoffs

| We gain | We accept |
|---|---|
| Identical app in Tauri and browser; simple static hosting | No SSR (irrelevant for an authenticated app); initial bundle must be managed (route-level code splitting) |
| Strong typing from route params to API contracts | Choosing TanStack Router over the more common React Router (smaller hiring pool familiarity) |

## Consequences

- **Performance budgets** enforced in CI: initial JS ≤ 250 KB gzip for the shell plus Home route. Heavy management routes (analytics) are lazy.
- **Security:** no `dangerouslySetInnerHTML` except the sanitised rich-text renderer (DOMPurify) for lessons and knowledge articles ([16](../16-security-architecture.md)).
- **Offline:** the desktop build enables TanStack Query persistence to the Tauri SQLite adapter; the web build uses memory only (no sensitive data at rest in the browser).
