//! Reports why something might not be working, honestly (mission spec §7, §18).
//!
//! `auth_expired` and `connecting` are shell-side states (session events and
//! startup). This module distinguishes the two network states it can verify:
//! Odoo answered (`online`), the machine has a network route but Odoo didn't
//! answer (`odoo_unreachable`), or the machine has no route at all (`offline`).

use crate::{config, odoo};
use serde::Serialize;

#[derive(Debug, Serialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum ConnectivityState {
    Online,
    OdooUnreachable,
    Offline,
}

#[derive(Debug, Serialize)]
pub struct ConnectivityReport {
    pub state: ConnectivityState,
    pub message: String,
}

/// Whether the OS has a route towards the Odoo host. A UDP `connect` sends no
/// packets; it only asks the OS routing table, so this never contacts a third
/// party. It fails immediately with "network unreachable" when the machine has
/// no usable network (cable out, Wi-Fi off, airplane mode).
fn has_route_to(host_port: &str) -> bool {
    use std::net::{ToSocketAddrs, UdpSocket};
    let Ok(mut addrs) = host_port.to_socket_addrs() else {
        // DNS failed. With a hostname-based Odoo URL this is the usual
        // offline symptom.
        return false;
    };
    let Some(addr) = addrs.next() else {
        return false;
    };
    let bind = if addr.is_ipv4() {
        "0.0.0.0:0"
    } else {
        "[::]:0"
    };
    UdpSocket::bind(bind).and_then(|s| s.connect(addr)).is_ok()
}

fn odoo_host_port() -> Option<String> {
    let url = url::Url::parse(&config::odoo_base_url()).ok()?;
    let host = url.host_str()?.to_string();
    let port = url.port_or_known_default()?;
    Some(format!("{host}:{port}"))
}

pub fn classify(odoo_answered: bool, has_route: bool) -> ConnectivityReport {
    match (odoo_answered, has_route) {
        (true, _) => ConnectivityReport {
            state: ConnectivityState::Online,
            message: String::new(),
        },
        (false, true) => ConnectivityReport {
            state: ConnectivityState::OdooUnreachable,
            message: "Your network is working, but DogForce ERP isn't answering.".to_string(),
        },
        (false, false) => ConnectivityReport {
            state: ConnectivityState::Offline,
            message: "This computer isn't connected to a network.".to_string(),
        },
    }
}

pub async fn check() -> ConnectivityReport {
    if odoo::health_check().await {
        return classify(true, true);
    }
    let route = match odoo_host_port() {
        Some(hp) => tokio::task::spawn_blocking(move || has_route_to(&hp))
            .await
            .unwrap_or(false),
        None => false,
    };
    classify(false, route)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn odoo_answering_is_online_regardless_of_route_probe() {
        assert_eq!(classify(true, false).state, ConnectivityState::Online);
    }

    #[test]
    fn route_but_no_answer_is_odoo_unreachable() {
        assert_eq!(
            classify(false, true).state,
            ConnectivityState::OdooUnreachable
        );
    }

    #[test]
    fn no_route_is_offline() {
        let r = classify(false, false);
        assert_eq!(r.state, ConnectivityState::Offline);
        assert!(!r.message.is_empty());
    }

    #[test]
    fn serialises_snake_case() {
        assert_eq!(
            serde_json::to_value(ConnectivityState::OdooUnreachable).unwrap(),
            "odoo_unreachable"
        );
    }
}
