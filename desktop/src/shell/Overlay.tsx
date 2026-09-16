import { useCallback, useEffect, useRef, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "../lib/tauri";
import { useSession } from "../session/SessionContext";
import { StatusBar } from "./StatusBar";
import { OdooIcon, HelpIcon } from "./icons";
import type { SessionEvent } from "../session/types";

const COLLAPSE_DELAY_MS = 280;

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/**
 * The entire DeployGuard UI lives in one always-present overlay:
 *  - Collapsed: a small corner handle (see src-tauri/src/windowing.rs —
 *    the native "shell" webview is literally sized to just this handle,
 *    so Odoo underneath is fully visible and interactive everywhere else).
 *  - Expanded: hover or click the handle (or focus it with Tab + Enter)
 *    to reveal the full panel. Escape, a deliberate mouseleave delay, or
 *    clicking "Go to Odoo" collapses it again.
 *
 * There is no separate "Home" route — this panel IS Home. There is no
 * login screen here either: Odoo's own login page is what's visible
 * underneath when signed out (see DEVIATIONS.md D-1/D-2).
 */
export function Overlay() {
  const { status, session, signOut } = useSession();
  const [expanded, setExpanded] = useState(false);
  const collapseTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const expand = useCallback(() => {
    if (collapseTimer.current) {
      clearTimeout(collapseTimer.current);
      collapseTimer.current = null;
    }
    setExpanded(true);
    void invoke("overlay_expand");
  }, []);

  const collapse = useCallback(() => {
    setExpanded(false);
    void invoke("overlay_collapse");
  }, []);

  const scheduleCollapse = useCallback(() => {
    if (collapseTimer.current) clearTimeout(collapseTimer.current);
    collapseTimer.current = setTimeout(collapse, COLLAPSE_DELAY_MS);
  }, [collapse]);

  const cancelScheduledCollapse = useCallback(() => {
    if (collapseTimer.current) {
      clearTimeout(collapseTimer.current);
      collapseTimer.current = null;
    }
  }, []);

  // Resync with the *actual* native webview size on mount. Rust is the
  // source of truth for whether the overlay is expanded — this component's
  // own `expanded` boolean is a local mirror that can otherwise drift out
  // of sync (a dev-server HMR reload resets React state but not the
  // already-resized native webview; see vite.config.ts's optimizeDeps
  // comment for why that reload happened in the first place).
  useEffect(() => {
    let cancelled = false;
    invoke<boolean>("get_overlay_expanded")
      .then((isExpanded) => {
        if (!cancelled && isExpanded) setExpanded(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  // Rust auto-expands the *native* webview the first time a session is
  // detected (see windowing.rs's `auto_reveal`), but that alone doesn't
  // update this component's local `expanded` boolean — without this
  // listener, React would keep rendering the small collapsed handle over
  // top of a native webview Rust already resized to the full panel width.
  useEffect(() => {
    const unlistenPromise = listen<SessionEvent>("deployguard://session-changed", (event) => {
      if (event.payload.status === "signed_in" && event.payload.auto_reveal) {
        cancelScheduledCollapse();
        setExpanded(true);
      }
    });
    return () => {
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {});
    };
  }, [cancelScheduledCollapse]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && expanded) collapse();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [expanded, collapse]);

  const goToOdoo = useCallback((path?: string) => {
    void invoke("navigate_odoo", { path });
    collapse();
  }, [collapse]);

  if (!expanded) {
    return (
      <button
        type="button"
        className="dg-handle"
        aria-label="Open DeployGuard Platform"
        title="Open DeployGuard Platform"
        onMouseEnter={expand}
        onFocus={expand}
        onClick={expand}
      >
        <span className="dg-handle__mark" aria-hidden="true">DG</span>
      </button>
    );
  }

  return (
    <div
      className="dg-panel"
      onMouseLeave={scheduleCollapse}
      onMouseEnter={cancelScheduledCollapse}
    >
      <div className="dg-panel__header">
        <div className="dg-rail__brand" aria-hidden="true" style={{ margin: 0 }}>DG</div>
        <div>
          <div className="dg-panel__title">DeployGuard Platform</div>
          {status === "signed_in" && session ? (
            <div className="dg-panel__subtitle">{session.name}</div>
          ) : (
            <div className="dg-panel__subtitle">Your DogForce workspace</div>
          )}
        </div>
        <button type="button" className="dg-panel__close" aria-label="Collapse" title="Collapse (Esc)" onClick={collapse}>
          ×
        </button>
      </div>

      <div className="dg-panel__body">
        <StatusBar />

        {status === "checking" && (
          <p className="dg-empty">Checking your session…</p>
        )}

        {status === "signed_out" && (
          <div className="dg-card" style={{ marginBottom: 16 }}>
            <p style={{ fontSize: 13, color: "var(--ds-text-2)", margin: 0 }}>
              Sign in below to get started. DeployGuard uses your DogForce
              Odoo login — nothing extra to remember.
            </p>
          </div>
        )}

        {status === "signed_in" && session && (
          <>
            <h1 style={{ fontSize: 18, fontWeight: 700, margin: "4px 0 18px", color: "var(--ds-text)" }}>
              {greeting()}, {session.name.split(" ")[0]}
            </h1>

            <button type="button" className="dg-tile" style={{ marginBottom: 12 }} onClick={() => goToOdoo()}>
              <span className="dg-tile__icon"><OdooIcon /></span>
              <span>
                <span className="dg-tile__title">Open DeployGuard System</span>
                <span className="dg-tile__subline">Rosters, attendance, incidents, reports</span>
              </span>
            </button>

            <div className="dg-card" style={{ marginBottom: 12 }}>
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
          </>
        )}
      </div>

      <div className="dg-panel__footer">
        {status === "signed_in" && (
          <button type="button" className="dg-btn dg-btn--secondary" style={{ width: "100%" }} onClick={() => void signOut()}>
            Sign out
          </button>
        )}
        <span style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11.5, color: "var(--ds-text-subtle)", marginTop: 10 }}>
          <HelpIcon /> Something not working? Ask your operations manager for now.
        </span>
      </div>
    </div>
  );
}
