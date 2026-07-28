/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class BillingCommandCenter extends Component {
    static template = "security_billing.BillingCommandCenter";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            data: null,
            activeTab: "overview",
            modeFilter: "all",
            searchQuery: "",
            isGenerating: false,
        });

        onWillStart(() => this._load());
    }

    async _load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("security.billing.dashboard", "get_dashboard_data", []);
            if (data) {
                data.mode_counts = data.mode_counts || { recurring: 0, shift: 0, adhoc: 0 };
                data.aging = data.aging || { "0_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0 };
                data.high_risk_clients = data.high_risk_clients || [];
                data.plans = data.plans || [];
                data.recent_invoices = data.recent_invoices || [];
            }
            this.state.data = data;
        } catch (e) {
            console.error("Failed to load Billing Command Center data", e);
        } finally {
            this.state.loading = false;
        }
    }

    fmt(amount) {
        const sym = (this.state.data && this.state.data.currency_symbol) || "ZMW";
        return `${sym} ` + (amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    stateLabel(state) {
        return { draft: "Draft", sent: "Sent", paid: "Paid", cancelled: "Cancelled" }[state] || state;
    }

    stateBadgeClass(state) {
        return {
            draft: "bcc-badge bcc-badge-draft",
            sent: "bcc-badge bcc-badge-sent",
            paid: "bcc-badge bcc-badge-paid",
            cancelled: "bcc-badge bcc-badge-cancelled",
        }[state] || "bcc-badge bcc-badge-draft";
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    setModeFilter(mode) {
        this.state.modeFilter = mode;
    }

    get filteredPlans() {
        if (!this.state.data || !this.state.data.plans) return [];
        let plans = this.state.data.plans;

        if (this.state.modeFilter !== "all") {
            plans = plans.filter(p => p.mode_key === this.state.modeFilter);
        }

        if (this.state.searchQuery.trim()) {
            const q = this.state.searchQuery.toLowerCase();
            plans = plans.filter(p =>
                (p.name && p.name.toLowerCase().includes(q)) ||
                (p.client && p.client.toLowerCase().includes(q))
            );
        }

        return plans;
    }

    get filteredInvoices() {
        if (!this.state.data || !this.state.data.recent_invoices) return [];
        let invoices = this.state.data.recent_invoices;

        if (this.state.searchQuery.trim()) {
            const q = this.state.searchQuery.toLowerCase();
            invoices = invoices.filter(i =>
                (i.name && i.name.toLowerCase().includes(q)) ||
                (i.client && i.client.toLowerCase().includes(q))
            );
        }

        return invoices;
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
        if (!id) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.billing.plan",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openPartner(partnerId) {
        if (!partnerId) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: partnerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openNewInvoice() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.billing.invoice",
            views: [[false, "form"]],
            target: "current",
        });
    }

    openWizard() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.contract.invoice.wizard",
            views: [[false, "form"]],
            target: "new",
        });
    }

    openDocumentDesigner() {
        this.actionService.doAction("security_billing.action_document_designer");
    }

    openAllInvoices() {
        this.actionService.doAction("security_billing.action_security_billing_invoice");
    }

    async runAutoBilling() {
        this.state.isGenerating = true;
        try {
            await this.orm.call("security.billing.plan", "action_auto_invoice_all", []);
            this.notification.add("Auto-billing process executed successfully. New draft invoices created.", {
                type: "success",
            });
            await this._load();
        } catch (e) {
            this.notification.add("Failed to run auto-billing batch process.", {
                type: "danger",
            });
        } finally {
            this.state.isGenerating = false;
        }
    }
}

registry.category("actions").add("security_billing.billing_command_center", BillingCommandCenter);
