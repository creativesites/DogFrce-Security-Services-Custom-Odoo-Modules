//! The IPC command surface exposed to the "shell" webview ONLY.
//! See capabilities/main.json — the "odoo" webview shares the same window
//! but has none of these.

use crate::state::{AppState, SessionInfo};
use crate::{connectivity, diagnostics, windowing};
use tauri::{AppHandle, State};

#[tauri::command]
pub fn get_current_session(state: State<AppState>) -> Option<SessionInfo> {
    state.session.lock().unwrap().clone()
}

/// Lets the "shell" webview's React state resync with the *actual* native
/// webview size on mount — including after a dev-server HMR reload, which
/// resets React state but not the native bounds Rust already set. Without
/// this, an auto-reveal (see windowing::open_menu) that happens to race a
/// reload leaves the native webview big while React renders the toolbar
/// only, or vice versa.
#[tauri::command]
pub fn get_menu_open(state: State<AppState>) -> bool {
    *state.overlay_expanded.lock().unwrap()
}

#[tauri::command]
pub async fn auth_sign_out(app: AppHandle) {
    windowing::sign_out(&app).await;
}

#[tauri::command]
pub fn menu_open(app: AppHandle) {
    windowing::open_menu(&app);
}

#[tauri::command]
pub fn menu_close(app: AppHandle) {
    windowing::close_menu(&app);
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
pub async fn connectivity_check() -> connectivity::ConnectivityReport {
    connectivity::check().await
}

#[tauri::command]
pub async fn diagnostics_get(state: State<'_, AppState>) -> Result<diagnostics::Diagnostics, ()> {
    let signed_in = state.session.lock().unwrap().is_some();
    Ok(diagnostics::collect(signed_in).await)
}
