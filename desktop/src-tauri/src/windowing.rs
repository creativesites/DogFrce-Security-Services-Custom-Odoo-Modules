//! Builds the single application window and its two child webviews.
//!
//! Architecture (per user direction, 2026-09-15 — supersedes the earlier
//! separate-window design; see DEVIATIONS.md D-2):
//!
//!   ┌────────────────────────────────────────────────────────┐
//!   │ window "main"                                           │
//!   │ ┌────┐                                                  │
//!   │ │[DG]│  ← "shell" webview: DeployGuard overlay.          │
//!   │ └────┘    Collapsed to a small corner handle by default; │
//!   │           expands to a full sidebar on hover/click.      │
//!   │                                                          │
//!   │   (rest of the window: "odoo" webview, Odoo's own UI,    │
//!   │    filling the entire window underneath/behind the       │
//!   │    handle — this is the PRIMARY content the user works   │
//!   │    in all day.)                                          │
//!   └────────────────────────────────────────────────────────┘
//!
//! Security model (unchanged in spirit from the previous design,
//! docs/deployguard/16-security-architecture.md §7): the "odoo" webview
//! gets ZERO Tauri IPC capabilities (see capabilities/main.json, scoped by
//! `"webviews": ["shell"]`, not by window). No script is injected into it.
//! We only ever READ its cookies (`Webview::cookies()`) after it navigates
//! somewhere that isn't a login/signup page — we never write to it.

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

/// A floating, always-visible round button — not a flush-corner sliver —
/// per user direction (2026-09-16): it needs to read as a permanent,
/// identifiable control, not something you have to know to hunt for.
const HANDLE_SIZE: f64 = 44.0;
const HANDLE_MARGIN: f64 = 14.0;
const EXPANDED_WIDTH: f64 = 340.0;

