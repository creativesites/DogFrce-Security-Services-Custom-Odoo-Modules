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

#[cfg(test)]
mod tests {
    use super::odoo_base_url;
    use std::sync::Mutex;

    // `std::env::var`/`set_var` are process-global state. `cargo test` runs
    // tests in parallel threads by default, so every test in this module
    // that touches `DEPLOYGUARD_ODOO_BASE_URL` must hold this lock for its
    // whole body — otherwise two tests can interleave their set/remove
    // calls and both see the wrong value (a classic flaky-test source).
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    const VAR: &str = "DEPLOYGUARD_ODOO_BASE_URL";

    /// Clears the var for the duration of `f`, restoring whatever was
    /// there before (there shouldn't be anything, in a normal `cargo test`
    /// invocation, but this keeps the test hermetic either way).
    fn with_env<T>(value: Option<&str>, f: impl FnOnce() -> T) -> T {
        let _guard = ENV_LOCK.lock().unwrap_or_else(|e| e.into_inner());
        let previous = std::env::var(VAR).ok();
        match value {
            Some(v) => std::env::set_var(VAR, v),
            None => std::env::remove_var(VAR),
        }
        let result = f();
        match previous {
            Some(v) => std::env::set_var(VAR, v),
            None => std::env::remove_var(VAR),
        }
        result
    }

    #[test]
    fn env_var_takes_precedence_over_default() {
        with_env(Some("https://staging.example.com"), || {
            assert_eq!(odoo_base_url(), "https://staging.example.com");
        });
    }

    #[test]
    fn env_var_trailing_slash_is_stripped() {
        with_env(Some("https://staging.example.com/"), || {
            assert_eq!(odoo_base_url(), "https://staging.example.com");
        });
    }

    #[test]
    fn env_var_multiple_trailing_slashes_all_stripped() {
        with_env(Some("https://staging.example.com///"), || {
            assert_eq!(odoo_base_url(), "https://staging.example.com");
        });
    }

    #[test]
    fn env_var_whitespace_only_is_treated_as_unset() {
        // Falls through to the compile-time default / localhost fallback,
        // not an empty string or a URL with leading/trailing spaces baked
        // in — a blank env var (e.g. from an empty CI secret) must not
        // silently become "the base URL is empty".
        with_env(Some("   "), || {
            let result = odoo_base_url();
            assert!(!result.trim().is_empty());
            assert_ne!(result, "   ");
        });
    }

    #[test]
    fn env_var_unset_falls_back_to_compiled_default_or_localhost() {
        // This binary is compiled in this dev/CI environment without
        // DEPLOYGUARD_ODOO_BASE_URL baked in via option_env!, so with the
        // runtime env var also cleared, the only remaining fallback is the
        // hardcoded "http://localhost:8069" default.
        with_env(None, || {
            assert_eq!(odoo_base_url(), "http://localhost:8069");
        });
    }

    #[test]
    fn env_var_without_trailing_slash_is_unchanged() {
        with_env(Some("http://localhost:9000"), || {
            assert_eq!(odoo_base_url(), "http://localhost:9000");
        });
    }

    #[test]
    fn env_var_with_path_segment_keeps_path_strips_trailing_slash() {
        with_env(Some("https://example.com/odoo/"), || {
            assert_eq!(odoo_base_url(), "https://example.com/odoo");
        });
    }
}
