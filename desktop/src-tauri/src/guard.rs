//! Pure validation for everything that crosses from the "shell" webview, or
//! from Odoo page content, into a native action: where the "odoo" webview may
//! navigate, which URL `navigate_odoo` may build, and which model/method
//! `odoo_call_kw` may proxy.
//!
//! None of this replaces Odoo's own access control. The employee's session and
//! ACLs remain the authority. These checks keep a compromised or buggy page
//! from turning the native layer into something broader than "this employee,
//! talking to this Odoo" (docs/deployguard/16-security-architecture.md §7).

use crate::errors::AppError;
use url::Url;

/// True when `candidate` is on the same origin (scheme + host + port) as the
/// configured Odoo base URL. This is the only place the "odoo" webview may
/// navigate to.
pub fn is_odoo_origin(base_url: &str, candidate: &Url) -> bool {
    match Url::parse(base_url) {
        Ok(base) => base.origin() == candidate.origin(),
        Err(_) => false,
    }
}

/// What the "odoo" webview should do with a navigation request.
#[derive(Debug, PartialEq, Eq)]
pub enum NavDecision {
    /// Stay inside the "odoo" webview.
    Allow,
    /// Refuse, and hand the URL to the operating system's default handler
    /// (browser, mail client, phone app).
    OpenExternally,
    /// Refuse outright (javascript:, file:, data:, unknown schemes).
    Block,
}

pub fn navigation_decision(base_url: &str, url: &Url) -> NavDecision {
    if is_odoo_origin(base_url, url) {
        return NavDecision::Allow;
    }
    match url.scheme() {
        // Odoo uses these for downloads and blank frames. They don't leave the
        // page's own origin.
        "about" | "blob" => NavDecision::Allow,
        "http" | "https" | "mailto" | "tel" => NavDecision::OpenExternally,
        _ => NavDecision::Block,
    }
}

/// Builds the URL `navigate_odoo` loads, or `None` if `path` isn't a plain
/// same-origin path. Paths come from the shell and, indirectly, from server
/// data (lesson deep links, exception records), so anything that could change
/// the host is refused. That includes `//evil.com`, `@evil.com`, `\\evil`,
/// absolute URLs and control characters.
pub fn safe_odoo_url(base_url: &str, path: &str) -> Option<Url> {
    if !path.starts_with('/') || path.starts_with("//") {
        return None;
    }
    if path.contains('\\') || path.contains('@') || path.chars().any(|c| c.is_control()) {
        return None;
    }
    let base = Url::parse(base_url).ok()?;
    let joined = base.join(path).ok()?;
    if joined.origin() != base.origin() {
        return None;
    }
    Some(joined)
}

/// Models the desktop has no business calling through the generic proxy, even
/// when the signed-in user is an administrator. The desktop is an employee work
/// tool. Anything touching configuration, code or credentials belongs in Odoo's
/// own UI, where Odoo's audit trail and confirmations apply.
const DENIED_MODEL_PREFIXES: &[&str] = &[
    "ir.",
    "base.",
    "res.config",
    "auth_",
    "auth.",
    "bus.",
    "iap.",
];
const DENIED_MODELS: &[&str] = &[
    "res.users.apikeys",
    "res.users.apikeys.description",
    "res.company",
    "res.groups",
];
/// Allowed *reads* on otherwise-denied models. The shell legitimately looks up
/// attachments and the model registry.
const READ_METHODS: &[&str] = &[
    "fields_get",
    "search_read",
    "read",
    "search_count",
    "read_group",
    "name_search",
];
const READ_ALLOWED_MODELS: &[&str] = &["ir.attachment", "ir.model"];
/// `res.users`: the shell may read the employee's own profile. It may not write
/// users (password, groups, login).
const RES_USERS_WRITE_METHODS: &[&str] = &[
    "write",
    "create",
    "unlink",
    "copy",
    "change_password",
    "preference_change_password",
];

fn is_identifier(s: &str, allow_dot: bool) -> bool {
    let mut chars = s.chars();
    match chars.next() {
        Some(c) if c.is_ascii_lowercase() => {}
        _ => return false,
    }
    s.len() <= 128
        && chars.all(|c| {
            c.is_ascii_lowercase() || c.is_ascii_digit() || c == '_' || (allow_dot && c == '.')
        })
}