/// Both states anchor to the **top-right** corner (per user direction) and
/// are recomputed from the current window size, so the overlay stays
/// pinned there through resizes without drifting.
fn shell_bounds(window_width: f64, window_height: f64, expanded: bool) -> (LogicalPosition<f64>, LogicalSize<f64>) {
    if expanded {
        (
            LogicalPosition::new((window_width - EXPANDED_WIDTH).max(0.0), 0.0),
            LogicalSize::new(EXPANDED_WIDTH.min(window_width), window_height),
        )
    } else {
        (
            LogicalPosition::new((window_width - HANDLE_SIZE - HANDLE_MARGIN).max(0.0), HANDLE_MARGIN),
            LogicalSize::new(HANDLE_SIZE, HANDLE_SIZE),
        )
    }
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

    // "odoo" — fills the entire window. No IPC (see capabilities/main.json).
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

    window.add_child(
        odoo_builder,
        LogicalPosition::new(0.0, 0.0),
        LogicalSize::new(logical.width, logical.height),
    )?;

    // "shell" — the DeployGuard overlay. Full IPC (see capabilities/main.json).
    let (shell_pos, shell_size) = shell_bounds(logical.width, logical.height, false);
    let shell_builder = WebviewBuilder::new(SHELL_LABEL, WebviewUrl::App("index.html".into()));
    window.add_child(shell_builder, shell_pos, shell_size)?;

    // Keep both children sized (and the overlay re-anchored to the
    // top-right corner) as the window is resized.
    let app_handle = app.clone();
    window.on_window_event(move |event| {
        if let tauri::WindowEvent::Resized(size) = event {
            let Some(win) = app_handle.get_window(WINDOW_LABEL) else { return };
            let Ok(scale) = win.scale_factor() else { return };
            let logical: tauri::LogicalSize<f64> = size.to_logical(scale);
            if let Some(odoo_wv) = app_handle.get_webview(ODOO_LABEL) {
                let _ = odoo_wv.set_size(LogicalSize::new(logical.width, logical.height));
            }
            if let Some(shell_wv) = app_handle.get_webview(SHELL_LABEL) {
                let expanded = *app_handle.state::<AppState>().overlay_expanded.lock().unwrap();
                let (pos, size) = shell_bounds(logical.width, logical.height, expanded);
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
        expand_overlay(app);
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

fn apply_shell_bounds(app: &AppHandle, expanded: bool) {
    let Some(window) = app.get_window(WINDOW_LABEL) else { return };
    let Ok(size) = window.inner_size() else { return };
    let Ok(scale) = window.scale_factor() else { return };
    let logical: tauri::LogicalSize<f64> = size.to_logical(scale);
    let (pos, size) = shell_bounds(logical.width, logical.height, expanded);
    if let Some(shell_wv) = app.get_webview(SHELL_LABEL) {
        // Order matters when growing: position before size, so the panel
        // never briefly renders at the old (wrong) x while already wide.
        let _ = shell_wv.set_position(pos);
        let _ = shell_wv.set_size(size);
    }
    *app.state::<AppState>().overlay_expanded.lock().unwrap() = expanded;
}

pub fn expand_overlay(app: &AppHandle) {
    apply_shell_bounds(app, true);
}

pub fn collapse_overlay(app: &AppHandle) {
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

pub async fn sign_out(app: &AppHandle) {
    let state: State<AppState> = app.state();
    let cookie = state.session_cookie.lock().unwrap().clone();
    if let Some(session_id) = cookie {
        odoo::destroy_session(&session_id).await;
    }
    set_signed_out(app);
    let _ = navigate_odoo(app, "/web/login");
}

// ─────────────────────────────────────────────────────────────────────────
// Unit tests for the pure `shell_bounds` geometry function only. Nothing
// else in this file is tested here (everything else needs a live AppHandle
// / webview, which is integration-test territory, not unit-test territory —
// see docs/deployguard/25-testing-strategy.md §1's "Desktop native" row).
// This block is purely additive at the end of the file and does not modify
// any of the code above.
// ─────────────────────────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    /// Typical window size (the default `inner_size` from `build()`).
    #[test]
    fn collapsed_bounds_at_default_window_size() {
        let (pos, size) = shell_bounds(1280.0, 860.0, false);
        assert_eq!(pos.x, 1280.0 - HANDLE_SIZE - HANDLE_MARGIN);
        assert_eq!(pos.y, HANDLE_MARGIN);
        assert_eq!(size.width, HANDLE_SIZE);
        assert_eq!(size.height, HANDLE_SIZE);
    }

    #[test]
    fn expanded_bounds_at_default_window_size() {
        let (pos, size) = shell_bounds(1280.0, 860.0, true);
        assert_eq!(pos.x, 1280.0 - EXPANDED_WIDTH);
        assert_eq!(pos.y, 0.0);
        assert_eq!(size.width, EXPANDED_WIDTH);
        assert_eq!(size.height, 860.0);
    }

    /// The documented minimum window size (`min_inner_size` in `build()`).
    #[test]
    fn collapsed_bounds_at_minimum_window_size() {
        let (pos, size) = shell_bounds(1024.0, 700.0, false);
        assert_eq!(pos.x, 1024.0 - HANDLE_SIZE - HANDLE_MARGIN);
        assert_eq!(pos.y, HANDLE_MARGIN);
        assert_eq!(size.width, HANDLE_SIZE);
        assert_eq!(size.height, HANDLE_SIZE);
    }

    #[test]
    fn expanded_bounds_at_minimum_window_size() {
        let (pos, size) = shell_bounds(1024.0, 700.0, true);
        assert_eq!(pos.x, 1024.0 - EXPANDED_WIDTH);
        assert_eq!(pos.y, 0.0);
        assert_eq!(size.width, EXPANDED_WIDTH);
        assert_eq!(size.height, 700.0);
    }

    /// Below `min_inner_size` shouldn't be reachable in the shipped app
    /// (Tauri enforces the window minimum), but the pure function must
    /// still not panic or produce negative/NaN geometry if ever called
    /// with a narrower width — it should clamp to the window edge.
    #[test]
    fn expanded_bounds_clamp_when_window_narrower_than_panel() {
        let (pos, size) = shell_bounds(300.0, 500.0, true);
        // Position never goes negative: the panel is pinned to x=0 instead
        // of spilling off the left edge of the window.
        assert_eq!(pos.x, 0.0);
        assert_eq!(pos.y, 0.0);
        // Width is clamped to the window's own width, never wider than the
        // window itself.
        assert_eq!(size.width, 300.0);
        assert_eq!(size.height, 500.0);
    }

    /// Symmetric clamp check for the collapsed handle: a window narrower
    /// than the handle + margin must not push the handle to a negative x.
    #[test]
    fn collapsed_bounds_clamp_when_window_narrower_than_handle() {
        let (pos, size) = shell_bounds(50.0, 200.0, false);
        assert_eq!(pos.x, 0.0);
        assert_eq!(pos.y, HANDLE_MARGIN);
        // The handle's own size is fixed regardless of window width — this
        // documents current behavior (it can visually overflow a
        // pathologically narrow window) rather than asserting it's ideal.
        assert_eq!(size.width, HANDLE_SIZE);
        assert_eq!(size.height, HANDLE_SIZE);
    }

    /// A very tall, narrow window: height should pass through unclamped in
    /// both states, confirming height is never touched by the width-based
    /// clamp logic.
    #[test]
    fn expanded_bounds_preserve_tall_window_height() {
        let (pos, size) = shell_bounds(1280.0, 2160.0, true);
        assert_eq!(pos.x, 1280.0 - EXPANDED_WIDTH);
        assert_eq!(size.height, 2160.0);
    }

    /// Exact boundary: window width equals the expanded panel width exactly
    /// — position should sit flush at x=0, not trigger the clamp's `.max`
    /// arm incorrectly.
    #[test]
    fn expanded_bounds_exact_panel_width_window() {
        let (pos, size) = shell_bounds(EXPANDED_WIDTH, 600.0, true);
        assert_eq!(pos.x, 0.0);
        assert_eq!(size.width, EXPANDED_WIDTH);
    }
}
