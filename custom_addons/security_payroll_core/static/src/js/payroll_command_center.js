/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PayrollCommandCenter extends Component {
    static template = "security_payroll_core.PayrollCommandCenter";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            currencySymbol: "ZMW",
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
            payslipSearchTerm: "",
            payslipStateFilter: "all",
            periodSearchTerm: "",
        });

        onWillStart(async () => {
            await this._loadCurrency();
            await this._loadPeriods();
        });
    }

    async _loadCurrency() {
        try {
            const companies = await this.orm.searchRead("res.company", [], ["currency_id"], { limit: 1 });
            if (companies.length && companies[0].currency_id) {
                const currencies = await this.orm.read("res.currency", [companies[0].currency_id[0]], ["symbol", "name"]);
                if (currencies.length) {
                    this.state.currencySymbol = currencies[0].symbol || currencies[0].name || "ZMW";
                }
            }
        } catch (_e) {
            this.state.currencySymbol = "ZMW";
        }
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

    get filteredPeriods() {
        if (!this.state.periods) return [];
        const term = (this.state.periodSearchTerm || "").toLowerCase().trim();
        if (!term) return this.state.periods;
        return this.state.periods.filter((p) =>
            (p.name || "").toLowerCase().includes(term) ||
            (p.state || "").toLowerCase().includes(term)
        );
    }

    get filteredPayslips() {
        if (!this.state.payslips) return [];
        let list = this.state.payslips;

        // State filter
        if (this.state.payslipStateFilter !== "all") {
            list = list.filter((p) => p.state === this.state.payslipStateFilter);
        }

        // Search term filter
        const term = (this.state.payslipSearchTerm || "").toLowerCase().trim();
        if (term) {
            list = list.filter((p) => {
                const nameMatch = (p.name || "").toLowerCase().includes(term);
                const empName = (p.employee_id && p.employee_id[1]) ? p.employee_id[1].toLowerCase() : "";
                const empMatch = empName.includes(term);
                return nameMatch || empMatch;
            });
        }
        return list;
    }

    // ── Data loading ────────────────────────────────────────────────────────

    async _loadPeriods() {
        this.state.loading = true;
        try {
            const periods = await this.orm.searchRead(
                "security.payroll.period",
                [],
                ["name", "state", "date_from", "date_to", "total_net_pay", "payslip_count"],
                { order: "date_from desc", limit: 12 }
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

    setPayslipStateFilter(stateKey) {
        this.state.payslipStateFilter = stateKey;
    }

    exportCsv() {
        const period = this.selectedPeriod;
        if (!period || !this.state.payslips.length) return;
        const header = ["Reference", "Employee", "Worked Days", "State", "Gross Earnings", "Deductions", "Net Pay", "Anomaly Score"];
        const rows = this.filteredPayslips.map((p) => [
            p.name,
            p.employee_id ? p.employee_id[1] : "",
            p.worked_days || 0,
            p.state,
            p.total_earnings || 0,
            p.total_deductions || 0,
            p.net_pay || 0,
            p.anomaly_score || 0,
        ]);
        const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `payroll_${period.name.replace(/\s+/g, "_")}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // ── Formatting helpers ───────────────────────────────────────────────────

    formatCurrency(amount) {
        const sym = this.state.currencySymbol || "ZMW";
        if (!amount && amount !== 0) return `${sym} 0.00`;
        return (
            `${sym} ` +
            Number(amount).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })
        );
    }

    stateBadgeClass(state) {
        if (state === "paid") return "bg-success text-white";
        if (state === "confirmed") return "bg-primary text-white";
        if (state === "cancelled") return "bg-secondary text-white";
        return "bg-warning text-dark";
    }

    periodStateBadgeClass(state) {
        if (state === "processed") return "bg-success text-white";
        if (state === "closed") return "bg-dark text-white";
        return "bg-secondary text-white";
    }
}

registry
    .category("actions")
    .add("security_payroll_core.payroll_command_center", PayrollCommandCenter);
