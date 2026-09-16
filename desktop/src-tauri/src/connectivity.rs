//! Reports why something might not be working, honestly (mission spec §7).

use crate::odoo;
use serde::Serialize;

#[derive(Debug, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum ConnectivityState {
    Online,
    OdooUnreachable,
    /// Reserved: distinguishing "no network at all" from "Odoo specifically
    /// unreachable" needs a network-level check this MVP doesn't add (see
    /// the comment in `check()` below). Kept so the frontend's richer
    /// `ConnectivityState` type (src/lib/connectivity.ts) stays honest
    /// about what's actually implemented vs. planned.
    #[allow(dead_code)]
    Offline,
}

#[derive(Debug, Serialize)]
pub struct ConnectivityReport {
    pub state: ConnectivityState,
    pub message: String,
}

pub async fn check() -> ConnectivityReport {
    if odoo::health_check().await {
        ConnectivityReport {
            state: ConnectivityState::Online,
            message: String::new(),
        }
    } else {
        // We can't cheaply distinguish "no internet" from "Odoo is down"
        // without a second, unrelated endpoint — and pinging a third-party
        // host from a customer's machine is unnecessary risk for an MVP.
        // Report the honest, narrower claim we can actually verify.
        ConnectivityReport {
            state: ConnectivityState::OdooUnreachable,
            message: "Can't reach DeployGuard ERP right now.".to_string(),
        }
    }
}
