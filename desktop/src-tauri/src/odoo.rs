//! DeployGuard ERP (Odoo) integration.
//!
//! MVP DEVIATION (see desktop/DEVIATIONS.md): the "odoo" webview renders
//! Odoo's own `/web/login` page directly — the user authenticates with
//! Odoo's native form, not a DeployGuard-branded one. This module no
//! longer performs the login itself; it only:
//!   - reads back the `session_id` cookie Odoo's own login just set
//!     (via `Webview::cookies()`, called from `windowing.rs` after a page
//!     load that looks like a successful sign-in);
//!   - asks Odoo who that session belongs to (`get_session_info`);
//!   - destroys the session on sign-out.
//!
//! When the DeployGuard Platform bridge (DG-ADR-007) ships, single sign-on
//! is brokered instead of read back from cookies, but the Odoo webview
//! keeps rendering Odoo's own UI either way — only how it gets
//! authenticated changes.

use crate::config;
use serde::Deserialize;
use serde_json::json;

#[derive(Deserialize)]
struct SessionInfoResult {
    uid: Option<serde_json::Value>, // Odoo returns `false` (not null) for an anonymous session
    name: Option<String>,
    username: Option<String>,
    db: Option<String>,
}

#[derive(Deserialize)]
struct JsonRpcResponse<T> {
    result: Option<T>,
    #[allow(dead_code)]
    error: Option<serde_json::Value>,
}

fn client() -> Option<reqwest::Client> {
    reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(10))
        .build()
        .ok()
}

/// Resolves who a session cookie belongs to, or `None` if it's not a
/// signed-in (internal) user's session.
pub async fn fetch_session_info(session_id: &str) -> Option<crate::state::SessionInfo> {
    let base_url = config::odoo_base_url();
    let c = client()?;

    let resp = c
        .post(format!("{base_url}/web/session/get_session_info"))
        .header(reqwest::header::COOKIE, format!("session_id={session_id}"))
        .json(&json!({ "jsonrpc": "2.0", "method": "call", "params": {} }))
        .send()
        .await
        .ok()?;

    if !resp.status().is_success() {
        return None;
    }

    let parsed: JsonRpcResponse<SessionInfoResult> = resp.json().await.ok()?;
    let result = parsed.result?;

    // Odoo represents "not logged in" as uid: false, not a missing field.
    let uid = match result.uid {
        Some(serde_json::Value::Number(n)) => n.as_i64()?,
        _ => return None,
    };

    Some(crate::state::SessionInfo {
        uid,
        login: result.username.clone().unwrap_or_default(),
        name: result.name.unwrap_or_default(),
        db: result.db.unwrap_or_default(),
    })
}

/// Best-effort session destroy. Errors are swallowed — the "odoo" webview
/// is navigated back to the login page regardless, which is what the user
/// actually observes as "signed out".
pub async fn destroy_session(session_id: &str) {
    let base_url = config::odoo_base_url();
    if let Some(c) = client() {
        let _ = c
            .post(format!("{base_url}/web/session/destroy"))
            .header(reqwest::header::COOKIE, format!("session_id={session_id}"))
            .json(&json!({ "jsonrpc": "2.0", "method": "call", "params": {} }))
            .send()
            .await;
    }
}

pub async fn health_check() -> bool {
    let base_url = config::odoo_base_url();
    match client() {
        Some(c) => c
            .get(format!("{base_url}/web/health"))
            .send()
            .await
            .map(|r| r.status().is_success())
            .unwrap_or(false),
        None => false,
    }
}

/// The initial URL loaded in the "odoo" webview. `/odoo` is Odoo 19's web
/// client entry point; an unauthenticated visitor is redirected to
/// `/web/login` by Odoo itself.
pub fn initial_url() -> String {
    format!("{}/odoo", config::odoo_base_url())
}

/// Heuristic: does this path look like a page where the user is NOT yet
/// authenticated (so we should not attempt to read/trust a session
/// cookie yet)? Used by the page-load handler in `windowing.rs`.
pub fn is_unauthenticated_path(path: &str) -> bool {
    const UNAUTH_PREFIXES: &[&str] = &[
        "/web/login",
        "/web/signup",
        "/web/reset_password",
        "/web/database",
        "/web/health",
    ];
    UNAUTH_PREFIXES.iter().any(|p| path.starts_with(p))
}
