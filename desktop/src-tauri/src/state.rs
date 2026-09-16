//! Shared, in-process application state.
//!
//! There is deliberately no persisted "we logged the user in" state
//! anymore (see DEVIATIONS.md D-1 update): authentication happens entirely
//! inside Odoo's own login page, rendered in the "odoo" webview, and Odoo's
//! own persistent cookie store (kept by WebView2 / WKWebView across app
//! restarts, exactly like a normal browser) is what makes "stay signed in"
//! work. This state is just an in-memory cache of what we last observed.

use serde::Serialize;
use std::sync::Mutex;

#[derive(Debug, Clone, Serialize)]
pub struct SessionInfo {
    pub uid: i64,
    pub login: String,
    pub name: String,
    pub db: String,
}

#[derive(Default)]
pub struct AppState {
    pub session: Mutex<Option<SessionInfo>>,
    /// The raw Odoo `session_id` cookie value, used only server-side (Rust)
    /// to call `/web/session/destroy` on sign-out. Never sent over IPC.
    pub(crate) session_cookie: Mutex<Option<String>>,
    pub overlay_expanded: Mutex<bool>,
    /// True once we've auto-revealed the DeployGuard overlay for the
    /// current signed-in session, so we don't pop it open again on every
    /// Odoo page navigation — only on the None → Some transition.
    pub(crate) has_auto_revealed: Mutex<bool>,
}
