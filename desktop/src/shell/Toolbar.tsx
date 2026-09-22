import {
  useCallback, useEffect, useMemo, useRef, useState, type ReactNode,
} from "react";
import { listen } from "@tauri-apps/api/event";
import { getCurrentWindow } from "@tauri-apps/api/window";
import { invoke } from "../lib/tauri";
import { getCachedAvatar, setCachedAvatar } from "../lib/avatarCache";
import { useSession } from "../session/SessionContext";
import { StatusBar } from "./StatusBar";
import {
  OdooIcon, HelpIcon, BackIcon, ForwardIcon, ReloadIcon, ChevronDownIcon, HomeIcon,
  WindowMinimizeIcon, WindowMaximizeIcon, WindowRestoreIcon, WindowCloseIcon, ClipboardListIcon, BookIcon,
  ChartBarIcon, LifeBuoyIcon, TrendingUpIcon, InboxIcon,
} from "./icons";
import { MyWork } from "./pages/MyWork";
import { DiagnosticsPanel } from "./DiagnosticsPanel";
import { MyTraining } from "./pages/MyTraining";
import { OwnerOverview } from "./pages/OwnerOverview";
import { AdoptionOverview } from "./pages/AdoptionOverview";
import { ExceptionsInbox } from "./pages/ExceptionsInbox";
import { ProblemReportDialog } from "./ProblemReportDialog";
import { HelpDrawer } from "./HelpDrawer";
import { FirstRunOnboarding } from "./FirstRunOnboarding";
import { UpdateNotice } from "./UpdateNotice";
import {
  type NoticeStatus,
  acknowledgeNotice,
  adoptionAllowed,
  fetchNotice,
  hasSeenWelcome,
  markWelcomeSeen,
  noticeStatusFrom,
  noticeStatusFromError,
  shouldShowOnboarding,
} from "../api/onboarding";
import { getVersion } from "@tauri-apps/api/app";
import { type Capabilities, type Feature, isAvailable, probeCapabilities } from "../api/capabilities";
import type { SessionEvent } from "../session/types";
import dogforceLogo from "../assets/dogforce-logo-256.png";
import "./toolbar.css";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("");
}

/** Deterministic hue so a given name always gets the same avatar gradient. */
function hueOf(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) % 360;
  return h;
}

/** The app's own pages, reachable from the left nav once the app view is
 * open. */
type AppPage = "home" | "work" | "training" | "adoption" | "inbox" | "owner";
const NAV_ITEMS: { key: AppPage; label: string; icon: () => JSX.Element; available: true }[] = [
  { key: "home", label: "Home", icon: () => <HomeIcon size={18} />, available: true },
  { key: "work", label: "My Work & Sweeps", icon: () => <ClipboardListIcon size={18} />, available: true },
  { key: "training", label: "My Training", icon: () => <BookIcon size={18} />, available: true },
  { key: "adoption", label: "Adoption", icon: () => <TrendingUpIcon size={18} />, available: true },
  { key: "inbox", label: "Exceptions Inbox", icon: () => <InboxIcon size={18} />, available: true },
  { key: "owner", label: "Owner Overview", icon: () => <ChartBarIcon size={18} />, available: true },
];
const COMING_SOON_ITEMS: string[] = [];
const HOME_TILES: { key: AppPage; title: string; subline: string; icon: () => JSX.Element }[] = [
  { key: "work", title: "My Work & Sweeps", subline: "Tasks, checklists, and sweep sign-offs", icon: () => <ClipboardListIcon /> },
  { key: "training", title: "My Training", subline: "Courses, lessons and assessments", icon: () => <BookIcon /> },
  { key: "adoption", title: "Adoption & Execution", subline: "Rolling score, 5-factor breakdown & assistance", icon: () => <TrendingUpIcon /> },
  { key: "inbox", title: "Exceptions & Triage", subline: "Critical ops inbox, escalation policies & rapid resolution", icon: () => <InboxIcon /> },
  { key: "owner", title: "Owner Overview", subline: "Live metrics, adoption, SLAs and digests", icon: () => <ChartBarIcon /> },
];

/** Which server module each page needs; pages without one are always available. */
const PAGE_FEATURE: Partial<Record<AppPage, Feature>> = {
  work: "work", training: "training", adoption: "adoption", inbox: "inbox", owner: "owner",
};

