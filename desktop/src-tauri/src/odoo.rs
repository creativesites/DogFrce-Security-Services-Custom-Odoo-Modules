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

/// Resolves who a session cookie belongs to.
///
/// Returns `Err(reason)` rather than collapsing every failure into `None`
/// -- a "why didn't sign-in work" report is useless without knowing
/// *which* step failed (couldn't reach the server at all vs. reached it
/// and got rejected vs. reached it and the session just isn't signed in).
/// `reason` is safe to show a user or put in diagnostics: it's a network/
/// protocol description, never the cookie value or any credential.
pub async fn fetch_session_info(session_id: &str) -> Result<crate::state::SessionInfo, String> {
    let base_url = config::odoo_base_url();
    let c = client().ok_or_else(|| "could not build an HTTP client".to_string())?;

    let resp = c
        .post(format!("{base_url}/web/session/get_session_info"))
        .header(reqwest::header::COOKIE, format!("session_id={session_id}"))
        .json(&json!({ "jsonrpc": "2.0", "method": "call", "params": {} }))
        .send()
        .await
        .map_err(|e| format!("couldn't reach {base_url}: {e}"))?;

    if !resp.status().is_success() {
        return Err(format!("{base_url} responded with HTTP {}", resp.status()));
    }

    let parsed: JsonRpcResponse<SessionInfoResult> = resp
        .json()
        .await
        .map_err(|e| format!("couldn't parse the response from {base_url}: {e}"))?;
    let result = parsed
        .result
        .ok_or_else(|| "Odoo's response had no result".to_string())?;

    // Odoo represents "not logged in" as uid: false, not a missing field.
    let uid = match result.uid {
        Some(serde_json::Value::Number(n)) => n
            .as_i64()
            .ok_or_else(|| "Odoo returned a non-integer uid".to_string())?,
        _ => return Err("that session isn't signed in (anonymous session)".to_string()),
    };

    Ok(crate::state::SessionInfo {
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

#[derive(Deserialize)]
struct CallKwResponse {
    result: Option<serde_json::Value>,
    error: Option<serde_json::Value>,
}

/// Generic `/web/dataset/call_kw` proxy, used by the "My Work" feature (and
/// any future feature needing standard Odoo model access) instead of a
/// bespoke endpoint per model — `call_kw` already respects the signed-in
/// user's normal ACLs. This is a thin passthrough: the "shell" webview never
/// sees the session cookie itself (D-1/D-2 — it lives only in
/// `AppState.session_cookie`), so the request has to be made from Rust.
pub async fn call_kw(
    session_id: &str,
    model: &str,
    method: &str,
    args: serde_json::Value,
    kwargs: serde_json::Value,
) -> Result<serde_json::Value, crate::errors::AppError> {
    let base_url = config::odoo_base_url();
    let c = client().ok_or(crate::errors::AppError::Unknown)?;

    let resp = c
        .post(format!("{base_url}/web/dataset/call_kw"))
        .header(reqwest::header::COOKIE, format!("session_id={session_id}"))
        .json(&json!({
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs,
            }
        }))
        .send()
        .await?;

    if !resp.status().is_success() {
        return Err(crate::errors::AppError::ServerError);
    }

    let parsed: CallKwResponse = resp.json().await.map_err(|_| crate::errors::AppError::ServerError)?;

    if let Some(err) = parsed.error {
        tracing::warn!(error = %err, model, method, "odoo call_kw returned an error");
        // Odoo's JSON-RPC error shape nests the actual UserError/
        // ValidationError text in error.data.message; error.message is
        // just "Odoo Server Error" and not useful to show. Fall back to
        // the generic message if the shape doesn't match (e.g. a raw
        // traceback with no `data.message`, which we don't want to leak).
        let user_message = err
            .get("data")
            .and_then(|d| d.get("message"))
            .and_then(|m| m.as_str());
        return Err(match user_message {
            Some(message) => crate::errors::AppError::RequestFailed(message.to_string()),
            None => crate::errors::AppError::ServerError,
        });
    }

    parsed.result.ok_or(crate::errors::AppError::ServerError)
}

/// Fetches the signed-in user's Odoo avatar (`res.users.avatar_128`) and
/// returns it as a `data:` URL the frontend can drop straight into an
/// `<img src>` -- same session-cookie-in-Rust reasoning as `call_kw`
/// (D-1/D-2: the "shell" webview never holds the cookie). Returns
/// `Ok(None)` on a non-2xx response or an empty body so the caller can
/// fall back to the initials avatar. Note: a user with no avatar set
/// still gets Odoo's own generic placeholder image back with a 200 --
/// this doesn't try to detect and reject that specifically, so such
/// users will see Odoo's placeholder rather than the initials fallback.
/// Not worth the fragility of fingerprinting a "no avatar" image.
pub async fn fetch_avatar_data_url(session_id: &str, uid: i64) -> Result<Option<String>, crate::errors::AppError> {
    let base_url = config::odoo_base_url();
    let c = client().ok_or(crate::errors::AppError::Unknown)?;

    let resp = c
        .get(format!("{base_url}/web/image/res.users/{uid}/avatar_128"))
        .header(reqwest::header::COOKIE, format!("session_id={session_id}"))
        .send()
        .await?;

    if !resp.status().is_success() {
        return Ok(None);
    }

    let content_type = resp
        .headers()
        .get(reqwest::header::CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or("image/png")
        .to_string();

    let bytes = resp.bytes().await.map_err(|_| crate::errors::AppError::ServerError)?;
    if bytes.is_empty() {
        return Ok(None);
    }

    let encoded = base64::Engine::encode(&base64::engine::general_purpose::STANDARD, &bytes);
    Ok(Some(format!("data:{content_type};base64,{encoded}")))
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

#[cfg(test)]
mod tests {
    use super::is_unauthenticated_path;

    #[test]
    fn exact_login_path_is_unauthenticated() {
        assert!(is_unauthenticated_path("/web/login"));
    }

    #[test]
    fn login_path_with_query_string_is_unauthenticated() {
        // Odoo appends redirect params, e.g. after a session expiry.
        assert!(is_unauthenticated_path("/web/login?redirect=/odoo"));
    }

    #[test]
    fn signup_path_is_unauthenticated() {
        assert!(is_unauthenticated_path("/web/signup"));
    }

    #[test]
    fn reset_password_path_is_unauthenticated() {
        assert!(is_unauthenticated_path("/web/reset_password"));
    }

    #[test]
    fn database_selector_path_is_unauthenticated() {
        assert!(is_unauthenticated_path("/web/database/selector"));
    }

    #[test]
    fn health_check_path_is_unauthenticated() {
        assert!(is_unauthenticated_path("/web/health"));
    }

    #[test]
    fn odoo_app_entry_point_is_authenticated() {
        assert!(!is_unauthenticated_path("/odoo"));
    }

    #[test]
    fn odoo_app_subroute_is_authenticated() {
        assert!(!is_unauthenticated_path("/odoo/attendance"));
    }

    #[test]
    fn web_root_is_authenticated() {
        // "/web" itself (no trailing segment) is the authenticated web
        // client shell, distinct from "/web/login".
        assert!(!is_unauthenticated_path("/web"));
    }

    #[test]
    fn empty_path_is_authenticated() {
        assert!(!is_unauthenticated_path(""));
    }

    #[test]
    fn root_path_is_authenticated() {
        assert!(!is_unauthenticated_path("/"));
    }

    #[test]
    fn path_containing_but_not_starting_with_login_is_authenticated() {
        // A substring match would be wrong here — only a *prefix* match
        // should count, so a record whose path happens to contain
        // "/web/login" partway through must not be misclassified.
        assert!(!is_unauthenticated_path("/odoo/web/login-history"));
    }

    #[test]
    fn case_sensitive_login_path_variant_is_authenticated() {
        // Odoo paths are case-sensitive; a differently-cased path is not
        // one of the known unauthenticated prefixes.
        assert!(!is_unauthenticated_path("/Web/Login"));
    }

    #[test]
    fn login_prefix_with_extra_trailing_segment_is_unauthenticated() {
        assert!(is_unauthenticated_path("/web/login/totp"));
    }
}