pub fn validate_call_kw(model: &str, method: &str) -> Result<(), AppError> {
    // Odoo already refuses underscore-prefixed methods through call_kw. We
    // refuse them one step earlier, together with anything that isn't a plain
    // identifier.
    if !is_identifier(model, true) || !is_identifier(method, false) {
        return Err(AppError::NotAllowed);
    }
    let is_read = READ_METHODS.contains(&method);
    if READ_ALLOWED_MODELS.contains(&model) && is_read {
        return Ok(());
    }
    if DENIED_MODELS.contains(&model) || DENIED_MODEL_PREFIXES.iter().any(|p| model.starts_with(p))
    {
        return Err(AppError::NotAllowed);
    }
    if model == "res.users" && RES_USERS_WRITE_METHODS.contains(&method) {
        return Err(AppError::NotAllowed);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    const BASE: &str = "https://erp.dogforce.example";

    fn u(s: &str) -> Url {
        Url::parse(s).unwrap()
    }

    #[test]
    fn same_origin_navigation_is_allowed() {
        assert_eq!(
            navigation_decision(BASE, &u("https://erp.dogforce.example/odoo/action-1")),
            NavDecision::Allow
        );
    }

    #[test]
    fn different_host_port_or_scheme_is_not_odoo() {
        assert!(!is_odoo_origin(BASE, &u("https://evil.example/odoo")));
        assert!(!is_odoo_origin(
            BASE,
            &u("https://erp.dogforce.example:8443/odoo")
        ));
        assert!(!is_odoo_origin(
            BASE,
            &u("http://erp.dogforce.example/odoo")
        ));
        assert!(!is_odoo_origin(
            BASE,
            &u("https://erp.dogforce.example.evil.com/")
        ));
    }

    #[test]
    fn external_web_and_mail_links_open_in_the_system() {
        assert_eq!(
            navigation_decision(BASE, &u("https://www.google.com/maps")),
            NavDecision::OpenExternally
        );
        assert_eq!(
            navigation_decision(BASE, &u("mailto:ops@dogforce.example")),
            NavDecision::OpenExternally
        );
    }

    #[test]
    fn dangerous_schemes_are_blocked() {
        assert_eq!(
            navigation_decision(BASE, &u("file:///C:/Windows/system32")),
            NavDecision::Block
        );
        assert_eq!(
            navigation_decision(BASE, &u("javascript:alert(1)")),
            NavDecision::Block
        );
        assert_eq!(
            navigation_decision(BASE, &u("data:text/html,hi")),
            NavDecision::Block
        );
    }

    #[test]
    fn blank_and_blob_frames_are_allowed() {
        assert_eq!(
            navigation_decision(BASE, &u("about:blank")),
            NavDecision::Allow
        );
    }

    #[test]
    fn safe_path_joins_on_the_odoo_origin() {
        let url = safe_odoo_url(BASE, "/odoo/action-security_attendance.action_x?debug=0").unwrap();
        assert_eq!(url.host_str(), Some("erp.dogforce.example"));
        assert_eq!(url.path(), "/odoo/action-security_attendance.action_x");
    }

    #[test]
    fn host_changing_paths_are_refused() {
        for bad in [
            "//evil.com/x",
            "@evil.com",
            "/\\evil.com",
            "https://evil.com",
            "evil",
            "/odoo@evil.com",
            "/a\nb",
            "",
        ] {
            assert!(
                safe_odoo_url(BASE, bad).is_none(),
                "{bad:?} should be refused"
            );
        }
    }

    #[test]
    fn normal_models_and_methods_pass() {
        assert!(validate_call_kw("security.work.task", "action_start").is_ok());
        assert!(validate_call_kw("hr.employee", "search_read").is_ok());
        assert!(validate_call_kw("res.users", "read").is_ok());
    }

    #[test]
    fn private_or_malformed_identifiers_are_refused() {
        assert!(validate_call_kw("security.work.task", "_compute_is_overdue").is_err());
        assert!(validate_call_kw("security.work.task", "Action").is_err());
        assert!(validate_call_kw("security work", "read").is_err());
        assert!(validate_call_kw("", "read").is_err());
        assert!(validate_call_kw("x", "read; drop").is_err());
    }

    #[test]
    fn administrative_models_are_refused() {
        assert!(validate_call_kw("ir.config_parameter", "get_param").is_err());
        assert!(validate_call_kw("ir.cron", "method_direct_trigger").is_err());
        assert!(validate_call_kw("res.groups", "write").is_err());
        assert!(validate_call_kw("res.users", "write").is_err());
        assert!(validate_call_kw("res.users.apikeys", "search_read").is_err());
    }

    #[test]
    fn allowlisted_reads_on_ir_models_pass() {
        assert!(validate_call_kw("ir.attachment", "search_read").is_ok());
        assert!(validate_call_kw("ir.attachment", "unlink").is_err());
    }
}
