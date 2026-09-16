import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "../lib/tauri";
import { useSession } from "../session/SessionContext";
import { StatusBar } from "./StatusBar";
import { OdooIcon, HelpIcon, BackIcon, ForwardIcon, ReloadIcon, ChevronDownIcon, HomeIcon } from "./icons";
import type { SessionEvent } from "../session/types";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/** The app's own pages, reachable from the left nav once the app view is
 * open. Only "home" exists today; this list is deliberately structured so
 * adding a real page later is "add an entry + a case in the switch", not
 * a redesign. */
type AppPage = "home";
const NAV_ITEMS: { key: AppPage; label: string; icon: () => JSX.Element; available: true }[] = [
  { key: "home", label: "Home", icon: () => <HomeIcon size={18} />, available: true },
];
const COMING_SOON_ITEMS = ["My Work", "Training", "Adoption"];

/**
 * The DeployGuard chrome around Odoo, revised 2026-09-16 (three times):
 * hover-corner-handle → toolbar + dropdown mega menu → **toolbar + full
 * app view** (see DEVIATIONS.md D-2/D-3). The DeployGuard side is a real,
 * growing application — a Home today, more pages later (My Work,
 * Training, Adoption, …) — so it gets real screen space when open, with
 * its own left navigation, rather than a glance-only dropdown.
 *
 *  - Toolbar: always visible, docked to the top (native "shell" webview
 *    bounds are exactly this strip — see windowing.rs). Real Odoo
 *    navigation controls (back/forward/reload) drive Odoo's own browser
 *    history via a one-off `history.back()`-style eval, not a bridge.
 *  - App view: clicking the DeployGuard brand switches the "shell"
 *    webview to cover the *entire* window (Odoo is still running
 *    underneath, just fully covered — not resized or reloaded). Clicking
 *    the brand again, Escape, or clicking a link into Odoo switches back.
 *
 * There is no DeployGuard-branded login screen: Odoo's own login page is
 * what's visible underneath when signed out.
 */
