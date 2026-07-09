/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class FleetDashboard extends Component {
    static template = "security_fleet.FleetDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ loading: true, data: null });
        onWillStart(() => this._load());
    }

    async _load() {
        const data = await this.orm.call("security.fleet.dashboard", "get_dashboard_data", []);
        this.state.data = data;
        this.state.loading = false;
    }

    fmt(amount) {
        return "N$ " + (amount || 0).toLocaleString("en-NA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    stateLabel(state) {
        return { available: "Available", in_transit: "In Transit", in_service: "In Service", scrapped: "Scrapped" }[state] || state;
    }

    stateBadgeClass(state) {
        return { available: "badge bg-success", in_transit: "badge bg-primary", in_service: "badge bg-warning text-dark", scrapped: "badge bg-secondary" }[state] || "badge bg-secondary";
    }

    runStateClass(state) {
        return { draft: "badge bg-secondary", boarding: "badge bg-info", in_transit: "badge bg-primary", completed: "badge bg-success", cancelled: "badge bg-light text-muted" }[state] || "badge bg-secondary";
    }

    openVehicle(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.vehicle",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRun(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.shuttle.run",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("security_fleet.fleet_dashboard", FleetDashboard);
