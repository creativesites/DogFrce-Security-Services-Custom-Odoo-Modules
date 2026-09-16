mod commands;
mod config;
mod connectivity;
mod diagnostics;
mod errors;
mod odoo;
mod state;
mod windowing;

use state::AppState;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tracing_subscriber::fmt()
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    tauri::Builder::default()
        .plugin(tauri_plugin_os::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_process::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(AppState::default())
        .setup(|app| {
            windowing::build(app.handle())?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_current_session,
            commands::get_app_view_open,
            commands::auth_sign_out,
            commands::app_view_open,
            commands::app_view_close,
            commands::navigate_odoo,
            commands::odoo_call_kw,
            commands::odoo_back,
            commands::odoo_forward,
            commands::odoo_reload,
            commands::window_minimize,
            commands::window_toggle_maximize,
            commands::window_close,
            commands::connectivity_check,
            commands::diagnostics_get,
        ])
        .run(tauri::generate_context!())
        .expect("error while running DeployGuard desktop");
}
