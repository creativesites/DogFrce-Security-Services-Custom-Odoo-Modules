# Agent findings — CI/test hardening pass (2026-09-16)

Findings from a background verification pass. Everything below was found
while doing static CI review, writing Rust/frontend unit tests, and a WCAG
contrast audit. Per the task boundary, `Overlay.tsx`, `StatusBar.tsx`,
`src/session/**`, `src-tauri/src/windowing.rs`, and `src/styles/shell.css`
were **not modified** — findings that would require touching those files
are documented here instead, for the main session (which owns those files)
to act on.

---

## 1. Accessibility — WCAG 2.2 AA contrast audit

Computed with the standard WCAG relative-luminance formula (sRGB →
linearized → `0.2126R + 0.7152G + 0.0722B`, contrast ratio =
`(L1+0.05)/(L2+0.05)`), against the real hex values in
`src/styles/ds.css` and `src/styles/dgs.css`, checked against
`docs/deployguard/05-ux-principles.md` §9 (`≥ 4.5:1` text, `≥ 3:1` UI
components/focus rings). Script and raw output available on request; key
results:

### 1.1 FAIL — Focus ring is nearly invisible (most serious finding)

`--ds-accent-mid` (`#C7D9F4`) is used as the `outline` color on every
`:focus-visible` state in `shell.css`: `.dg-handle`, `.dg-panel__close`,
`.dg-tile`, `.dg-btn` (lines 53, 109, 188, 244).

- Against white / `--dgs-panel` (`#FFFFFF`): **1.43:1**
- Against `--dgs-canvas` (`#F5F6F9`): **1.33:1**

Both are far below the **3:1** WCAG 2.2 SC 1.4.11 (non-text contrast)
threshold the project's own doc calls out for "focus rings" explicitly.
Given principle #11 ("Keyboard first for power users") and the
accessibility checklist's own "every interactive element reachable and
**operable by keyboard, with visible focus**" requirement, this is a real
gap: a keyboard user tabbing through the handle, close button, "Open
DeployGuard System" tile, or sign-out button gets a focus ring that's
barely perceptible against the panel's light backgrounds.

**Suggested fix:** swap the focus-ring color to a token that clears 3:1
against white, e.g. `--ds-accent` (`#1B3A6B`, which is 8.53:1 against
white — comfortably over both the 3:1 UI-component threshold and even the
4.5:1 text threshold) or `--ds-info` (`#1D5FA4`, 5.17:1). This is a
one-token swap in `shell.css` (4 `outline:` declarations) — no new hex
values needed, stays within the "no new hex values without a recorded
design decision" rule in `docs/deployguard/05-ux-principles.md` §2.

### 1.2 FAIL — "Coming soon" chip text, once its `opacity: .6` is accounted for

`.dg-chip` (`shell.css` line ~212) sets `color: var(--ds-text-subtle)`
(`#64748B`) on `background: var(--ds-slate)` (`#F1F4F8`), **and** the
whole element has `opacity: .6`. Evaluated as flat token colors alone,
text-on-background is 4.31:1 (already just under 4.5:1) — but `opacity`
composites the *entire rendered chip* (text + its own background rect)
against whatever sits behind it. In every actual usage in `Overlay.tsx`
the chip sits inside a `.dg-card` (background `#FFFFFF`), so the real
rendered pixels are:

- Effective chip background ≈ blend(`#F1F4F8`, white, 0.6) = `#F7F8FB`
- Effective chip text ≈ blend(`#64748B`, white, 0.6) = `#A2ACB9`
- **Real contrast ≈ 2.16:1** — well under the 4.5:1 text threshold.

This is on the "My work" and "Training" cards' "Coming soon" labels — low
severity in impact (short, non-critical label) but a clear numeric
failure, and ADR-flagged as a hard rule area (design system §2, chip
pattern spec in 05-ux-principles.md §5).

**Suggested fix:** drop the `opacity: .6` (the mono/uppercase/letter-spaced
styling already visually de-emphasizes it enough) or compensate by
darkening the text token used specifically here — the `Chip` spec in
05-ux-principles.md §5 already documents "60% label opacity" as the
intended pattern, so this is worth flagging as a spec-level tension, not
just an implementation bug: the spec's own 60%-opacity chip recipe doesn't
clear AA once you do the compositing math. Recommend raising this back to
the design-system source (`security_shell`) rather than diverging only in
the desktop port.

### 1.3 Borderline FAIL — loading-state text directly on `--dgs-canvas`

