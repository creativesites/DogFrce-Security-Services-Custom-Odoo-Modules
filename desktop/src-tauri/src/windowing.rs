//! Builds the single application window and its two child webviews.
//!
//! Architecture (revised 2026-09-16 twice — first to a persistent toolbar
//! with a mega-menu dropdown, then to a full **app view** the toolbar
//! switches into, since the DeployGuard side is a real, growing app with
//! its own Home and future pages, not a glance-only dropdown. Supersedes
//! the earlier hover-handle sidebar design; see DEVIATIONS.md D-2/D-3):
//!
//!   ┌──────────────────────────────────────────────────────────┐
//!   │ "shell" webview: toolbar (always visible, full width)      │
//!   │  ⟨ ⟩ ⟳  DG DeployGuard          status ······ name  ⏻     │
//!   ├──────────────────────────────────────────────────────────┤
//!   │  EITHER "odoo" (default — fills the rest of the window,    │
//!   │  this is the PRIMARY content the user works in all day)    │
//!   │                                                            │
//!   │  OR, while the app view is open, "shell" itself grows to   │
//!   │  cover this whole area too (Odoo is still running          │
//!   │  underneath, just fully covered) — a real app page (Home   │
//!   │  today, more to come: Training, Work, …), not a dropdown.  │
//!   └──────────────────────────────────────────────────────────┘
//!
//! Security model (unchanged): the "odoo" webview gets ZERO Tauri IPC
//! capabilities (see capabilities/main.json, scoped by
//! `"webviews": ["shell"]`, not by window). No script is injected into it
//! persistently. Back/forward/reload use `Webview::eval()` for one-off,
//! Rust-initiated calls (`history.back()` etc.) — the same thing a native
//! browser chrome's back button does; this exposes no API *to* the page
//! and the page cannot call back into us. We separately READ the "odoo"
//! webview's cookies (`Webview::cookies()`) after navigation to detect
//! sign-in; we never write to them.

use crate::guard::{self, NavDecision};
use crate::state::{AppState, SessionInfo, ViewMode};
use crate::{errors::AppError, odoo};
use serde::Serialize;
use tauri::{
    webview::PageLoadEvent, AppHandle, Emitter, LogicalPosition, LogicalSize, Manager, State,
    WebviewBuilder, WebviewUrl, WindowBuilder,
};

pub const ODOO_LABEL: &str = "odoo";
pub const SHELL_LABEL: &str = "shell";
pub const WINDOW_LABEL: &str = "main";

pub const TOOLBAR_HEIGHT: f64 = 48.0;
/// Width of the guided-task side panel. Odoo keeps the rest; at the 1024 px
/// minimum window width that still leaves Odoo ~644 px, which is enough for
/// its form and list views.
pub const GUIDE_DOCK_WIDTH: f64 = 380.0;

type Bounds = (LogicalPosition<f64>, LogicalSize<f64>);

/// "shell" bounds per view mode. A webview is a single rectangle, so the guide
/// dock is a full-height right-hand column (it carries its own drag region and
/// window controls) rather than toolbar + column.
fn shell_bounds(window_width: f64, window_height: f64, mode: ViewMode) -> Bounds {
    match mode {
        ViewMode::Odoo => (
            LogicalPosition::new(0.0, 0.0),
            LogicalSize::new(window_width, TOOLBAR_HEIGHT.min(window_height)),
        ),
        ViewMode::App => (
            LogicalPosition::new(0.0, 0.0),
            LogicalSize::new(window_width, window_height),
        ),
        ViewMode::GuideDock => {
            let dock = GUIDE_DOCK_WIDTH.min(window_width);
            (
                LogicalPosition::new(window_width - dock, 0.0),
                LogicalSize::new(dock, window_height),
            )
        }
    }
}

