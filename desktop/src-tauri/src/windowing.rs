//! Builds the single application window and its two child webviews.
//!
//! Architecture (revised 2026-09-16 — persistent toolbar + mega menu,
//! superseding the earlier hover-handle sidebar design; see DEVIATIONS.md
//! D-2 and D-3):
//!
//!   ┌──────────────────────────────────────────────────────────┐
//!   │ "shell" webview: toolbar (always visible, full width)      │
//!   │  ⟨ ⟩ ⟳  DG DeployGuard          status ······ name  ⏻     │
//!   ├──────────────────────────────────────────────────────────┤
//!   │ ┌ mega menu (only while open — overlays the top of Odoo) ┐│
//!   │ │  Home content: greeting, work, training …              ││
//!   │ └──────────────────────────────────────────────────────┘ │
//!   │                                                            │
//!   │   "odoo" webview: Odoo's own UI, filling the window below  │
//!   │   the toolbar — this is the PRIMARY content the user       │
//!   │   works in all day. Never resizes when the menu opens;     │
//!   │   the menu floats over it instead of pushing it down.      │
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

use crate::state::{AppState, SessionInfo};
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
const MEGA_MENU_HEIGHT: f64 = 480.0;

/// The "shell" webview is always at least the toolbar strip, full width,
/// docked to the top. With the mega menu open it grows downward to also
/// cover a menu panel — but never past the window, and it always
/// overlays "odoo" rather than resizing it (odoo's own bounds are
/// independent, see `odoo_bounds`).
fn shell_bounds(window_width: f64, window_height: f64, menu_open: bool) -> (LogicalPosition<f64>, LogicalSize<f64>) {
    let height = if menu_open {
        (TOOLBAR_HEIGHT + MEGA_MENU_HEIGHT).min(window_height)
    } else {
        TOOLBAR_HEIGHT.min(window_height)
    };
    (LogicalPosition::new(0.0, 0.0), LogicalSize::new(window_width, height))
}

fn odoo_bounds(window_width: f64, window_height: f64) -> (LogicalPosition<f64>, LogicalSize<f64>) {
    (
        LogicalPosition::new(0.0, TOOLBAR_HEIGHT),
        LogicalSize::new(window_width, (window_height - TOOLBAR_HEIGHT).max(0.0)),
    )
}

#[derive(Debug, Clone, Serialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum SessionEvent {
    SignedIn { session: SessionInfo, auto_reveal: bool },
    SignedOut,
}

pub fn build(app: &AppHandle) -> tauri::Result<()> {
    let window = WindowBuilder::new(app, WINDOW_LABEL)
        .title("DeployGuard")
        .inner_size(1280.0, 860.0)
        .min_inner_size(1024.0, 700.0)
        .center()
        .build()?;

    let inner_size = window.inner_size()?;
    let logical: tauri::LogicalSize<f64> = inner_size.to_logical(window.scale_factor()?);

    // "odoo" — fills the window below the toolbar. No IPC (see capabilities/main.json).
    let (odoo_pos, odoo_size) = odoo_bounds(logical.width, logical.height);
    let odoo_builder = WebviewBuilder::new(ODOO_LABEL, WebviewUrl::External(odoo::initial_url().parse().unwrap()))
        .on_navigation(|_url| true)
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
    let (shell_pos, shell_size) = shell_bounds(logical.width, logical.height, false);
    let shell_builder = WebviewBuilder::new(SHELL_LABEL, WebviewUrl::App("index.html".into()));
    window.add_child(shell_builder, shell_pos, shell_size)?;

    // Keep both children sized to the window as it's resized; re-derive
    // from current state rather than assuming anything about prior bounds.
    let app_handle = app.clone();
    window.on_window_event(move |event| {
        if let tauri::WindowEvent::Resized(size) = event {
            let Some(win) = app_handle.get_window(WINDOW_LABEL) else { return };
            let Ok(scale) = win.scale_factor() else { return };
            let logical: tauri::LogicalSize<f64> = size.to_logical(scale);
            if let Some(odoo_wv) = app_handle.get_webview(ODOO_LABEL) {
                let (pos, size) = odoo_bounds(logical.width, logical.height);
                let _ = odoo_wv.set_position(pos);
                let _ = odoo_wv.set_size(size);
            }
            if let Some(shell_wv) = app_handle.get_webview(SHELL_LABEL) {
                let menu_open = *app_handle.state::<AppState>().overlay_expanded.lock().unwrap();
                let (pos, size) = shell_bounds(logical.width, logical.height, menu_open);
                let _ = shell_wv.set_position(pos);
                let _ = shell_wv.set_size(size);
            }
        }
    });

    Ok(())
}