The "Checking your session…" text (`Overlay.tsx`, the `status ===
"checking"` branch) renders as `<p className="dg-empty">` directly inside
`.dg-panel__body`, whose background is `--dgs-canvas` (`#F5F6F9`) — not
wrapped in a white `.dg-card` like the other `.dg-empty` usages are.
`--ds-text-subtle` (`#64748B`) on `#F5F6F9` is **4.40:1**, just under the
4.5:1 threshold. Every *other* `.dg-empty` usage in the current markup
happens to sit inside a white `.dg-card`, where the same pair is 4.76:1
(passes) — so this is specifically the transient sign-in-check state that
fails, easy to miss in manual QA since it's on screen only briefly.

**Suggested fix:** wrap the checking-state message in a `.dg-card` like
the other empty states, or use `--ds-text-muted` (`#475569`, 7.58:1 on
`--dgs-canvas`, comfortably passes) for text that sits directly on the
canvas background.

### 1.4 Sub-3:1 decorative border (low severity, flagging for completeness)

`.dg-handle`'s `border: 1px solid var(--ds-border)` (`#E2E8F0` on white)
is 1.23:1. This is *not* the primary way the handle's boundary reads (it
also has `box-shadow: var(--dgs-lift)`, a visible drop shadow, and a
44×44px distinct region), so I'm not flagging this as a hard failure —
just noting it in case a future high-contrast-mode pass wants to
strengthen it.

### 1.5 Passing pairs (for completeness — nothing to fix)

| Pair | Ratio |
|---|---|
| `--ds-text` on white/panel | 18.92:1 |
| `--ds-text-2` on white | 10.31:1 |
| `--ds-text-muted` on white | 7.58:1 |
| `--ds-text-subtle` on white | 4.76:1 (passes, barely) |
| white on `--ds-accent` (handle mark, brand square, primary button) | 11.27:1 |
| `--ds-accent` on `--ds-accent-light` (tile icon) | 9.93:1 |
| Status dots (success/warning/danger/info) on the statusbar's white background | 5.37 / 7.09 / 8.31 / 6.51 :1 |

Status dots are also never the *sole* indicator of state — `StatusBar.tsx`
always renders the dot with `aria-hidden="true"` next to a text label
(`LABEL[state]`), which correctly satisfies "status never conveyed by
colour alone."

### 1.6 Non-contrast checklist items (docs/deployguard/05-ux-principles.md §9)

Reviewed against the rest of the checklist, read-only (`Overlay.tsx`,
`SessionContext.tsx`):

- **Keyboard reachability:** all interactive elements are real `<button>`
  elements (handle, close, "Open DeployGuard System" tile, sign-out) —
  correctly tab-reachable, no `div`-as-button anti-pattern. Good.
- **`aria-label`/`title` on icon-only controls:** the handle and close
  button both have both. Good.
- **Esc closes overlay, but focus does NOT return to the trigger.**
  `Overlay.tsx`'s `Escape` handler (around line 97-103) calls `collapse()`
  directly; nothing calls `.focus()` back on the `.dg-handle` button
  afterward. Per the checklist's explicit "Esc closes any overlay, **focus
  returns to the trigger**" requirement, this is a real gap — a keyboard
  user who tabs into the expanded panel and presses Escape loses their
  focus position (it likely falls back to `<body>`). Since this is inside
  the boundary file, I'm not fixing it, but the fix would be: keep a
  `handleRef` on the collapsed-state button, and call
  `handleRef.current?.focus()` at the end of `collapse()`.
- **Reduced motion:** already handled — `shell.css`'s
  `@media (prefers-reduced-motion: reduce)` block correctly zeroes
  transition duration for `.dg-tile`, `.dg-card`, `.dg-btn`, `.dg-handle`.
- **Text scaling to 200%:** `shell.css` uses fixed `px` font sizes
  throughout rather than `rem`/`em`. This *may* still scale correctly
  under OS-level display zoom (which the Tauri webview should respect via
  the OS's DPI/zoom, not CSS root font-size), but I could not verify this
  at runtime (no Windows/macOS accessibility zoom testing available in
  this environment) — flagging as **unverified**, not a confirmed defect.
- **1024px minimum window width layout:** the 340px expanded panel leaves
  684px for Odoo at the documented minimum — no obvious breakage from
  reading the CSS, but this is also not something I could visually verify
  without running the app.

---

## 2. CI workflow (`.github/workflows/desktop-build.yml`) — static verification

Checked against `desktop/package.json`'s actual scripts, `tauri.conf.json`,
`Cargo.toml`, and `tauri-apps/tauri-action`'s real `action.yml` (fetched
live, not from memory). **No concrete bugs found**; specifics:

- Script names used (`npm run typecheck`, `npm run lint`) both exist
  verbatim in `package.json`. `tauri:dev` (mentioned in `desktop/README.md`
  as the required dev entrypoint) is **not** called by CI — CI calls
  `tauri-apps/tauri-action@v0` directly with `projectPath: desktop`, which
  invokes Tauri's own build pipeline (`beforeBuildCommand: "npm run
  build"` in `tauri.conf.json`), not `tauri:dev` — correct, since `dev`
  scripts are irrelevant to a build workflow.