/** Small local icon button with a CSS tooltip. */
function IconButton({
  label, onClick, children, tone = "default",
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
  tone?: "default" | "close";
}) {
  return (
    <button
      type="button"
      className={`dg-toolbar__btn${tone === "close" ? " dg-toolbar__btn--close" : ""}`}
      aria-label={label}
      data-tip={label}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function Toolbar() {
  const { status, session, signOut } = useSession();
  const [appViewOpen, setAppViewOpen] = useState(false);
  const [page, setPage] = useState<AppPage>("home");
  const [workReloadSignal, setWorkReloadSignal] = useState(0);
  const [trainingReloadSignal, setTrainingReloadSignal] = useState(0);
  const [isMaximized, setIsMaximized] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const [paletteQuery, setPaletteQuery] = useState("");
  const [paletteIndex, setPaletteIndex] = useState(0);
  const [problemReportOpen, setProblemReportOpen] = useState(false);
  const [helpDrawerOpen, setHelpDrawerOpen] = useState(false);
  const brandButtonRef = useRef<HTMLButtonElement | null>(null);
  const paletteInputRef = useRef<HTMLInputElement | null>(null);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [noticeStatus, setNoticeStatus] = useState<NoticeStatus>({ kind: "loading" });
  const [capabilities, setCapabilities] = useState<Capabilities>({});

  // Hide screens the connected server can't support (module not installed)
  // rather than letting them fail with a raw 404.
  useEffect(() => {
    setCapabilities({});
    if (status !== "signed_in" || !session) return;
    let cancelled = false;
    probeCapabilities()
      .then((caps) => { if (!cancelled) setCapabilities(caps); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [status, session]);

  const pageAvailable = useCallback((p: AppPage) => {
    const feature = PAGE_FEATURE[p];
    return !feature || isAvailable(capabilities, feature);
  }, [capabilities]);

  useEffect(() => {
    if (!pageAvailable(page)) setPage("home");
  }, [page, pageAvailable]);
  const [onboardingDismissed, setOnboardingDismissed] = useState(false);

  // ---- Monitoring notice + first-run onboarding ---------------------------
  useEffect(() => {
    setOnboardingDismissed(false);
    if (status !== "signed_in" || !session) {
      setNoticeStatus({ kind: "loading" });
      return;
    }
    let cancelled = false;
    setNoticeStatus({ kind: "loading" });
    fetchNotice()
      .then((notice) => { if (!cancelled) setNoticeStatus(noticeStatusFrom(notice)); })
      .catch((err) => { if (!cancelled) setNoticeStatus(noticeStatusFromError(err)); });
    return () => { cancelled = true; };
  }, [status, session]);

  // Latched: acknowledging the notice flips it to "acknowledged" mid-flow,
  // which would otherwise pull the onboarding away before its last step --
  // the one with "Start my training" on it.
  const [onboardingLatched, setOnboardingLatched] = useState(false);
  const onboardingDue =
    status === "signed_in" &&
    !!session &&
    shouldShowOnboarding(noticeStatus, hasSeenWelcome(session.db, session.uid));
  useEffect(() => {
    if (onboardingDue) setOnboardingLatched(true);
  }, [onboardingDue]);
  useEffect(() => {
    if (status !== "signed_in") setOnboardingLatched(false);
  }, [status]);
  const showOnboarding =
    status === "signed_in" && !!session && !onboardingDismissed && (onboardingDue || onboardingLatched);

  const handleAcknowledge = useCallback(async () => {
    if (noticeStatus.kind !== "needs_ack") return;
    let client = "DeployGuard Desktop";
    try {
      client = `DeployGuard Desktop ${await getVersion()}`;
    } catch {
      // Version lookup is only for the audit record's "client" note.
    }
    const updated = await acknowledgeNotice(noticeStatus.notice.version, client);
    setNoticeStatus(noticeStatusFrom(updated));
  }, [noticeStatus]);

  const finishOnboarding = useCallback((target: "training" | "work") => {
    if (session) markWelcomeSeen(session.db, session.uid);
    setOnboardingDismissed(true);
    setPage(target);
  }, [session]);

  // ---- Avatar: cached first, then a background refresh from Odoo --------
  useEffect(() => {
    if (status !== "signed_in" || !session) {
      setAvatarUrl(null);
      return;
    }
    const cached = getCachedAvatar(session.uid);
    setAvatarUrl(cached);

    let cancelled = false;
    invoke<string | null>("odoo_fetch_avatar")
      .then((dataUrl) => {
        if (cancelled || !dataUrl) return;
        setCachedAvatar(session.uid, dataUrl);
        setAvatarUrl(dataUrl);
      })
      .catch(() => {
        // No network fetch this launch — the cached avatar (if any) or the
        // initials fallback below is all we show. Not worth surfacing an
        // error for a cosmetic feature.
      });
    return () => { cancelled = true; };
  }, [status, session]);

  // ---- Window state (unchanged behavior) ---------------------------------
  useEffect(() => {
    const win = getCurrentWindow();
    let cancelled = false;
    win.isMaximized().then((m) => { if (!cancelled) setIsMaximized(m); }).catch(() => {});
    const unlistenPromise = win.onResized(() => {
      win.isMaximized().then((m) => { if (!cancelled) setIsMaximized(m); }).catch(() => {});
    });
    return () => {
      cancelled = true;
      unlistenPromise.then((unlisten) => unlisten()).catch(() => {});
    };
  }, []);

  const minimizeWindow = useCallback(() => void invoke("window_minimize"), []);
  const toggleMaximizeWindow = useCallback(() => void invoke("window_toggle_maximize"), []);
  const closeWindow = useCallback(() => void invoke("window_close"), []);

  // ---- App view (unchanged behavior) -------------------------------------
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

  useEffect(() => {
    let cancelled = false;
    invoke<boolean>("get_app_view_open")
      .then((isOpen) => { if (!cancelled && isOpen) setAppViewOpen(true); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // A first-run employee should land on the welcome, not on Odoo's home --
  // once per sign-in. If they close it they can still use Odoo; the welcome
  // is simply what the app view shows until they've been through it.
  const onboardingAutoOpened = useRef(false);
  useEffect(() => {
    if (!showOnboarding) {
      onboardingAutoOpened.current = false;
      return;
    }
    if (!onboardingAutoOpened.current) {
      onboardingAutoOpened.current = true;
      if (!appViewOpen) openAppView();
    }
  }, [showOnboarding, appViewOpen, openAppView]);

  useEffect(() => {
    const unlistenPromise = listen<SessionEvent>("deployguard://session-changed", (event) => {
      if (event.payload.status === "signed_in" && event.payload.auto_reveal) {
        setAppViewOpen(true);
      }
    });
    return () => { unlistenPromise.then((unlisten) => unlisten()).catch(() => {}); };
  }, []);

  // ---- Keyboard: Escape (existing) + ⌘K/Ctrl+K (new) ---------------------
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const mod = e.metaKey || e.ctrlKey;
      if (mod && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((v) => !v);
        return;
      }
      if (e.key === "Escape") {
        if (commandOpen) { setCommandOpen(false); return; }
        if (appViewOpen) {
          closeAppView();
          brandButtonRef.current?.focus();
        }
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [appViewOpen, commandOpen, closeAppView]);

  // Reset + focus the palette each time it opens.
  useEffect(() => {
    if (!commandOpen) return;
    setPaletteQuery("");
    setPaletteIndex(0);
    const id = requestAnimationFrame(() => paletteInputRef.current?.focus());
    return () => cancelAnimationFrame(id);
  }, [commandOpen]);

  // ---- Odoo nav (unchanged behavior) -------------------------------------
  const goToOdoo = useCallback((path?: string) => {
    void invoke("navigate_odoo", { path });
    closeAppView();
  }, [closeAppView]);

  const goBack = useCallback(() => void invoke("odoo_back"), []);
  const goForward = useCallback(() => void invoke("odoo_forward"), []);
  const reload = useCallback(() => {
    // Reload always targeting the Odoo webview is a no-op the user can
    // see whenever a DeployGuard page (like My Work) covers it -- that
    // webview is invisible while appViewOpen, so "nothing happens" is
    // exactly what you'd expect from reloading a hidden page. Route to
    // whatever's actually on screen instead.
    if (appViewOpen && page === "work") {
      setWorkReloadSignal((n) => n + 1);
      return;
    }
    if (appViewOpen && page === "training") {
      setTrainingReloadSignal((n) => n + 1);
      return;
    }
    void invoke("odoo_reload");
  }, [appViewOpen, page]);

  // ---- Command palette ---------------------------------------------------
  type Command = {
    id: string; label: string; group: string; icon: ReactNode; shortcut?: string; run: () => void;
  };

  const commands = useMemo<Command[]>(() => {
    const list: Command[] = [
      {
        id: "home", group: "Navigate", label: "Go to Home",
        icon: <HomeIcon size={16} />,
        run: () => { openAppView(); setPage("home"); },
      },
      {
        id: "work", group: "Navigate", label: "Go to My Work & Sweeps",
        icon: <ClipboardListIcon size={16} />,
        run: () => { openAppView(); setPage("work"); },
      },
      {
        id: "training", group: "Navigate", label: "Go to My Training",
        icon: <BookIcon size={16} />,
        run: () => { openAppView(); setPage("training"); },
      },
      {
        id: "adoption", group: "Navigate", label: "Go to Adoption & Execution",
        icon: <TrendingUpIcon size={16} />,
        run: () => { openAppView(); setPage("adoption"); },
      },
      {
        id: "inbox", group: "Navigate", label: "Go to Exceptions Inbox",
        icon: <InboxIcon size={16} />,
        run: () => { openAppView(); setPage("inbox"); },
      },
      {
        id: "owner", group: "Navigate", label: "Go to Owner Overview",
        icon: <ChartBarIcon size={16} />,
        run: () => { openAppView(); setPage("owner"); },
      },
      {
        id: "help", group: "Support", label: "Help Centre & Knowledge Base",
        icon: <HelpIcon size={16} />,
        run: () => setHelpDrawerOpen(true),
      },
      {
        id: "report-issue", group: "Support", label: "Report a Problem / Something's Wrong",
        icon: <LifeBuoyIcon size={16} />,
        run: () => setProblemReportOpen(true),
      },
      {
        id: "odoo", group: "Navigate", label: "Open DogForce ERP",
        icon: <OdooIcon size={16} />,
        run: () => goToOdoo(),
      },
      {
        id: "back", group: "Odoo", label: "Back",
        icon: <BackIcon size={16} />, shortcut: "⌘[",
        run: () => goBack(),
      },
      {
        id: "forward", group: "Odoo", label: "Forward",
        icon: <ForwardIcon size={16} />, shortcut: "⌘]",
        run: () => goForward(),
      },
      {
        id: "reload", group: "Odoo", label: "Reload",
        icon: <ReloadIcon size={16} />, shortcut: "⌘R",
        run: () => reload(),
      },
      {
        id: "toggle-appview", group: "View", label: appViewOpen ? "Close DogForce" : "Open DogForce",
        icon: <ChevronDownIcon size={16} />,
        run: () => toggleAppView(),
      },
      {
        id: "minimize", group: "Window", label: "Minimize",
        icon: <WindowMinimizeIcon size={16} />,
        run: () => minimizeWindow(),
      },
      {
        id: "maximize", group: "Window", label: isMaximized ? "Restore" : "Maximize",
        icon: isMaximized ? <WindowRestoreIcon size={16} /> : <WindowMaximizeIcon size={16} />,
        run: () => toggleMaximizeWindow(),
      },
      {
        id: "close", group: "Window", label: "Close window",
        icon: <WindowCloseIcon size={16} />,
        run: () => closeWindow(),
      },
    ];
    if (status === "signed_in") {
      list.push({
        id: "signout", group: "Account", label: "Sign out",
        icon: <HelpIcon size={16} />,
        run: () => void signOut(),
      });
    }
    // Page commands share their id with the page they open.
    return list.filter((c) => !(c.id in PAGE_FEATURE) || pageAvailable(c.id as AppPage));
  }, [
    pageAvailable,
    appViewOpen, isMaximized, status, openAppView, goToOdoo, goBack, goForward,
    reload, toggleAppView, minimizeWindow, toggleMaximizeWindow, closeWindow, signOut,
  ]);

  const filtered = useMemo(() => {
    const q = paletteQuery.trim().toLowerCase();
    if (!q) return commands;
    return commands.filter(
      (c) => c.label.toLowerCase().includes(q) || c.group.toLowerCase().includes(q),
    );
  }, [commands, paletteQuery]);

  useEffect(() => { setPaletteIndex(0); }, [paletteQuery]);

  const runCommand = useCallback((c: Command) => {
    setCommandOpen(false);
    // Defer so the palette can unmount before any focus-stealing work runs.
    requestAnimationFrame(() => c.run());
  }, []);

  const avatarHue = session ? hueOf(session.name) : 0;

  return (
    <div className="dg-shell">
      <div className="dg-toolbar">
        <div className="dg-toolbar__nav" role="group" aria-label="Odoo navigation">
          <IconButton label="Back" onClick={goBack}><BackIcon size={16} /></IconButton>
          <IconButton label="Forward" onClick={goForward}><ForwardIcon size={16} /></IconButton>
          <IconButton label="Reload" onClick={reload}><ReloadIcon size={15} /></IconButton>
          <span className="dg-toolbar__divider" aria-hidden="true" />
          <IconButton label="DogForce ERP home" onClick={() => goToOdoo()}>
            <OdooIcon size={16} />
          </IconButton>
          <IconButton label="Help Centre & Knowledge" onClick={() => setHelpDrawerOpen(true)}>
            <HelpIcon size={16} />
          </IconButton>
        </div>

        <button
          ref={brandButtonRef}
          type="button"
          className={`dg-toolbar__brand${appViewOpen ? " is-open" : ""}`}
          aria-expanded={appViewOpen}
          aria-label={appViewOpen ? "Close DogForce" : "Open DogForce"}
          onClick={toggleAppView}
        >
          <img className="dg-toolbar__brand-logo" src={dogforceLogo} alt="" aria-hidden="true" />
          <span className="dg-toolbar__brand-label">DogForce</span>
          <ChevronDownIcon size={14}  />
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
              <span
                className="dg-toolbar__avatar"
                aria-hidden="true"
                style={{
                  background: `linear-gradient(135deg, hsl(${avatarHue} 62% 46%), hsl(${(avatarHue + 40) % 360} 68% 38%))`,
                }}
              >
                {initialsOf(session.name)}
              </span>
            )}
            <span className="dg-toolbar__profile-name">{session.name}</span>
            <span className="dg-toolbar__presence" aria-label="Signed in" />
          </div>
        ) : (
          <span className="dg-toolbar__signedout">Not signed in</span>
        )}

        <div className="dg-toolbar__winctl" role="group" aria-label="Window controls">
          <button
            type="button" className="dg-toolbar__winbtn"
            aria-label="Minimize" data-tip="Minimize" onClick={minimizeWindow}
          >
            <WindowMinimizeIcon size={14} />
          </button>
          <button
            type="button" className="dg-toolbar__winbtn"
            aria-label={isMaximized ? "Restore" : "Maximize"}
            data-tip={isMaximized ? "Restore" : "Maximize"}
            onClick={toggleMaximizeWindow}
          >
            {isMaximized ? <WindowRestoreIcon size={13} /> : <WindowMaximizeIcon size={13} />}
          </button>
          <button
            type="button" className="dg-toolbar__winbtn dg-toolbar__winbtn--close"
            aria-label="Close" data-tip="Close" onClick={closeWindow}
          >
            <WindowCloseIcon size={14} />
          </button>
        </div>
      </div>

      {appViewOpen && (
        <div className="dg-appview" role="dialog" aria-modal="false" aria-label="DogForce">
          <nav className="dg-appview__nav" aria-label="DogForce sections">
            <div className="dg-appview__nav-group">Workspace</div>
            {NAV_ITEMS.filter((item) => pageAvailable(item.key)).map((item) => (
              <button
                key={item.key}
                type="button"
                className={`dg-appview__navitem${page === item.key ? " is-active" : ""}`}
                aria-current={page === item.key ? "page" : undefined}
                onClick={() => setPage(item.key)}
              >
                <span className="dg-appview__navitem-icon">{item.icon()}</span>
                <span className="dg-appview__navitem-label">{item.label}</span>
              </button>
            ))}

            {COMING_SOON_ITEMS.length > 0 && <div className="dg-appview__nav-group">Upcoming</div>}
            {COMING_SOON_ITEMS.map((label) => (
              <div
                key={label}
                className="dg-appview__navitem dg-appview__navitem--soon"
                aria-disabled="true"
              >
                <span className="dg-appview__navitem-dot" aria-hidden="true" />
                <span className="dg-appview__navitem-label">{label}</span>
                <span className="dg-chip">Soon</span>
              </div>
            ))}

            <div className="dg-appview__nav-foot">
              <button
                type="button"
                className="dg-palette-hint"
                onClick={() => setCommandOpen(true)}
              >
                <span>Quick actions</span>
                <kbd>⌘K</kbd>
              </button>
            </div>
          </nav>

          <div className="dg-appview__content">
            <header className="dg-appview__topbar">
              <StatusBar />
            </header>

            {status === "checking" && (
              <div className="dg-appview__body">
                <div className="dg-skeleton dg-skeleton--title" />
                <div className="dg-appview__grid">
                  <div className="dg-skeleton dg-skeleton--tile" />
                  <div className="dg-skeleton dg-skeleton--card" />
                  <div className="dg-skeleton dg-skeleton--card" />
                </div>
              </div>
            )}

            {status === "signed_out" && (
              <div className="dg-appview__body">
                <div className="dg-emptystate">
                  <img className="dg-emptystate__glyph" src={dogforceLogo} alt="" aria-hidden="true" />
                  <h2>Sign in to continue</h2>
                  <p>
                    Sign in on the DogForce ERP page to get started —
                    nothing extra to remember, it's your existing DogForce Odoo login.
                  </p>
                  <button
                    type="button"
                    className="dg-btn dg-btn--primary"
                    onClick={() => goToOdoo()}
                  >
                    <OdooIcon size={16} /> Open DogForce ERP
                  </button>
                  <DiagnosticsPanel />
                </div>
              </div>
            )}

            {showOnboarding && session && (
              <div className="dg-appview__body">
                <FirstRunOnboarding
                  firstName={session.name.split(" ")[0]}
                  status={noticeStatus}
                  onAcknowledge={handleAcknowledge}
                  onFinish={finishOnboarding}
                />
              </div>
            )}

            {status === "signed_in" && session && !showOnboarding && page ==="home" && (
              <div className="dg-appview__body">
                <h1 className="dg-greeting">
                  {greeting()}, <span>{session.name.split(" ")[0]}</span>
                </h1>

                <div className="dg-appview__grid">
                  <button
                    type="button"
                    className="dg-tile"
                    style={{ animationDelay: "40ms" }}
                    onClick={() => goToOdoo()}
                  >
                    <span className="dg-tile__icon"><OdooIcon /></span>
                    <span className="dg-tile__body">
                      <span className="dg-tile__title">DogForce ERP</span>
                      <span className="dg-tile__subline">
                        Rosters, attendance, incidents, reports
                      </span>
                    </span>
                    <span className="dg-tile__arrow" aria-hidden="true">→</span>
                  </button>

                  {HOME_TILES.filter((tile) => pageAvailable(tile.key)).map((tile, i) => (
                    <button
                      key={tile.key}
                      type="button"
                      className="dg-tile"
                      style={{ animationDelay: `${90 + i * 50}ms` }}
                      onClick={() => setPage(tile.key)}
                    >
                      <span className="dg-tile__icon">{tile.icon()}</span>
                      <span className="dg-tile__body">
                        <span className="dg-tile__title">{tile.title}</span>
                        <span className="dg-tile__subline">{tile.subline}</span>
                      </span>
                      <span className="dg-tile__arrow" aria-hidden="true">→</span>
                    </button>
                  ))}
                </div>

                <footer className="dg-appview__footer">
                  <button
                    type="button"
                    className="dg-btn dg-btn--secondary"
                    onClick={() => void signOut()}
                  >
                    Sign out
                  </button>
                  <button
                    type="button"
                    className="dg-appview__help"
                    style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", padding: 0, display: "inline-flex", alignItems: "center", gap: 6 }}
                    onClick={() => setProblemReportOpen(true)}
                  >
                    <HelpIcon size={16} />
                    Something not working? Report an issue
                  </button>
                </footer>
              </div>
            )}

            {status === "signed_in" && session && !showOnboarding && page ==="work" && (
              <div className="dg-appview__body">
                <MyWork reloadSignal={workReloadSignal} />
              </div>
            )}
            {status === "signed_in" && session && !showOnboarding && page ==="training" && (
              <div className="dg-appview__body">
                <MyTraining reloadSignal={trainingReloadSignal} />
              </div>
            )}
            {status === "signed_in" && session && !showOnboarding && page ==="adoption" && (
              <div className="dg-appview__body">
                {adoptionAllowed(noticeStatus) ? (
                  <AdoptionOverview />
                ) : (
                  <div className="dg-card dg-gatecard dg-page-enter">
                    <h2 className="dg-onboarding__title">Adoption figures aren't shown yet</h2>
                    {noticeStatus.kind === "unavailable" ? (
                      <p>
                        Your administrator still needs to finish setting up DeployGuard on the server
                        (the DeployGuard Bridge module), so there's no way yet to record that you've been
                        told what's collected. Until then, no adoption figures are shown here.
                      </p>
                    ) : noticeStatus.kind === "error" ? (
                      <p>{noticeStatus.message}</p>
                    ) : (
                      <p>Checking whether you've seen the monitoring notice…</p>
                    )}
                  </div>
                )}
              </div>
            )}
            {status === "signed_in" && session && !showOnboarding && page ==="inbox" && (
              <div className="dg-appview__body">
                <ExceptionsInbox />
              </div>
            )}
            {status === "signed_in" && session && !showOnboarding && page ==="owner" && (
              <div className="dg-appview__body">
                <OwnerOverview />
              </div>
            )}
          </div>
        </div>
      )}

      {commandOpen && (
        <div className="dg-palette" role="dialog" aria-modal="true" aria-label="Command palette">
          <div className="dg-palette__backdrop" onClick={() => setCommandOpen(false)} />
          <div className="dg-palette__panel" role="combobox" aria-expanded="true" aria-controls="dg-palette-list">
            <div className="dg-palette__inputwrap">
              <svg className="dg-palette__search" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
                <path
                  d="M11.2 10.1a5 5 0 1 0-1.1 1.1l2.8 2.8.9-.9-2.6-3ZM7.5 11a3.5 3.5 0 1 1 0-7 3.5 3.5 0 0 1 0 7Z"
                  fill="currentColor"
                />
              </svg>
              <input
                ref={paletteInputRef}
                className="dg-palette__input"
                placeholder="Type a command or search…"
                value={paletteQuery}
                onChange={(e) => setPaletteQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "ArrowDown") {
                    e.preventDefault();
                    setPaletteIndex((i) => Math.min(i + 1, Math.max(filtered.length - 1, 0)));
                  } else if (e.key === "ArrowUp") {
                    e.preventDefault();
                    setPaletteIndex((i) => Math.max(i - 1, 0));
                  } else if (e.key === "Enter") {
                    e.preventDefault();
                    const c = filtered[paletteIndex];
                    if (c) runCommand(c);
                  }
                }}
                aria-controls="dg-palette-list"
                aria-activedescendant={
                  filtered[paletteIndex] ? `dg-cmd-${filtered[paletteIndex].id}` : undefined
                }
              />
              <kbd className="dg-palette__esc">Esc</kbd>
            </div>

            <div className="dg-palette__list" id="dg-palette-list" role="listbox">
              {filtered.length === 0 && (
                <div className="dg-palette__empty">No matching commands</div>
              )}
              {filtered.map((c, i) => (
                <button
                  key={c.id}
                  id={`dg-cmd-${c.id}`}
                  type="button"
                  role="option"
                  aria-selected={i === paletteIndex}
                  className={`dg-palette__item${i === paletteIndex ? " is-active" : ""}`}
                  onMouseEnter={() => setPaletteIndex(i)}
                  onClick={() => runCommand(c)}
                >
                  <span className="dg-palette__item-icon">{c.icon}</span>
                  <span className="dg-palette__item-label">{c.label}</span>
                  <span className="dg-palette__item-group">{c.group}</span>
                  {c.shortcut && <kbd className="dg-palette__kbd">{c.shortcut}</kbd>}
                </button>
              ))}
            </div>

            <div className="dg-palette__footer">
              <span aria-live="polite">
                {filtered.length} {filtered.length === 1 ? "result" : "results"}
              </span>
              <span className="dg-palette__legend">
                <kbd>↑</kbd><kbd>↓</kbd> navigate <kbd>↵</kbd> run
              </span>
            </div>
          </div>
        </div>
      )}

      <ProblemReportDialog
        isOpen={problemReportOpen}
        onClose={() => setProblemReportOpen(false)}
        currentRoute={`/${page}`}
      />

      <HelpDrawer
        isOpen={helpDrawerOpen}
        onClose={() => setHelpDrawerOpen(false)}
        currentRoute={`/${page}`}
        onOpenReportProblem={() => setProblemReportOpen(true)}
      />
    </div>
  );
}