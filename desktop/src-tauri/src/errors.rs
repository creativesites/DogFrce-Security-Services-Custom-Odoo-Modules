use serde::Serialize;

/// Structured errors surfaced to the frontend. Never carries a credential,
/// token or cookie value (mission spec §8, §21, §22).
#[derive(Debug, thiserror::Error, Serialize)]
#[serde(tag = "kind", content = "message", rename_all = "snake_case")]
pub enum AppError {
    #[error("Can't reach DeployGuard ERP. Check your connection.")]
    NetworkUnreachable,
    #[error("DeployGuard ERP returned an unexpected error.")]
    ServerError,
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
