//! The IPC command surface exposed to the "shell" webview ONLY.
//! See capabilities/main.json — the "odoo" webview shares the same window
//! but has none of these.

use crate::errors::AppError;
use crate::state::{AppState, SessionInfo};
use crate::{connectivity, diagnostics, odoo, windowing};
use tauri::{AppHandle, State};

#[tauri::command]
pub fn get_current_session(state: State<AppState>) -> Option<SessionInfo> {
    state.session.lock().unwrap().clone()
}

/// Lets the "shell" webview's React state resync with the *actual* native
/// webview size on mount — including after a dev-server HMR reload, which
/// resets React state but not the native bounds Rust already set. Without
/// this, an auto-reveal (see windowing::open_app_view) that happens to race a
/// reload leaves the native webview big while React renders the toolbar
/// only, or vice versa.
#[tauri::command]
pub fn get_app_view_open(state: State<AppState>) -> bool {
    *state.overlay_expanded.lock().unwrap()
}

#[tauri::command]
pub async fn auth_sign_out(app: AppHandle) {
    windowing::sign_out(&app).await;
}

#[tauri::command]
pub fn app_view_open(app: AppHandle) {
    windowing::open_app_view(&app);
}

#[tauri::command]
pub fn app_view_close(app: AppHandle) {
    windowing::close_app_view(&app);
}

#[tauri::command]
pub fn navigate_odoo(app: AppHandle, path: Option<String>) -> Result<(), String> {
    windowing::navigate_odoo(&app, path.as_deref().unwrap_or("/odoo")).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn odoo_back(app: AppHandle) -> Result<(), String> {
    windowing::odoo_history_back(&app).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn odoo_forward(app: AppHandle) -> Result<(), String> {
    windowing::odoo_history_forward(&app).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn odoo_reload(app: AppHandle) -> Result<(), String> {
    windowing::odoo_reload(&app).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn window_minimize(app: AppHandle) -> Result<(), String> {
    windowing::window_minimize(&app).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn window_toggle_maximize(app: AppHandle) -> Result<(), String> {
    windowing::window_toggle_maximize(&app).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn window_close(app: AppHandle) -> Result<(), String> {
    windowing::window_close(&app).map_err(|e| e.to_string())
}

/// Generic Odoo `call_kw` proxy for the "shell" webview (see odoo.rs's
/// `call_kw` doc comment for why this has to be a Rust hop rather than a
/// direct fetch from React). Scoped to whatever ACLs the signed-in user's
/// session already has — no elevated access, no bespoke per-feature
/// endpoint. Used by My Work today; any future feature needing standard
/// Odoo model reads/writes can reuse it rather than growing a new command.
#[tauri::command]
pub async fn odoo_call_kw(
    state: State<'_, AppState>,
    model: String,
    method: String,
    args: serde_json::Value,
    kwargs: serde_json::Value,
) -> Result<serde_json::Value, AppError> {
    let session_id = state
        .session_cookie
        .lock()
        .unwrap()
        .clone()
        .ok_or(AppError::SessionExpired)?;
    odoo::call_kw(&session_id, &model, &method, args, kwargs).await
}

/// Fetches the signed-in user's Odoo avatar as a `data:` URL. The
/// frontend is responsible for caching it (localStorage, keyed by uid) --
/// this command always does a real fetch, it doesn't cache on the Rust
/// side.
#[tauri::command]
pub async fn odoo_fetch_avatar(state: State<'_, AppState>) -> Result<Option<String>, AppError> {
    let session_id = state
        .session_cookie
        .lock()
        .unwrap()
        .clone()
        .ok_or(AppError::SessionExpired)?;
    let uid = state
        .session
        .lock()
        .unwrap()
        .as_ref()
        .map(|s| s.uid)
        .ok_or(AppError::Unknown)?;
    odoo::fetch_avatar_data_url(&session_id, uid).await
}

#[tauri::command]
pub async fn connectivity_check() -> connectivity::ConnectivityReport {
    connectivity::check().await
}

#[tauri::command]
pub async fn diagnostics_get(state: State<'_, AppState>) -> Result<diagnostics::Diagnostics, ()> {
    let signed_in = state.session.lock().unwrap().is_some();
    let last_sync_note = state.last_sync_note.lock().unwrap().clone();
    Ok(diagnostics::collect(signed_in, last_sync_note).await)
}