export function Toolbar() {
  const { status, session, signOut } = useSession();
  const [appViewOpen, setAppViewOpen] = useState(false);
  const [page, setPage] = useState<AppPage>("home");
  const brandButtonRef = useRef<HTMLButtonElement | null>(null);

  const openAppView = useCallback(() => {
    setAppViewOpen(true);
    void invoke("app_view_open");
  }, []);

  const closeAppView = useCallback(() => {
    setAppViewOpen(false);
    void invoke("app_view_close");
  }, []);

  const toggleAppView = useCallback(() => {
    if (appViewOpen) closeAppView();
    else openAppView();
  }, [appViewOpen, openAppView, closeAppView]);

  // Resync with the *actual* native webview size on mount — Rust is the
  // source of truth (see get_app_view_open's doc comment on the Rust
  // side for why this matters, e.g. after a dev-server HMR reload).
  useEffect(() => {
    let cancelled = false;
    invoke<boolean>("get_app_view_open")
      .then((isOpen) => {
        if (!cancelled && isOpen) setAppViewOpen(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Rust auto-opens the app view the first time a session is detected.
  useEffect(() => {
    const unlistenPromise = listen<SessionEvent>("deployguard://session-changed", (event) => {
      if (event.payload.status === "signed_in" && event.payload.auto_reveal) {
        setAppViewOpen(true);
      }
    });
    return () => {
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {});
    };
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && appViewOpen) {
        closeAppView();
        // Keyboard-initiated close returns focus to the control that
        // opened it (docs/deployguard/05-ux-principles.md §9).
        brandButtonRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [appViewOpen, closeAppView]);

  const goToOdoo = useCallback((path?: string) => {
    void invoke("navigate_odoo", { path });
    closeAppView();
  }, [closeAppView]);

  const goBack = useCallback(() => void invoke("odoo_back"), []);
  const goForward = useCallback(() => void invoke("odoo_forward"), []);
  const reload = useCallback(() => void invoke("odoo_reload"), []);

  return (
    <div className="dg-shell">
      <div className="dg-toolbar">
        <div className="dg-toolbar__nav">
          <button type="button" className="dg-toolbar__btn" aria-label="Back" title="Back" onClick={goBack}>
            <BackIcon size={17} />
          </button>
          <button type="button" className="dg-toolbar__btn" aria-label="Forward" title="Forward" onClick={goForward}>
            <ForwardIcon size={17} />
          </button>
          <button type="button" className="dg-toolbar__btn" aria-label="Reload" title="Reload" onClick={reload}>
            <ReloadIcon size={16} />
          </button>
          <button type="button" className="dg-toolbar__btn" aria-label="Go to DeployGuard System home" title="DeployGuard System home" onClick={() => goToOdoo()}>
            <OdooIcon size={16} />
          </button>
        </div>

        <button
          ref={brandButtonRef}
          type="button"
          className="dg-toolbar__brand"
          aria-expanded={appViewOpen}
          aria-label={appViewOpen ? "Close DeployGuard" : "Open DeployGuard"}
          onClick={toggleAppView}
        >
          <span className="dg-toolbar__brand-mark" aria-hidden="true">DG</span>
          <span className="dg-toolbar__brand-label">DeployGuard</span>
          <ChevronDownIcon size={14} />
        </button>

        <div className="dg-toolbar__spacer" />

        <div className="dg-toolbar__status">
          <StatusBar compact />
        </div>

        {status === "signed_in" && session ? (
          <div className="dg-toolbar__profile" title={session.name}>
            <span className="dg-toolbar__profile-name">{session.name}</span>
          </div>
        ) : (
          <span className="dg-toolbar__signedout">Not signed in</span>
        )}
      </div>

      {appViewOpen && (
        <div className="dg-appview">
          <nav className="dg-appview__nav" aria-label="DeployGuard sections">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.key}
                type="button"
                className="dg-appview__navitem"
                aria-current={page === item.key ? "page" : undefined}
                onClick={() => setPage(item.key)}
              >
                {item.icon()}
                <span>{item.label}</span>
              </button>
            ))}
            {COMING_SOON_ITEMS.map((label) => (
              <div key={label} className="dg-appview__navitem dg-appview__navitem--soon" aria-disabled="true">
                <span className="dg-appview__navitem-dot" aria-hidden="true" />
                <span>{label}</span>
                <span className="dg-chip">Soon</span>
              </div>
            ))}
          </nav>

          <div className="dg-appview__content">
            <StatusBar />

            {status === "checking" && <p className="dg-empty">Checking your session…</p>}

            {status === "signed_out" && (
              <div className="dg-card" style={{ maxWidth: 480 }}>
                <p style={{ fontSize: 13, color: "var(--ds-text-2)", margin: 0 }}>
                  Sign in on the DeployGuard System page to get started —
                  nothing extra to remember, it's your existing DogForce
                  Odoo login.
                </p>
              </div>
            )}

            {status === "signed_in" && session && page === "home" && (
              <>
                <h1 style={{ fontSize: 20, fontWeight: 700, margin: "4px 0 20px", color: "var(--ds-text)" }}>
                  {greeting()}, {session.name.split(" ")[0]}
                </h1>

                <div className="dg-appview__grid">
                  <button type="button" className="dg-tile" onClick={() => goToOdoo()}>
                    <span className="dg-tile__icon"><OdooIcon /></span>
                    <span>
                      <span className="dg-tile__title">DeployGuard System</span>
                      <span className="dg-tile__subline">Rosters, attendance, incidents, reports</span>
                    </span>
                  </button>

                  <div className="dg-card">
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-text)" }}>My work</span>
                      <span className="dg-chip">Coming soon</span>
                    </div>
                    <p className="dg-empty" style={{ padding: "8px 0", textAlign: "left" }}>
                      Tasks and checklists will appear here once work management is enabled.
                    </p>
                  </div>

                  <div className="dg-card">
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: "var(--ds-text)" }}>Training</span>
                      <span className="dg-chip">Coming soon</span>
                    </div>
                    <p className="dg-empty" style={{ padding: "8px 0", textAlign: "left" }}>
                      No training assigned yet.
                    </p>
                  </div>
                </div>

                <div className="dg-appview__footer">
                  <button type="button" className="dg-btn dg-btn--secondary" onClick={() => void signOut()}>
                    Sign out
                  </button>
                  <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--ds-text-subtle)" }}>
                    <HelpIcon size={16} /> Something not working? Ask your operations manager for now.
                  </span>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
