//! Non-sensitive diagnostics bundle (mission spec §21).
//!
//! NEVER includes passwords, session cookies, tokens or other secrets —
//! only what's needed to triage "DeployGuard isn't working" reports.

use crate::odoo;
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct Diagnostics {
    pub app_version: String,
    pub os: String,
    pub os_version: String,
    pub odoo_base_url: String,
    pub odoo_reachable: bool,
    pub signed_in: bool,
    /// What happened the last time the app tried to sync the session from
    /// the Odoo webview (e.g. why a login attempt didn't take) -- `None`
    /// if that's never run yet this session. See `state::AppState`.
    pub last_sync_note: Option<String>,
    /// Folder holding the rotating log files (logging.rs); `None` if the
    /// app couldn't create it and is logging to stdout only.
    pub log_dir: Option<String>,
    pub generated_at: String,
}

pub async fn collect(signed_in: bool, last_sync_note: Option<String>, log_dir: Option<String>) -> Diagnostics {
    Diagnostics {
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        os: tauri_plugin_os::type_().to_string(),
        os_version: tauri_plugin_os::version().to_string(),
        odoo_base_url: crate::config::odoo_base_url(),
        odoo_reachable: odoo::health_check().await,
        signed_in,
        last_sync_note,
        log_dir,
        generated_at: chrono::Utc::now().to_rfc3339(),
    }
}