async fn sync_session_from_odoo(app: &AppHandle, url: &tauri::Url) {
    if odoo::is_unauthenticated_path(url.path()) {
        set_signed_out(app);
        return;
    }

    let Some(odoo_wv) = app.get_webview(ODOO_LABEL) else { return };
    let cookies = match odoo_wv.cookies() {
        Ok(c) => c,
        Err(e) => {
            tracing::warn!(error = %e, "could not read odoo webview cookies");
            return;
        }
    };
    let Some(session_id) = cookies
        .into_iter()
        .find(|c| c.name() == "session_id")
        .map(|c| c.value().to_string())
    else {
        set_signed_out(app);
        return;
    };

    let Some(session) = odoo::fetch_session_info(&session_id).await else {
        set_signed_out(app);
        return;
    };

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
        open_menu(app);
    }

    let _ = app.emit_to(
        SHELL_LABEL,
        "deployguard://session-changed",
        SessionEvent::SignedIn { session, auto_reveal },
    );
}

fn set_signed_out(app: &AppHandle) {
    let state = app.state::<AppState>();
    let mut session = state.session.lock().unwrap();
    if session.is_some() {
        *session = None;
        *state.session_cookie.lock().unwrap() = None;
        *state.has_auto_revealed.lock().unwrap() = false;
        drop(session);
        let _ = app.emit_to(SHELL_LABEL, "deployguard://session-changed", SessionEvent::SignedOut);
    }
}

fn apply_shell_bounds(app: &AppHandle, menu_open: bool) {
    let Some(window) = app.get_window(WINDOW_LABEL) else { return };
    let Ok(size) = window.inner_size() else { return };
    let Ok(scale) = window.scale_factor() else { return };
    let logical: tauri::LogicalSize<f64> = size.to_logical(scale);
    let (pos, size) = shell_bounds(logical.width, logical.height, menu_open);
    if let Some(shell_wv) = app.get_webview(SHELL_LABEL) {
        let _ = shell_wv.set_position(pos);
        let _ = shell_wv.set_size(size);
    }
    *app.state::<AppState>().overlay_expanded.lock().unwrap() = menu_open;
}

pub fn open_menu(app: &AppHandle) {
    apply_shell_bounds(app, true);
}

pub fn close_menu(app: &AppHandle) {
    apply_shell_bounds(app, false);
}

pub fn navigate_odoo(app: &AppHandle, path: &str) -> Result<(), AppError> {
    let base_url = crate::config::odoo_base_url();
    let target = format!("{base_url}{path}");
    let url: tauri::Url = target.parse().map_err(|_| AppError::Unknown)?;
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

pub async fn sign_out(app: &AppHandle) {
    let state: State<AppState> = app.state();
    let cookie = state.session_cookie.lock().unwrap().clone();
    if let Some(session_id) = cookie {
        odoo::destroy_session(&session_id).await;
    }
    set_signed_out(app);
    let _ = navigate_odoo(app, "/web/login");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shell_bounds_collapsed_is_full_width_toolbar_strip() {
        let (pos, size) = shell_bounds(1280.0, 860.0, false);
        assert_eq!(pos, LogicalPosition::new(0.0, 0.0));
        assert_eq!(size, LogicalSize::new(1280.0, TOOLBAR_HEIGHT));
    }

    #[test]
    fn shell_bounds_menu_open_grows_downward_capped_to_window() {
        let (pos, size) = shell_bounds(1280.0, 860.0, true);
        assert_eq!(pos, LogicalPosition::new(0.0, 0.0));
        assert_eq!(size, LogicalSize::new(1280.0, TOOLBAR_HEIGHT + MEGA_MENU_HEIGHT));

        // A short window: the menu must never exceed the window height.
        let (_, short_size) = shell_bounds(1280.0, 300.0, true);
        assert_eq!(short_size.height, 300.0);
    }

    #[test]
    fn odoo_bounds_sits_below_the_toolbar() {
        let (pos, size) = odoo_bounds(1280.0, 860.0);
        assert_eq!(pos, LogicalPosition::new(0.0, TOOLBAR_HEIGHT));
        assert_eq!(size, LogicalSize::new(1280.0, 860.0 - TOOLBAR_HEIGHT));
    }

    #[test]
    fn odoo_bounds_never_negative_height_when_window_shorter_than_toolbar() {
        let (_, size) = odoo_bounds(1280.0, 20.0);
        assert_eq!(size.height, 0.0);
    }
}
