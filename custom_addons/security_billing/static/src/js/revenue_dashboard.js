/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class RevenueDashboard extends Component {
    static template = "security_billing.RevenueDashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            data: null,
        });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "security.billing.invoice",
                "get_revenue_dashboard_data",
                [],
                {}
            );
            this.state.data = data;
        } catch (e) {
            console.error("Revenue dashboard load failed", e);
            this.state.data = null;
        } finally {
            this.state.loading = false;
        }
    }

    get kpis() {
        const d = this.state.data;
        if (!d) return [];
        const sym = d.currency_symbol || "N$";
        return [
            {
                label: "Approved Billing (MTD)",
                value: `${sym} ${this._fmt(d.mtd_approved_billing)}`,
                icon: "fa-check-circle",
                cls: "rd-kpi-green",
                help: "Sum of billable hours × contract rates for approved attendance this month",
            },
            {
                label: "Invoiced (MTD)",
                value: `${sym} ${this._fmt(d.invoiced_mtd)}`,
                icon: "fa-file-text",
                cls: "rd-kpi-blue",
                help: "Total sent/paid invoices issued this month",
            },
            {
                label: "Collected (MTD)",
                value: `${sym} ${this._fmt(d.paid_mtd)}`,
                icon: "fa-money",
                cls: "rd-kpi-teal",
                help: "Payments received this month",
            },
            {
                label: "Outstanding",
                value: `${sym} ${this._fmt(d.outstanding)}`,
                icon: "fa-exclamation-circle",
                cls: d.outstanding > 0 ? "rd-kpi-amber" : "rd-kpi-green",
                help: "All-time invoiced minus collected",
            },
            {
                label: "Exception Queue",
                value: `${d.pending_approval_count} pending`,
                subvalue: `${d.exception_count} total`,
                icon: "fa-warning",
                cls: d.pending_approval_count > 0 ? "rd-kpi-red" : "rd-kpi-green",
                action: "exception_queue",
                help: "Attendance records with exceptions requiring billing approval",
            },
        ];
    }

    get chartBars() {
        const trend = this.state.data?.monthly_trend || [];
        if (!trend.length) return [];
        const maxAmt = Math.max(...trend.map((t) => t.amount), 1);
        return trend.map((t) => ({
            month: t.month,
            amount: t.amount,
            paid: t.paid,
            heightPct: Math.round((t.amount / maxAmt) * 100),
            paidPct: Math.round((t.paid / maxAmt) * 100),
            label: `${this.state.data.currency_symbol} ${this._fmt(t.amount)}`,
        }));
    }

    _fmt(n) {
        if (!n && n !== 0) return "0.00";
        return Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    async onKpiClick(kpi) {
        if (kpi.action === "exception_queue") {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "security.attendance.record",
                name: "Billing Exception Queue",
                view_mode: "list,form",
                domain: [["has_billing_exception", "=", true]],
                context: { search_default_filter_pending_approval: 1 },
                views: [[false, "list"], [false, "form"]],
            });
        }
    }

    async onNavigate(target) {
        const actions = {
            invoices: "security_billing.action_security_billing_invoice",
            generate: "security_billing.action_security_contract_invoice_wizard",
        };
        if (actions[target]) {
            await this.action.doAction(actions[target]);
        }
    }

    async refresh() {
        await this._loadData();
    }
}

registry.category("actions").add("security_billing.revenue_dashboard", RevenueDashboard);

export { RevenueDashboard };
