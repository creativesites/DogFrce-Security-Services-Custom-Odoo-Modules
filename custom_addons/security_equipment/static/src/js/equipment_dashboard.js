/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class EquipmentDashboard extends Component {
    static template = "security_equipment.EquipmentDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ loading: true, data: null });
        onWillStart(() => this._load());
    }

    async _load() {
        const data = await this.orm.call("security.equipment.dashboard", "get_dashboard_data", []);
        this.state.data = data;
        this.state.loading = false;
    }

    openAllocations() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.equipment.allocation",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [["state", "in", ["issued", "acknowledged"]]],
        });
    }

    openOverdue() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.equipment.allocation",
            views: [[false, "list"], [false, "form"]],
            target: "current",
            domain: [["state", "in", ["issued", "acknowledged"]], ["expected_return_date", "<", new Date().toISOString().slice(0, 10)]],
        });
    }

    openDamages() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.equipment.damage",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    severityColor(daysOverdue) {
        if (daysOverdue > 60) return "text-danger fw-bold";
        if (daysOverdue > 30) return "text-warning fw-semibold";
        return "text-muted";
    }
}

registry.category("actions").add("security_equipment.equipment_dashboard", EquipmentDashboard);
