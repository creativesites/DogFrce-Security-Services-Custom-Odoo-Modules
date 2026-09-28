import { useCallback, useEffect, useState, type ReactNode } from "react";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { invoke } from "../lib/tauri";
import { getCachedAvatar, setCachedAvatar } from "../lib/avatarCache";
import { useSession } from "../session/SessionContext";
import { StatusBar } from "./StatusBar";
import { UpdateNotice } from "./UpdateNotice";
import {
  OdooIcon, HelpIcon, BackIcon, ForwardIcon, ReloadIcon, ChevronDownIcon,
  WindowMinimizeIcon, WindowMaximizeIcon, WindowRestoreIcon, WindowCloseIcon,
} from "./icons";
import dogforceLogo from "../assets/dogforce-logo-256.png";
import "./toolbar.css";

function initialsOf(name: string): string {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

/** Small icon button with a CSS tooltip. */
export function IconButton({ label, onClick, children }: { label: string; onClick: () => void; children: ReactNode }) {
  return (
    <button type="button" className="dg-toolbar__btn" aria-label={label} data-tip={label} onClick={onClick}>
      {children}
    </button>
  );
}

/** Window state + controls for the custom (decorations-off) title bar. */
export function useWindowControls() {
  const [isMaximized, setIsMaximized] = useState(false);
  useEffect(() => {
    const win = getCurrentWindow();
    let cancelled = false;
    const refresh = () => win.isMaximized().then((m) => { if (!cancelled) setIsMaximized(m); }).catch(() => {});
    void refresh();
    const unlisten = win.onResized(() => void refresh());
    return () => {
      cancelled = true;
      unlisten.then((u) => u()).catch(() => {});
    };
  }, []);
  return {
    isMaximized,
    minimize: useCallback(() => void invoke("window_minimize"), []),
    toggleMaximize: useCallback(() => void invoke("window_toggle_maximize"), []),
    close: useCallback(() => void invoke("window_close"), []),
  };
}

export function WindowControls() {
  const { isMaximized, minimize, toggleMaximize, close } = useWindowControls();
  return (
    <div className="dg-toolbar__winctl" role="group" aria-label="Window controls">
      <button type="button" className="dg-toolbar__winbtn" aria-label="Minimize" data-tip="Minimize" onClick={minimize}>
        <WindowMinimizeIcon size={14} />
      </button>
      <button
        type="button"
        className="dg-toolbar__winbtn"
        aria-label={isMaximized ? "Restore" : "Maximize"}
        data-tip={isMaximized ? "Restore" : "Maximize"}
        onClick={toggleMaximize}
      >
        {isMaximized ? <WindowRestoreIcon size={13} /> : <WindowMaximizeIcon size={13} />}
      </button>
      <button type="button" className="dg-toolbar__winbtn dg-toolbar__winbtn--close" aria-label="Close" data-tip="Close" onClick={close}>
        <WindowCloseIcon size={14} />
      </button>
    </div>
  );
}

function useAvatar(uid: number | null): string | null {
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  useEffect(() => {
    if (uid == null) {
      setAvatarUrl(null);
      return;
    }
    setAvatarUrl(getCachedAvatar(uid));
    let cancelled = false;
    invoke<string | null>("odoo_fetch_avatar")
      .then((dataUrl) => {
        if (cancelled || !dataUrl) return;
        setCachedAvatar(uid, dataUrl);
        setAvatarUrl(dataUrl);
      })
      // Cosmetic: the cached avatar or the initials are enough.
      .catch(() => {});
    return () => { cancelled = true; };
  }, [uid]);
  return avatarUrl;
}

interface ToolbarProps {
  appOpen: boolean;
  onToggleApp: () => void;
  onOdooHome: () => void;
  onBack: () => void;
  onForward: () => void;
  onReload: () => void;
  onHelp: () => void;
  brandRef?: React.Ref<HTMLButtonElement>;
}

/** The always-visible 48 px strip above Odoo. Presentational: the app shell
 * owns what each button does. */
export function Toolbar({ appOpen, onToggleApp, onOdooHome, onBack, onForward, onReload, onHelp, brandRef }: ToolbarProps) {
  const { status, session } = useSession();
  const avatarUrl = useAvatar(status === "signed_in" ? session?.uid ?? null : null);

  return (
    <div className="dg-toolbar">
      <div className="dg-toolbar__nav" role="group" aria-label="DogForce ERP navigation">
        <IconButton label="Back" onClick={onBack}><BackIcon size={16} /></IconButton>
        <IconButton label="Forward" onClick={onForward}><ForwardIcon size={16} /></IconButton>
        <IconButton label="Reload" onClick={onReload}><ReloadIcon size={15} /></IconButton>
        <span className="dg-toolbar__divider" aria-hidden="true" />
        <IconButton label="DogForce ERP home" onClick={onOdooHome}><OdooIcon size={16} /></IconButton>
        <IconButton label="Help" onClick={onHelp}><HelpIcon size={16} /></IconButton>
      </div>

      <button
        ref={brandRef}
        type="button"
        className={`dg-toolbar__brand${appOpen ? " is-open" : ""}`}
        aria-expanded={appOpen}
        aria-label={appOpen ? "Close DeployGuard" : "Open DeployGuard"}
        onClick={onToggleApp}
      >
        <img className="dg-toolbar__brand-logo" src={dogforceLogo} alt="" aria-hidden="true" />
        <span className="dg-toolbar__brand-label">DogForce</span>
        <ChevronDownIcon size={14} />
      </button>

      {/* Empty space doubles as the window's drag handle. */}
      <div className="dg-toolbar__spacer" data-tauri-drag-region />

      <div className="dg-toolbar__status">
        <StatusBar compact />
      </div>

      <UpdateNotice />

      {status === "signed_in" && session ? (
        <div className="dg-toolbar__profile" title={session.name}>
          {avatarUrl ? (
            <img className="dg-toolbar__avatar" src={avatarUrl} alt="" aria-hidden="true" />
          ) : (
            <span className="dg-toolbar__avatar dg-toolbar__avatar--initials" aria-hidden="true">
              {initialsOf(session.name)}
            </span>
          )}
          <span className="dg-toolbar__profile-name">{session.name}</span>
          <span className="dg-toolbar__presence" aria-label="Signed in" />
        </div>
      ) : (
        <span className="dg-toolbar__signedout">{status === "expired" ? "Session expired" : "Not signed in"}</span>
      )}

      <WindowControls />
    </div>
  );
}
