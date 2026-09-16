import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "../lib/tauri";
import { useSession } from "../session/SessionContext";
import { StatusBar } from "./StatusBar";
import { OdooIcon, HelpIcon, BackIcon, ForwardIcon, ReloadIcon, ChevronDownIcon } from "./icons";
import type { SessionEvent } from "../session/types";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/**
 * The DeployGuard chrome around Odoo, revised 2026-09-16 to a persistent
 * toolbar + mega menu (see DEVIATIONS.md D-2/D-3), replacing the earlier
 * hover-corner-handle design:
 *
 *  - Always visible, docked to the top of the window (the native "shell"
 *    webview is exactly this toolbar strip — see windowing.rs).
 *  - Real Odoo navigation controls (back/forward/reload) drive Odoo's own
 *    browser history via a one-off `history.back()`-style eval, not a
 *    persistent bridge.
 *  - Clicking the DeployGuard brand opens a mega menu that drops down
 *    below the toolbar, overlaying the top of Odoo rather than resizing
 *    it. Click again, Escape, or a click outside closes it.
 *
 * There is no separate "Home" route — the mega menu IS Home. There is no
 * DeployGuard-branded login screen: Odoo's own login page is what's
 * visible underneath when signed out.
 */
export function Toolbar() {
  const { status, session, signOut } = useSession();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement | null>(null);
  const brandButtonRef = useRef<HTMLButtonElement | null>(null);

  const openMenu = useCallback(() => {
    setMenuOpen(true);
    void invoke("menu_open");
  }, []);

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    void invoke("menu_close");
  }, []);

  const toggleMenu = useCallback(() => {
    if (menuOpen) closeMenu();
    else openMenu();
  }, [menuOpen, openMenu, closeMenu]);

  // Resync with the *actual* native webview size on mount — Rust is the
  // source of truth (see get_menu_open's doc comment on the Rust side for
  // why this matters, e.g. after a dev-server HMR reload).
  useEffect(() => {
    let cancelled = false;
    invoke<boolean>("get_menu_open")
      .then((isOpen) => {
        if (!cancelled && isOpen) setMenuOpen(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Rust auto-opens the menu the first time a session is detected.
  useEffect(() => {
    const unlistenPromise = listen<SessionEvent>("deployguard://session-changed", (event) => {
      if (event.payload.status === "signed_in" && event.payload.auto_reveal) {
        setMenuOpen(true);
      }
    });
    return () => {
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {});
    };
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && menuOpen) {
        closeMenu();
        // Keyboard-initiated close returns focus to the control that
        // opened it (docs/deployguard/05-ux-principles.md §9) — unlike
        // the outside-click case below, where focus should follow the
        // user's click, not jump back to the brand button.
        brandButtonRef.current?.focus();
      }
    }
    function onPointerDown(e: MouseEvent) {
      if (menuOpen && menuRef.current && !menuRef.current.contains(e.target as Node)) {
        closeMenu();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("mousedown", onPointerDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("mousedown", onPointerDown);
    };
  }, [menuOpen, closeMenu]);

  const goHome = useCallback(() => {
    void invoke("navigate_odoo", { path: "/odoo" });
    closeMenu();
  }, [closeMenu]);

  const goBack = useCallback(() => void invoke("odoo_back"), []);
  const goForward = useCallback(() => void invoke("odoo_forward"), []);
  const reload = useCallback(() => void invoke("odoo_reload"), []);

  return (
    <div className="dg-shell" ref={menuRef}>
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
          <button type="button" className="dg-toolbar__btn" aria-label="Go to DeployGuard System home" title="Home" onClick={goHome}>
            <OdooIcon size={16} />
          </button>
        </div>

        <button
          ref={brandButtonRef}
          type="button"
          className="dg-toolbar__brand"
          aria-expanded={menuOpen}
          aria-label={menuOpen ? "Close DeployGuard menu" : "Open DeployGuard menu"}
          onClick={toggleMenu}
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

      {menuOpen && (
        <div className="dg-megamenu">
          <StatusBar />

          {status === "checking" && <p className="dg-empty">Checking your session…</p>}

          {status === "signed_out" && (
            <div className="dg-card">
              <p style={{ fontSize: 13, color: "var(--ds-text-2)", margin: 0 }}>
                Sign in on the DeployGuard System page below to get started
                — nothing extra to remember, it's your existing DogForce
                Odoo login.
              </p>
            </div>
          )}

          {status === "signed_in" && session && (
            <>
              <h1 style={{ fontSize: 18, fontWeight: 700, margin: "0 0 18px", color: "var(--ds-text)" }}>
                {greeting()}, {session.name.split(" ")[0]}
              </h1>

              <div className="dg-megamenu__grid">
                <button type="button" className="dg-tile" onClick={goHome}>
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

              <div className="dg-megamenu__footer">
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
      )}
    </div>
  );
}
