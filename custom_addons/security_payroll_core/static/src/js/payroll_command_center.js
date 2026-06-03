/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PayrollCommandCenter extends Component {
    static template = "security_payroll_core.PayrollCommandCenter";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            periods: [],
            selectedPeriodId: null,
            payslips: [],
            stats: {
                total: 0,
                draft: 0,
                confirmed: 0,
                paid: 0,
                anomalyCount: 0,
                totalGross: 0,
                totalNet: 0,
                totalDeductions: 0,
            },
            activeTab: "overview",
        });

        onWillStart(async () => {
            await this._loadPeriods();
        });
    }

    // ── Computed getters ────────────────────────────────────────────────────

    get anomalyPayslips() {
        return this.state.payslips.filter((p) => (p.anomaly_score || 0) > 0);
    }

    get draftPayslips() {
        return this.state.payslips.filter((p) => p.state === "draft");
    }

    get confirmedPayslips() {
        return this.state.payslips.filter((p) => p.state === "confirmed");
    }

    get paidPayslips() {
        return this.state.payslips.filter((p) => p.state === "paid");
    }

    get selectedPeriod() {
        return this.state.periods.find((p) => p.id === this.state.selectedPeriodId) || null;
    }

    // ── Data loading ────────────────────────────────────────────────────────

    async _loadPeriods() {
        this.state.loading = true;
        try {
            const periods = await this.orm.searchRead(
                "security.payroll.period",
                [],
                ["name", "state", "date_from", "date_to", "total_net_pay", "payslip_count"],
                { order: "date_from desc", limit: 6 }
            );
            this.state.periods = periods;

            // Auto-select the first (most recent) period
            if (periods.length > 0 && !this.state.selectedPeriodId) {
                await this.selectPeriod(periods[0].id);
            } else {
                this.state.loading = false;
            }
        } catch (error) {
            this.notification.add("Failed to load payroll periods.", {
                type: "warning",
                title: "Load Error",
            });
            console.error("PayrollCommandCenter._loadPeriods error:", error);
            this.state.loading = false;
        }
    }

    async _loadPayslips(periodId) {
        if (!periodId) {
            this.state.payslips = [];
            this._computeStats([]);
            return;
        }
        try {
            const payslips = await this.orm.searchRead(
                "security.payslip",
                [["period_id", "=", periodId]],
                [
                    "name",
                    "employee_id",
                    "state",
                    "total_earnings",
                    "total_deductions",
                    "net_pay",
                    "anomaly_score",
                    "anomaly_flags",
                    "worked_days",
                ],
                { order: "employee_id asc" }
            );
            this.state.payslips = payslips;
            this._computeStats(payslips);
        } catch (error) {
            this.notification.add("Failed to load payslips for this period.", {
                type: "warning",
                title: "Load Error",
            });
            console.error("PayrollCommandCenter._loadPayslips error:", error);
            this.state.payslips = [];
            this._computeStats([]);
        }
    }

    _computeStats(payslips) {
        const stats = {
            total: payslips.length,
            draft: 0,
            confirmed: 0,
            paid: 0,
            anomalyCount: 0,
            totalGross: 0,
            totalNet: 0,
            totalDeductions: 0,
        };
        for (const ps of payslips) {
            if (ps.state === "draft") stats.draft++;
            else if (ps.state === "confirmed") stats.confirmed++;
            else if (ps.state === "paid") stats.paid++;
            if ((ps.anomaly_score || 0) > 0) stats.anomalyCount++;
            stats.totalGross += ps.total_earnings || 0;
            stats.totalNet += ps.net_pay || 0;
            stats.totalDeductions += ps.total_deductions || 0;
        }
        this.state.stats = stats;
    }

    // ── Actions ─────────────────────────────────────────────────────────────

    async selectPeriod(id) {
        this.state.selectedPeriodId = id;
        this.state.loading = true;
        await this._loadPayslips(id);
        this.state.loading = false;
    }

    async bulkConfirm() {
        const draftIds = this.draftPayslips.map((p) => p.id);
        if (draftIds.length === 0) {
            this.notification.add("No draft payslips to confirm in this period.", {
                type: "info",
            });
            return;
        }
        try {
            await this.orm.call("security.payslip", "action_confirm", [draftIds]);
            this.notification.add(`${draftIds.length} payslip(s) confirmed successfully.`, {
                type: "success",
                title: "Confirmed",
            });
            await this._loadPayslips(this.state.selectedPeriodId);
        } catch (error) {
            this.notification.add("Failed to confirm payslips. Check your permissions.", {
                type: "danger",
                title: "Error",
            });
            console.error("PayrollCommandCenter.bulkConfirm error:", error);
        }
    }

    async bulkMarkPaid() {
        const confirmedIds = this.confirmedPayslips.map((p) => p.id);
        if (confirmedIds.length === 0) {
            this.notification.add("No confirmed payslips to mark as paid in this period.", {
                type: "info",
            });
            return;
        }
        try {
            await this.orm.call("security.payslip", "action_mark_paid", [confirmedIds]);
            this.notification.add(`${confirmedIds.length} payslip(s) marked as paid.`, {
                type: "success",
                title: "Marked Paid",
            });
            await this._loadPayslips(this.state.selectedPeriodId);
        } catch (error) {
            this.notification.add("Failed to mark payslips as paid. Check your permissions.", {
                type: "danger",
                title: "Error",
            });
            console.error("PayrollCommandCenter.bulkMarkPaid error:", error);
        }
    }

    async openPayslip(id) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.payslip",
            res_id: id,
            views: [[false, "form"]],
        });
    }

    async openPeriod(id) {
        if (!id) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.payroll.period",
            res_id: id,
            views: [[false, "form"]],
        });
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    // ── Formatting helpers ───────────────────────────────────────────────────

    formatCurrency(amount) {
        if (!amount && amount !== 0) return "N$ 0.00";
        return (
            "N$ " +
            Number(amount).toLocaleString("en-NA", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })
        );
    }

    stateBadgeClass(state) {
        if (state === "paid") return "bg-success";
        if (state === "confirmed") return "bg-primary";
        if (state === "cancelled") return "bg-secondary";
        return "bg-secondary text-dark";
    }

    periodStateBadgeClass(state) {
        if (state === "processed") return "bg-success";
        if (state === "closed") return "bg-dark";
        return "bg-secondary text-dark";
    }
}

registry
    .category("actions")
    .add("security_payroll_core.payroll_command_center", PayrollCommandCenter);