- `tauri-apps/tauri-action@v0`'s actual inputs (fetched from its
  `action.yml`) confirm `projectPath` and `args` are valid, and that
  **omitting `tagName`/`releaseId`/`releaseName` is the documented way to
  build without creating/uploading to a GitHub Release** — which is
  exactly what this workflow does (it uploads via
  `actions/upload-artifact@v4` separately instead). This is correct as
  written.
- The `env.TARGET_ENV: ${{ inputs.environment || 'production' }}`
  expression: GitHub's own docs confirm dereferencing a context property
  that doesn't apply to the current trigger (e.g. `inputs.*` on a `push`
  event, since `inputs` is only populated for `workflow_dispatch`/
  `workflow_call`) evaluates to an empty string rather than erroring, so
  the `||` fallback to `'production'` correctly applies on `push`/
  `pull_request` runs. Verified against GitHub Actions' documented
  expression-evaluation behavior, not assumed.
- `Cargo.toml` dependencies are all cross-platform (`reqwest` uses
  `rustls-tls`, avoiding the OpenSSL system-dependency problems that trip
  up Windows builds; no `objc`/`cocoa`/other macOS-only crates are
  depended on directly — those only appear transitively for the macOS
  build target, which is expected and inert on Windows). No Unix-only
  path/permission assumptions found in `src-tauri/src/*.rs`.
- `bundle.icon` in `tauri.conf.json` references 5 icon files; all 5 exist
  in `src-tauri/icons/` (`32x32.png`, `128x128.png`, `128x128@2x.png`,
  `icon.icns`, `icon.ico`) — a missing icon file is a common
  works-on-my-machine CI failure, ruled out.
- `capabilities/main.json` correctly scopes IPC to `"webviews": ["shell"]`
  with `"windows": []`, matching what `DEVIATIONS.md` D-2 and
  `windowing.rs`'s doc comment both claim — consistent, no drift.

**Not verified (could not, without a real Windows runner or Actions
run):** actual successful compilation of `tao`/`wry`/`muda` and other
native-UI crates against the MSVC toolchain, actual NSIS/MSI bundle
generation, and WebView2 runtime behavior.

I pushed branch `agent/desktop-ci-test-hardening` and opened
[PR #1](https://github.com/creativesites/DogFrce-Security-Services-Custom-Odoo-Modules/pull/1)
specifically to make `desktop-build.yml` actually run on a real
`windows-latest` runner (it had literally never executed before this —
`workflow_dispatch` isn't usable until the workflow file exists on
`main`, which it doesn't yet on this remote, so `pull_request` was the
only way to fire it). **The run failed in ~3 seconds with: "The job was
not started because your account is locked due to a billing issue."** —
this is not a code or config problem. I confirmed it's account-wide and
pre-existing by checking runs on `main` going back to 2026-09-02, which
fail with the identical billing-lockout annotation regardless of what
they build. **Action needed from a human with billing access to the
`creativesites` GitHub account/org** before this workflow (or any
workflow in this repo) can actually execute and give a real pass/fail
signal. Everything else in this section remains static-verification-only
until that's resolved.

---

## 3. Bug found and fixed while writing frontend tests

`src/lib/extractErrorMessage.ts` (not a boundary file) had a real logic
gap: `err instanceof Error && err.message` is `false` for an `Error` with
an **empty** message (empty string is falsy in JS), so it fell through to
the generic object-shape branch below, which still matched (a real `Error`
has a `message` string property) and returned that same empty string —
meaning a blank/empty `Error` message rendered as **blank UI text**
instead of the intended "Something went wrong. Try again." fallback.
Fixed to check `.trim().length > 0` explicitly within the `Error` branch
(and the object-shape branch, for the same class of bug with a
whitespace-only serialized message). Regression tests added in
`src/lib/extractErrorMessage.test.ts` naming the defect, per
`docs/deployguard/25-testing-strategy.md` §5 ("every bug fix adds a
regression test naming the defect").

---

## 4. What's left undone

- The Windows CI run's actual pass/fail result (see §2) — build was
  triggered via `gh`, but Tauri's native build (`tao`, `wry`, `muda`, NSIS
  packaging) takes several minutes on a cold `windows-latest` runner and
  may not have finished within this pass. Check the Actions tab / the run
  URL in the handback message.
- The four accessibility findings in §1 (focus-ring contrast, chip
  opacity, loading-state text, handle border) are documented here but
  **not fixed**, since fixing them means editing `shell.css` and/or
  `Overlay.tsx`, both boundary files the main session owns while live
  testing.
- Runtime verification of 200% text scaling and the 1024px-width layout
  (§1.6) — no way to visually run the app in this environment.
