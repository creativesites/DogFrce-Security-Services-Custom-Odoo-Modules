/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class BillingCommandCenter extends Component {
    static template = "security_billing.BillingCommandCenter";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ loading: true, data: null });
        onWillStart(() => this._load());
    }

    async _load() {
        const data = await this.orm.call("security.billing.dashboard", "get_dashboard_data", []);
        this.state.data = data;
        this.state.loading = false;
    }

    fmt(amount) {
        return "N$ " + (amount || 0).toLocaleString("en-NA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    stateLabel(state) {
        return { draft: "Draft", sent: "Sent", paid: "Paid", cancelled: "Cancelled" }[state] || state;
    }

    stateBadgeClass(state) {
        return { draft: "badge bg-secondary", sent: "badge bg-primary", paid: "badge bg-success", cancelled: "badge bg-light text-muted" }[state] || "badge bg-secondary";
    }

    openInvoice(id) {
        if (!id) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.billing.invoice",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPlan(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.billing.plan",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllInvoices() {
        this.actionService.doAction("security_billing.action_security_billing_invoice");
    }
}

registry.category("actions").add("security_billing.billing_command_center", BillingCommandCenter);
