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
    pub generated_at: String,
}

pub async fn collect(signed_in: bool) -> Diagnostics {
    Diagnostics {
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        os: tauri_plugin_os::type_().to_string(),
        os_version: tauri_plugin_os::version().to_string(),
        odoo_base_url: crate::config::odoo_base_url(),
        odoo_reachable: odoo::health_check().await,
        signed_in,
        generated_at: chrono::Utc::now().to_rfc3339(),
    }
}