/// "odoo" bounds per view mode: below the toolbar normally, and full height to
/// the left of the dock while a guided task is running.
fn odoo_bounds(window_width: f64, window_height: f64, mode: ViewMode) -> Bounds {
    match mode {
        ViewMode::GuideDock => (
            LogicalPosition::new(0.0, 0.0),
            LogicalSize::new((window_width - GUIDE_DOCK_WIDTH).max(0.0), window_height),
        ),
        _ => (
            LogicalPosition::new(0.0, TOOLBAR_HEIGHT),
            LogicalSize::new(window_width, (window_height - TOOLBAR_HEIGHT).max(0.0)),
        ),
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum SessionEvent {
    SignedIn {
        session: SessionInfo,
        auto_reveal: bool,
    },
    SignedOut,
    /// Odoo rejected the session mid-use (JSON-RPC code 100). Distinct from a
    /// deliberate sign-out so the shell can say "your session expired" rather
    /// than silently showing the sign-in screen.
    Expired,
}

/// The window's initial logical content size, matching the `inner_size`
/// requested from `WindowBuilder` below. We deliberately do NOT re-query
/// `window.inner_size()` right after `build()` to compute the initial
/// child-webview bounds: on macOS in particular, the OS can still be
/// finishing the window's real geometry when that synchronous call runs,
/// so it can return a stale/default size — the toolbar would render with
/// wrong bounds until the first real `Resized` event (e.g. the user
/// maximizing the window) recalculated it correctly. Using the size we
/// know we asked for avoids the race entirely; the `on_window_event`
/// resize handler below is what keeps things correct afterward, and it
/// *is* safe to trust because it's driven by a real, already-applied
/// resize.
const INITIAL_WINDOW_SIZE: (f64, f64) = (1280.0, 860.0);

pub fn build(app: &AppHandle) -> tauri::Result<()> {
    let window = WindowBuilder::new(app, WINDOW_LABEL)
        .title("DogForce Security Services")
        .inner_size(INITIAL_WINDOW_SIZE.0, INITIAL_WINDOW_SIZE.1)
        .min_inner_size(1024.0, 700.0)
        // Custom title bar (see Toolbar.tsx): the toolbar itself carries
        // the drag region and window controls, VS Code–style, instead of
        // stacking our chrome under a separate native title bar.
        .decorations(false)
        .center()
        .build()?;

    let logical = LogicalSize::new(INITIAL_WINDOW_SIZE.0, INITIAL_WINDOW_SIZE.1);

    // "odoo" — fills the window below the toolbar. No IPC (see capabilities/main.json).
    let (odoo_pos, odoo_size) = odoo_bounds(logical.width, logical.height, ViewMode::Odoo);
    let nav_app = app.clone();
    let popup_app = app.clone();
    let odoo_builder = WebviewBuilder::new(
        ODOO_LABEL,
        WebviewUrl::External(odoo::initial_url().parse().unwrap()),
    )
    // The "odoo" webview stays on the Odoo origin (16 §7). Anything else is
    // handed to the OS (browser/mail) or refused -- it never loads inside
    // the trusted app chrome.
    .on_navigation(move |url| handle_odoo_navigation(&nav_app, url))
    .on_new_window(move |url, _features| {
        // Same-origin popups (e.g. Odoo's "print" or "open in new tab")
        // keep the default behaviour: an unmanaged window with no IPC.
        // Anything else goes to the system browser.
        if guard::is_odoo_origin(&crate::config::odoo_base_url(), &url) {
            tauri::webview::NewWindowResponse::Allow
        } else {
            let _ = handle_odoo_navigation(&popup_app, &url);
            tauri::webview::NewWindowResponse::Deny
        }
    })
    .on_page_load(|webview, payload| {
        if payload.event() != PageLoadEvent::Finished {
            return;
        }
        let url = payload.url().clone();
        let app = webview.app_handle().clone();
        tauri::async_runtime::spawn(async move {
            sync_session_from_odoo(&app, &url).await;
        });
    });
    window.add_child(odoo_builder, odoo_pos, odoo_size)?;

    // "shell" — toolbar (+ mega menu when open). Full IPC. Added AFTER
    // "odoo" so it stacks on top when the menu overlays Odoo's content.
    let (shell_pos, shell_size) = shell_bounds(logical.width, logical.height, ViewMode::Odoo);
    let shell_builder = WebviewBuilder::new(SHELL_LABEL, WebviewUrl::App("index.html".into()));
    window.add_child(shell_builder, shell_pos, shell_size)?;

    // Keep both children sized to the window as it's resized; re-derive
    // from current state rather than assuming anything about prior bounds.
    let app_handle = app.clone();
    window.on_window_event(move |event| {
        if let tauri::WindowEvent::Resized(size) = event {
            let Some(win) = app_handle.get_window(WINDOW_LABEL) else {
                return;
            };
            let Ok(scale) = win.scale_factor() else {
                return;
            };
            let logical: tauri::LogicalSize<f64> = size.to_logical(scale);
            let mode = *app_handle.state::<AppState>().view_mode.lock().unwrap();
            place_webviews(&app_handle, logical.width, logical.height, mode);
        }
    });

    Ok(())
}

/// Decides what the "odoo" webview may do with a navigation, opening
/// non-Odoo web/mail links in the operating system instead.
fn handle_odoo_navigation(app: &AppHandle, url: &tauri::Url) -> bool {
    match guard::navigation_decision(&crate::config::odoo_base_url(), url) {
        NavDecision::Allow => true,
        NavDecision::OpenExternally => {
            tracing::info!(
                scheme = url.scheme(),
                host = url.host_str().unwrap_or(""),
                "opening external link in the system"
            );
            open_externally(app, url.as_str());
            false
        }
        NavDecision::Block => {
            tracing::warn!(
                scheme = url.scheme(),
                "blocked a navigation in the odoo webview"
            );
            false
        }
    }
}

#[allow(deprecated)] // tauri-plugin-shell's `open` is the plugin already bundled; opener would be a new dependency for one call.
fn open_externally(app: &AppHandle, url: &str) {
    use tauri_plugin_shell::ShellExt;
    if let Err(e) = app.shell().open(url, None) {
        tracing::warn!(error = %e, "could not open external link");
    }
}

async fn sync_session_from_odoo(app: &AppHandle, url: &tauri::Url) {
    if odoo::is_unauthenticated_path(url.path()) {
        set_signed_out(app, SessionEvent::SignedOut);
        return;
    }
    // Only pages on the Odoo origin say anything about the Odoo session.
    let base_url = crate::config::odoo_base_url();
    if !guard::is_odoo_origin(&base_url, url) {
        return;
    }

    let Some(odoo_wv) = app.get_webview(ODOO_LABEL) else {
        return;
    };
    let Ok(base) = tauri::Url::parse(&base_url) else {
        return;
    };
    // Scoped to the Odoo URL: never pick up a `session_id` some other site set.
    let cookies = match odoo_wv.cookies_for_url(base) {
        Ok(c) => c,
        Err(e) => {
            // A cookie-store hiccup is not evidence of being signed out; keep
            // whatever we last knew rather than flapping the UI.
            tracing::warn!(error = %e, "could not read odoo webview cookies");
            record_sync_note(app, format!("couldn't read the browser cookies: {e}"));
            return;
        }
    };
    let Some(session_id) = cookies
        .into_iter()
        .find(|c| c.name() == "session_id")
        .map(|c| c.value().to_string())
    else {
        record_sync_note(
            app,
            "the page loaded but no session cookie was set".to_string(),
        );
        set_signed_out(app, SessionEvent::SignedOut);
        return;
    };

    let session = match odoo::fetch_session_info(&session_id).await {
        Ok(session) => session,
        Err(odoo::SessionCheckError::Anonymous) => {
            record_sync_note(app, "that session isn't signed in".to_string());
            set_signed_out(app, SessionEvent::SignedOut);
            return;
        }
        Err(odoo::SessionCheckError::Unverifiable(reason)) => {
            // Network blip or server hiccup: keep the last known session.
            // Connectivity is reported separately (connectivity_check); a
            // really expired session surfaces on the next call as Expired.
            tracing::warn!(reason, "could not verify the odoo session");
            record_sync_note(
                app,
                format!("signed in to Odoo, but couldn't verify it: {reason}"),
            );
            return;
        }
    };
    record_sync_note(app, "signed in successfully".to_string());

    let state = app.state::<AppState>();
    let was_signed_in = state.session.lock().unwrap().is_some();
    *state.session.lock().unwrap() = Some(session.clone());
    *state.session_cookie.lock().unwrap() = Some(session_id);

    let mut revealed = state.has_auto_revealed.lock().unwrap();
    let auto_reveal = !was_signed_in && !*revealed;
    if auto_reveal {
        *revealed = true;
    }
    drop(revealed);

    if auto_reveal {
        set_view_mode(app, ViewMode::App);
    }

    let _ = app.emit_to(
        SHELL_LABEL,
        "deployguard://session-changed",
        SessionEvent::SignedIn {
            session,
            auto_reveal,
        },
    );
}

fn record_sync_note(app: &AppHandle, note: String) {
    *app.state::<AppState>().last_sync_note.lock().unwrap() = Some(note);
}

fn set_signed_out(app: &AppHandle, event: SessionEvent) {
    let state = app.state::<AppState>();
    let mut session = state.session.lock().unwrap();
    if session.is_some() {
        *session = None;
        *state.session_cookie.lock().unwrap() = None;
        *state.has_auto_revealed.lock().unwrap() = false;
        drop(session);
        let _ = app.emit_to(SHELL_LABEL, "deployguard://session-changed", event);
    }
}

/// Called when Odoo rejects the session during a proxied call: clears it,
/// tells the shell it *expired* (not a sign-out), and brings Odoo's login page
/// back so the employee can sign in again.
pub fn session_expired(app: &AppHandle) {
    set_signed_out(app, SessionEvent::Expired);
    set_view_mode(app, ViewMode::Odoo);
    let _ = navigate_odoo(app, "/web/login");
}

fn place_webviews(app: &AppHandle, width: f64, height: f64, mode: ViewMode) {
    if let Some(odoo_wv) = app.get_webview(ODOO_LABEL) {
        let (pos, size) = odoo_bounds(width, height, mode);
        let _ = odoo_wv.set_position(pos);
        let _ = odoo_wv.set_size(size);
    }
    if let Some(shell_wv) = app.get_webview(SHELL_LABEL) {
        let (pos, size) = shell_bounds(width, height, mode);
        let _ = shell_wv.set_position(pos);
        let _ = shell_wv.set_size(size);
    }
}

/// The single place the window layout changes. Emits `deployguard://view-mode`
/// so the shell's React state always follows the native bounds, whoever asked
/// for the change.
pub fn set_view_mode(app: &AppHandle, mode: ViewMode) {
    *app.state::<AppState>().view_mode.lock().unwrap() = mode;
    if let Some(window) = app.get_window(WINDOW_LABEL) {
        if let (Ok(size), Ok(scale)) = (window.inner_size(), window.scale_factor()) {
            let logical: tauri::LogicalSize<f64> = size.to_logical(scale);
            place_webviews(app, logical.width, logical.height, mode);
        }
    }
    let _ = app.emit_to(SHELL_LABEL, "deployguard://view-mode", mode);
}

pub fn navigate_odoo(app: &AppHandle, path: &str) -> Result<(), AppError> {
    let url =
        guard::safe_odoo_url(&crate::config::odoo_base_url(), path).ok_or(AppError::NotAllowed)?;
    if let Some(odoo_wv) = app.get_webview(ODOO_LABEL) {
        odoo_wv.navigate(url).map_err(|_| AppError::Unknown)?;
    }
    Ok(())
}

/// Drives Odoo's own browser history — the same effect a real browser's
/// back/forward/reload buttons would have. One-off `eval()` calls, not a
/// persistent injected script; see the module doc for why this doesn't
/// weaken the isolation between "shell" and "odoo".
pub fn odoo_history_back(app: &AppHandle) -> Result<(), AppError> {
    eval_in_odoo(app, "history.back();")
}

pub fn odoo_history_forward(app: &AppHandle) -> Result<(), AppError> {
    eval_in_odoo(app, "history.forward();")
}

pub fn odoo_reload(app: &AppHandle) -> Result<(), AppError> {
    eval_in_odoo(app, "location.reload();")
}

fn eval_in_odoo(app: &AppHandle, js: &str) -> Result<(), AppError> {
    if let Some(odoo_wv) = app.get_webview(ODOO_LABEL) {
        odoo_wv.eval(js).map_err(|_| AppError::Unknown)?;
    }
    Ok(())
}

/// Window controls for the custom (decorations-off) title bar — the
/// toolbar provides its own minimize/maximize/close buttons since the OS
/// no longer draws any (see `build()`'s `.decorations(false)`).
pub fn window_minimize(app: &AppHandle) -> Result<(), AppError> {
    app.get_window(WINDOW_LABEL)
        .and_then(|w| w.minimize().ok())
        .ok_or(AppError::Unknown)
}

pub fn window_toggle_maximize(app: &AppHandle) -> Result<(), AppError> {
    let Some(window) = app.get_window(WINDOW_LABEL) else {
        return Err(AppError::Unknown);
    };
    let is_maximized = window.is_maximized().map_err(|_| AppError::Unknown)?;
    if is_maximized {
        window.unmaximize().map_err(|_| AppError::Unknown)
    } else {
        window.maximize().map_err(|_| AppError::Unknown)
    }
}

pub fn window_close(app: &AppHandle) -> Result<(), AppError> {
    app.get_window(WINDOW_LABEL)
        .and_then(|w| w.close().ok())
        .ok_or(AppError::Unknown)
}

pub async fn sign_out(app: &AppHandle) {
    let state: State<AppState> = app.state();
    let cookie = state.session_cookie.lock().unwrap().clone();
    if let Some(session_id) = cookie {
        odoo::destroy_session(&session_id).await;
    }
    set_signed_out(app, SessionEvent::SignedOut);
    set_view_mode(app, ViewMode::Odoo);
    let _ = navigate_odoo(app, "/web/login");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn odoo_mode_shell_is_a_full_width_toolbar_strip() {
        let (pos, size) = shell_bounds(1280.0, 860.0, ViewMode::Odoo);
        assert_eq!(pos, LogicalPosition::new(0.0, 0.0));
        assert_eq!(size, LogicalSize::new(1280.0, TOOLBAR_HEIGHT));
    }

    #[test]
    fn app_mode_shell_covers_the_entire_window() {
        let (pos, size) = shell_bounds(1280.0, 860.0, ViewMode::App);
        assert_eq!(pos, LogicalPosition::new(0.0, 0.0));
        assert_eq!(size, LogicalSize::new(1280.0, 860.0));
        let (_, short_size) = shell_bounds(1280.0, 300.0, ViewMode::App);
        assert_eq!(short_size.height, 300.0);
    }

    #[test]
    fn odoo_sits_below_the_toolbar_outside_guidance() {
        for mode in [ViewMode::Odoo, ViewMode::App] {
            let (pos, size) = odoo_bounds(1280.0, 860.0, mode);
            assert_eq!(pos, LogicalPosition::new(0.0, TOOLBAR_HEIGHT));
            assert_eq!(size, LogicalSize::new(1280.0, 860.0 - TOOLBAR_HEIGHT));
        }
    }

    #[test]
    fn odoo_never_negative_height_when_window_shorter_than_toolbar() {
        let (_, size) = odoo_bounds(1280.0, 20.0, ViewMode::Odoo);
        assert_eq!(size.height, 0.0);
    }

    #[test]
    fn guide_dock_puts_odoo_left_and_shell_right_without_overlap() {
        let (opos, osize) = odoo_bounds(1280.0, 860.0, ViewMode::GuideDock);
        let (spos, ssize) = shell_bounds(1280.0, 860.0, ViewMode::GuideDock);
        assert_eq!(opos, LogicalPosition::new(0.0, 0.0));
        assert_eq!(osize, LogicalSize::new(1280.0 - GUIDE_DOCK_WIDTH, 860.0));
        assert_eq!(spos, LogicalPosition::new(1280.0 - GUIDE_DOCK_WIDTH, 0.0));
        assert_eq!(ssize, LogicalSize::new(GUIDE_DOCK_WIDTH, 860.0));
        assert_eq!(opos.x + osize.width, spos.x);
    }

    #[test]
    fn guide_dock_at_minimum_width_leaves_odoo_usable() {
        let (_, osize) = odoo_bounds(1024.0, 700.0, ViewMode::GuideDock);
        assert!(osize.width >= 640.0);
    }
}
