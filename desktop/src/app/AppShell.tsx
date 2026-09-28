import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { getVersion } from "@tauri-apps/api/app";
import { invoke } from "../lib/tauri";
import { useSession } from "../session/SessionContext";
import { useViewMode } from "./viewMode";
import { PAGES, type AppPage } from "./pages";
import { CommandPalette, type Command } from "./CommandPalette";
import { Home } from "./Home";
import { Toolbar } from "../shell/Toolbar";
import { StatusBar } from "../shell/StatusBar";
import { DiagnosticsPanel } from "../shell/DiagnosticsPanel";
import { FirstRunOnboarding } from "../shell/FirstRunOnboarding";
import { ProblemReportDialog } from "../shell/ProblemReportDialog";
import { HelpDrawer } from "../shell/HelpDrawer";
import { MyWork } from "../shell/pages/MyWork";
import { MyTraining } from "../shell/pages/MyTraining";
import { AdoptionOverview } from "../shell/pages/AdoptionOverview";
import { ExceptionsInbox } from "../shell/pages/ExceptionsInbox";
import { OwnerOverview } from "../shell/pages/OwnerOverview";
import { HelpIcon, LifeBuoyIcon, OdooIcon } from "../shell/icons";
import {
  type NoticeStatus, acknowledgeNotice, adoptionAllowed, fetchNotice, hasSeenWelcome, markWelcomeSeen,
  noticeStatusFrom, noticeStatusFromError, shouldShowOnboarding,
} from "../api/onboarding";
import { type Capabilities, isAvailable, probeCapabilities } from "../api/capabilities";
import { fetchViewerContext, type ViewerContext } from "../api/work";
import dogforceLogo from "../assets/dogforce-logo-256.png";

/** Pages only some roles see. The server decides the roles (ViewerContext). */
function roleAllows(page: AppPage, viewer: ViewerContext | null): boolean {
  if (!viewer) return true; // older server: let its own access rules answer
  if (page === "team") return viewer.is_supervisor || viewer.is_manager || viewer.is_owner;
  if (page === "owner") return viewer.is_manager || viewer.is_owner;
  return true;
}

/**
 * The DeployGuard application: which page is showing, first-run onboarding,
 * capability gating, and the overlays. Window layout is owned by
 * `useViewMode()`; this component only asks for changes.
 */
