import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "../lib/tauri";

/** Mirrors src-tauri/src/state.rs `ViewMode`. */
export type ViewMode = "odoo" | "app" | "guide_dock";

interface ViewModeValue {
  mode: ViewMode;
  setMode: (mode: ViewMode) => void;
  /** Navigate the Odoo webview to a same-origin path and show it. */
  openInOdoo: (path?: string) => Promise<void>;
  /** Load the path in Odoo (a full page load, which wakes the guidance runner)
   * with the DeployGuard guide panel beside it. */
  openGuide: (path?: string) => Promise<void>;
}

const ViewModeContext = createContext<ViewModeValue | null>(null);

/**
 * The single owner of the window layout on the React side.
 *
 * Rust is the source of truth: every change, whoever requested it (this
 * provider, an auto-reveal on sign-in, a session expiry), arrives as a
 * `deployguard://view-mode` event. Components never call `invoke("set_view_mode")`
 * themselves, which is how React and the native bounds used to drift apart.
 */
export function ViewModeProvider({ children }: { children: ReactNode }) {
  const [mode, setLocalMode] = useState<ViewMode>("odoo");

  useEffect(() => {
    let cancelled = false;
    invoke<ViewMode>("get_view_mode")
      .then((m) => { if (!cancelled) setLocalMode(m); })
      .catch(() => {});
    const unlisten = listen<ViewMode>("deployguard://view-mode", (e) => {
      if (!cancelled) setLocalMode(e.payload);
    });
    return () => {
      cancelled = true;
      unlisten.then((u) => u()).catch(() => {});
    };
  }, []);

  const setMode = useCallback((next: ViewMode) => {
    // Optimistic, so the UI responds on the same frame; the event confirms it.
    setLocalMode(next);
    void invoke("set_view_mode", { mode: next }).catch(() => {});
  }, []);

  const openInOdoo = useCallback(async (path?: string) => {
    await invoke("navigate_odoo", { path });
    setMode("odoo");
  }, [setMode]);

  const openGuide = useCallback(async (path?: string) => {
    await invoke("navigate_odoo", { path: path || "/odoo" });
    setMode("guide_dock");
  }, [setMode]);

  const value = useMemo(() => ({ mode, setMode, openInOdoo, openGuide }), [mode, setMode, openInOdoo, openGuide]);
  return <ViewModeContext.Provider value={value}>{children}</ViewModeContext.Provider>;
}

export function useViewMode(): ViewModeValue {
  const ctx = useContext(ViewModeContext);
  if (!ctx) throw new Error("useViewMode() must be used within <ViewModeProvider>");
  return ctx;
}
