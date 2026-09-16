//! Runtime configuration boundary (Rust side).
//!
//! Mirrors `desktop/src/config/env.ts`. Nothing secret lives here — only
//! non-secret endpoint configuration. Overridable via environment variable
//! for CI/staging builds without recompiling; falls back to a compiled-in
//! default baked at build time (see desktop/.github or CI docs), and
//! finally to a safe localhost default for plain `cargo run` during
//! development.
//!
//! See docs/deployguard/17-desktop-architecture.md and
//! desktop/DEVIATIONS.md for why this talks to Odoo directly in the MVP.

pub fn odoo_base_url() -> String {
    if let Ok(v) = std::env::var("DEPLOYGUARD_ODOO_BASE_URL") {
        if !v.trim().is_empty() {
            return v.trim_end_matches('/').to_string();
        }
    }
    option_env!("DEPLOYGUARD_ODOO_BASE_URL")
        .filter(|v| !v.is_empty())
        .unwrap_or("http://localhost:8069")
        .trim_end_matches('/')
        .to_string()
}
