use serde::ser::SerializeStruct;
use serde::Serialize;

/// Structured errors surfaced to the frontend. Never carries a credential,
/// token or cookie value (mission spec §8, §21, §22).
///
/// Serialised as `{ "kind": "<snake_case>", "message": "<human text>" }` for
/// **every** variant. An earlier `#[serde(tag, content)]` derive dropped
/// `message` for unit variants, so the UI only ever saw its own generic
/// fallbacks. See `serialises_every_variant_with_a_message` below.
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("Can't reach DogForce ERP. Check your connection.")]
    NetworkUnreachable,
    #[error("DogForce ERP returned an unexpected error.")]
    ServerError,
    #[error("Your session has expired. Please sign in to continue.")]
    SessionExpired,
    /// The model a call targets isn't installed on this Odoo server. Odoo 19
    /// answers that with werkzeug's NotFound before dispatch, so it arrives
    /// as a "404 Not Found" -- telling it apart lets the app hide a screen
    /// instead of showing a raw 404.
    #[error("This feature isn't installed on DogForce ERP yet.")]
    ModuleNotInstalled,
    /// The desktop refused to proxy a call (see guard.rs). Not an Odoo access
    /// error -- Odoo never saw the request.
    #[error("DeployGuard can't do that from here. Open DogForce ERP to do it directly.")]
    NotAllowed,
    /// An Odoo-side validation/business-rule message (e.g. a UserError
    /// raised by a model method) — safe to show verbatim, it's
    /// domain-logic text the same user would see inside Odoo itself,
    /// never a credential/token/cookie.
    #[error("{0}")]
    RequestFailed(String),
    #[error("Something went wrong. Try again.")]
    Unknown,
}

impl AppError {
    pub fn kind(&self) -> &'static str {
        match self {
            AppError::NetworkUnreachable => "network_unreachable",
            AppError::ServerError => "server_error",
            AppError::SessionExpired => "session_expired",
            AppError::ModuleNotInstalled => "module_not_installed",
            AppError::NotAllowed => "not_allowed",
            AppError::RequestFailed(_) => "request_failed",
            AppError::Unknown => "unknown",
        }
    }
}

impl Serialize for AppError {
    fn serialize<S: serde::Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        let mut s = serializer.serialize_struct("AppError", 2)?;
        s.serialize_field("kind", self.kind())?;
        s.serialize_field("message", &self.to_string())?;
        s.end()
    }
}

impl From<reqwest::Error> for AppError {
    fn from(err: reqwest::Error) -> Self {
        if err.is_connect() || err.is_timeout() {
            AppError::NetworkUnreachable
        } else {
            tracing::warn!(error = %err, "odoo request failed");
            AppError::ServerError
        }
    }
}

#[cfg(test)]
mod tests {
    use super::AppError;

    #[test]
    fn serialises_every_variant_with_a_message() {
        let all = [
            AppError::NetworkUnreachable,
            AppError::ServerError,
            AppError::SessionExpired,
            AppError::ModuleNotInstalled,
            AppError::NotAllowed,
            AppError::RequestFailed("No attempts left.".into()),
            AppError::Unknown,
        ];
        for err in all {
            let v = serde_json::to_value(&err).unwrap();
            assert_eq!(v["kind"], err.kind());
            let msg = v["message"].as_str().unwrap();
            assert!(!msg.is_empty(), "{} has an empty message", err.kind());
        }
    }

    #[test]
    fn request_failed_keeps_the_odoo_text() {
        let v = serde_json::to_value(AppError::RequestFailed("No attempts left.".into())).unwrap();
        assert_eq!(
            v,
            serde_json::json!({"kind": "request_failed", "message": "No attempts left."})
        );
    }
}
