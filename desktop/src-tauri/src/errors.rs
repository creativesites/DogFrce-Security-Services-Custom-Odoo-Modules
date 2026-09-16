use serde::Serialize;

/// Structured errors surfaced to the frontend. Never carries a credential,
/// token or cookie value (mission spec §8, §21, §22).
#[derive(Debug, thiserror::Error, Serialize)]
#[serde(tag = "kind", content = "message", rename_all = "snake_case")]
pub enum AppError {
    #[error("Can't reach DogForce ERP. Check your connection.")]
    NetworkUnreachable,
    #[error("DogForce ERP returned an unexpected error.")]
    ServerError,
    /// An Odoo-side validation/business-rule message (e.g. a UserError
    /// raised by a model method) — safe to show verbatim, it's
    /// domain-logic text the same user would see inside Odoo itself,
    /// never a credential/token/cookie.
    #[error("{0}")]
    RequestFailed(String),
    #[error("Something went wrong. Try again.")]
    Unknown,
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