export function AppShell() {
  const { status, session, signOut } = useSession();
  const { mode, setMode, openInOdoo } = useViewMode();
  const appOpen = mode === "app";

  const [page, setPage] = useState<AppPage>("home");
  const [reloadSignal, setReloadSignal] = useState(0);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [problemReportOpen, setProblemReportOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const brandRef = useRef<HTMLButtonElement | null>(null);

  // Keyed on *who* is signed in, never on the session object (commit 40d5849).
  const sessionUid = status === "signed_in" ? session?.uid ?? null : null;
  const sessionDb = session?.db ?? null;

  // ---- What this server and this person can use ---------------------------
  const [capabilities, setCapabilities] = useState<Capabilities>({});
  const [viewer, setViewer] = useState<ViewerContext | null>(null);
  useEffect(() => {
    setCapabilities({});
    setViewer(null);
    if (sessionUid == null) return;
    let cancelled = false;
    probeCapabilities().then((c) => { if (!cancelled) setCapabilities(c); }).catch(() => {});
    fetchViewerContext().then((v) => { if (!cancelled) setViewer(v); }).catch(() => {});
    return () => { cancelled = true; };
  }, [sessionUid, sessionDb]);

  const pageAvailable = useCallback((p: AppPage) => {
    const def = PAGES.find((d) => d.key === p);
    if (!def) return false;
    return (!def.feature || isAvailable(capabilities, def.feature)) && roleAllows(p, viewer);
  }, [capabilities, viewer]);

  useEffect(() => {
    if (!pageAvailable(page)) setPage("home");
  }, [page, pageAvailable]);

  // ---- Monitoring notice + first-run onboarding ----------------------------
  const [noticeStatus, setNoticeStatus] = useState<NoticeStatus>({ kind: "loading" });
  const [onboardingDismissed, setOnboardingDismissed] = useState(false);
  const [onboardingLatched, setOnboardingLatched] = useState(false);

  useEffect(() => {
    setOnboardingDismissed(false);
    setOnboardingLatched(false);
    setNoticeStatus({ kind: "loading" });
    if (sessionUid == null) return;
    let cancelled = false;
    fetchNotice()
      .then((n) => { if (!cancelled) setNoticeStatus(noticeStatusFrom(n)); })
      .catch((err) => { if (!cancelled) setNoticeStatus(noticeStatusFromError(err)); });
    return () => { cancelled = true; };
  }, [sessionUid, sessionDb]);

  const onboardingDue =
    status === "signed_in" && !!session && shouldShowOnboarding(noticeStatus, hasSeenWelcome(session.db, session.uid));
  // Latched: acknowledging flips the notice mid-flow, which would otherwise
  // pull onboarding away before its last step.
  useEffect(() => { if (onboardingDue) setOnboardingLatched(true); }, [onboardingDue]);
  const showOnboarding = status === "signed_in" && !!session && !onboardingDismissed && (onboardingDue || onboardingLatched);

  // A first-run employee lands on the welcome, once per sign-in.
  const onboardingAutoOpened = useRef(false);
  useEffect(() => {
    if (!showOnboarding) {
      onboardingAutoOpened.current = false;
      return;
    }
    if (!onboardingAutoOpened.current) {
      onboardingAutoOpened.current = true;
      if (mode !== "app") setMode("app");
    }
  }, [showOnboarding, mode, setMode]);

  const handleAcknowledge = useCallback(async () => {
    if (noticeStatus.kind !== "needs_ack") return;
    let client = "DeployGuard Desktop";
    try {
      client = `DeployGuard Desktop ${await getVersion()}`;
    } catch {
      // Only for the audit record's "client" note.
    }
    setNoticeStatus(noticeStatusFrom(await acknowledgeNotice(noticeStatus.notice.version, client)));
  }, [noticeStatus]);

  const finishOnboarding = useCallback((target: AppPage) => {
    if (sessionUid != null && sessionDb) markWelcomeSeen(sessionDb, sessionUid);
    setOnboardingDismissed(true);
    setPage(target);
  }, [sessionUid, sessionDb]);

  // ---- Navigation -----------------------------------------------------------
  const goTo = useCallback((p: AppPage) => {
    setPage(p);
    setMode("app");
  }, [setMode]);

  const toggleApp = useCallback(() => setMode(appOpen ? "odoo" : "app"), [appOpen, setMode]);
  const goToOdoo = useCallback((path?: string) => void openInOdoo(path), [openInOdoo]);
  const goBack = useCallback(() => void invoke("odoo_back"), []);
  const goForward = useCallback(() => void invoke("odoo_forward"), []);
  // Reload whatever is on screen: the Odoo webview is hidden while the app is open.
  const reload = useCallback(() => {
    if (appOpen) setReloadSignal((n) => n + 1);
    else void invoke("odoo_reload");
  }, [appOpen]);

  // Overlays need the full window: in Odoo mode the shell is a 48 px strip and
  // a dialog would be clipped to it.
  const openHelp = useCallback(() => { setMode("app"); setHelpOpen(true); }, [setMode]);
  const openReport = useCallback(() => { setMode("app"); setProblemReportOpen(true); }, [setMode]);
  const openPalette = useCallback(() => { setMode("app"); setPaletteOpen(true); }, [setMode]);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && !e.altKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        if (paletteOpen) setPaletteOpen(false);
        else openPalette();
        return;
      }
      if (e.key === "Escape" && !paletteOpen && !helpOpen && !problemReportOpen && appOpen) {
        setMode("odoo");
        brandRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [appOpen, paletteOpen, helpOpen, problemReportOpen, openPalette, setMode]);

  const commands = useMemo<Command[]>(() => {
    const list: Command[] = PAGES.filter((p) => pageAvailable(p.key)).map((p) => ({
      id: `page-${p.key}`, group: "Go to", label: p.label, icon: p.icon(16), run: () => goTo(p.key),
    }));
    list.push(
      { id: "odoo", group: "Go to", label: "DogForce ERP", icon: <OdooIcon size={16} />, run: () => goToOdoo() },
      { id: "help", group: "Support", label: "Help", icon: <HelpIcon size={16} />, run: openHelp },
      { id: "report", group: "Support", label: "Report a problem", icon: <LifeBuoyIcon size={16} />, run: openReport },
    );
    if (status === "signed_in") {
      list.push({ id: "signout", group: "Account", label: "Sign out", icon: <OdooIcon size={16} />, run: () => void signOut() });
    }
    return list;
  }, [pageAvailable, goTo, goToOdoo, openHelp, openReport, status, signOut]);

  const signedIn = status === "signed_in" && !!session && !showOnboarding;

  return (
    <div className="dg-shell">
      <Toolbar
        appOpen={appOpen}
        onToggleApp={toggleApp}
        onOdooHome={() => goToOdoo()}
        onBack={goBack}
        onForward={goForward}
        onReload={reload}
        onHelp={openHelp}
        brandRef={brandRef}
      />

      {appOpen && (
        <div className="dg-appview" aria-label="DeployGuard">
          <nav className="dg-appview__nav" aria-label="DeployGuard sections">
            <div className="dg-appview__nav-group">Workspace</div>
            {PAGES.filter((p) => pageAvailable(p.key)).map((p) => (
              <button
                key={p.key}
                type="button"
                className={`dg-appview__navitem${page === p.key ? " is-active" : ""}`}
                aria-current={page === p.key ? "page" : undefined}
                onClick={() => setPage(p.key)}
              >
                <span className="dg-appview__navitem-icon">{p.icon()}</span>
                <span className="dg-appview__navitem-label">{p.label}</span>
              </button>
            ))}
            <div className="dg-appview__nav-foot">
              <button type="button" className="dg-palette-hint" onClick={openPalette}>
                <span>Quick actions</span>
                <kbd>Ctrl K</kbd>
              </button>
            </div>
          </nav>

          <main className="dg-appview__content">
            <header className="dg-appview__topbar">
              <StatusBar />
            </header>

            {status === "checking" && (
              <div className="dg-appview__body">
                <div className="dg-skeleton dg-skeleton--title" />
                <div className="dg-appview__grid">
                  <div className="dg-skeleton dg-skeleton--tile" />
                  <div className="dg-skeleton dg-skeleton--card" />
                </div>
              </div>
            )}

            {(status === "signed_out" || status === "expired") && (
              <div className="dg-appview__body">
                <div className="dg-emptystate">
                  <img className="dg-emptystate__glyph" src={dogforceLogo} alt="" aria-hidden="true" />
                  <h2>{status === "expired" ? "Your session expired" : "Sign in to continue"}</h2>
                  <p>
                    {status === "expired"
                      ? "For your security, DogForce ERP signed you out. Sign in again and you'll carry on where you were."
                      : "Sign in on the DogForce ERP page with your usual DogForce login. There's nothing extra to remember."}
                  </p>
                  <button type="button" className="dg-btn dg-btn--primary" onClick={() => goToOdoo(status === "expired" ? "/web/login" : undefined)}>
                    <OdooIcon size={16} /> {status === "expired" ? "Sign in again" : "Open DogForce ERP"}
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
                  available={{ work: pageAvailable("work"), training: pageAvailable("training") }}
                  onFinish={(target) => {
                    if (target === "odoo") {
                      finishOnboarding("home");
                      goToOdoo();
                    } else {
                      finishOnboarding(target);
                    }
                  }}
                />
              </div>
            )}

            {signedIn && (
              <div className="dg-appview__body" key={page}>
                {page === "home" && (
                  <Home
                    reloadSignal={reloadSignal}
                    pageAvailable={pageAvailable}
                    onGoTo={goTo}
                    onReportProblem={openReport}
                  />
                )}
                {page === "work" && <MyWork reloadSignal={reloadSignal} />}
                {page === "training" && <MyTraining reloadSignal={reloadSignal} />}
                {page === "inbox" && <ExceptionsInbox />}
                {page === "owner" && <OwnerOverview />}
                {page === "adoption" && (
                  adoptionAllowed(noticeStatus) ? (
                    <AdoptionOverview viewer={viewer} />
                  ) : (
                    <div className="dg-card dg-gatecard dg-page-enter">
                      <h2 className="dg-onboarding__title">Adoption figures aren't shown yet</h2>
                      <p>
                        {noticeStatus.kind === "unavailable"
                          ? "Your administrator still needs to finish setting up DeployGuard on the server, so there's no record yet that you've been told what's collected. Until then, no adoption figures are shown."
                          : noticeStatus.kind === "error"
                            ? noticeStatus.message
                            : "Checking whether you've seen the monitoring notice…"}
                      </p>
                    </div>
                  )
                )}
              </div>
            )}
          </main>
        </div>
      )}

      {paletteOpen && <CommandPalette commands={commands} onClose={() => setPaletteOpen(false)} />}
      {problemReportOpen && <ProblemReportDialog onClose={() => setProblemReportOpen(false)} currentRoute={`/${page}`} />}
      {helpOpen && (
        <HelpDrawer onClose={() => setHelpOpen(false)} currentRoute={`/${page}`} onOpenReportProblem={openReport} />
      )}
    </div>
  );
}
