/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PayrollExpenditure extends Component {
    static template = "security_payroll_core.PayrollExpenditure";
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
            byEmployee: [],
            totals: { gross: 0, net: 0, normal_hrs: 0, overtime_hrs: 0, premium_hrs: 0 },
            prevTotals: { gross: 0, net: 0 },
            activeTab: "by_employee",
            employeeSearchTerm: "",
            employeeFilter: "all",
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

    get selectedPeriod() {
        return this.state.periods.find((p) => p.id === this.state.selectedPeriodId) || null;
    }

    get previousPeriod() {
        const idx = this.state.periods.findIndex((p) => p.id === this.state.selectedPeriodId);
        return idx >= 0 && idx + 1 < this.state.periods.length ? this.state.periods[idx + 1] : null;
    }

    get grossChangePct() {
        if (!this.state.prevTotals.gross) return null;
        return ((this.state.totals.gross - this.state.prevTotals.gross) / this.state.prevTotals.gross) * 100;
    }

    get netChangePct() {
        if (!this.state.prevTotals.net) return null;
        return ((this.state.totals.net - this.state.prevTotals.net) / this.state.prevTotals.net) * 100;
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

    get filteredEmployees() {
        if (!this.state.byEmployee) return [];
        let list = this.state.byEmployee;

        // Custom filter
        if (this.state.employeeFilter === "ot") {
            list = list.filter((e) => e.ot_hrs > 0);
        } else if (this.state.employeeFilter === "premium") {
            list = list.filter((e) => (e.sat_hrs + e.sun_hrs + e.ph_hrs + e.night_hrs) > 0);
        }

        // Search filter
        const term = (this.state.employeeSearchTerm || "").toLowerCase().trim();
        if (term) {
            list = list.filter((e) => {
                const nameMatch = (e.name || "").toLowerCase().includes(term);
                const gradeMatch = (e.grade || "").toLowerCase().includes(term);
                return nameMatch || gradeMatch;
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
                ["name", "state", "total_earnings", "total_net_pay", "date_from", "date_to"],
                { limit: 12, order: "date_from desc" }
            );
            this.state.periods = periods;

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
            console.error("PayrollExpenditure._loadPeriods error:", error);
            this.state.loading = false;
        }
    }

    async loadPeriodData(periodId) {
        if (!periodId) {
            this.state.byEmployee = [];
            this.state.totals = { gross: 0, net: 0, normal_hrs: 0, overtime_hrs: 0, premium_hrs: 0 };
            return;
        }
        try {
            const payslips = await this.orm.searchRead(
                "security.payslip",
                [["period_id", "=", periodId]],
                [
                    "employee_id",
                    "total_earnings",
                    "net_pay",
                    "normal_hours",
                    "saturday_hours",
                    "sunday_hours",
                    "public_holiday_hours",
                    "night_hours",
                    "overtime_hours",
                    "state",
                ],
                { order: "employee_id asc" }
            );

            const empIds = [...new Set(payslips.map((p) => p.employee_id[0]))];
            let empMap = {};
            if (empIds.length > 0) {
                const employees = await this.orm.searchRead(
                    "hr.employee",
                    [["id", "in", empIds]],
                    ["id", "name", "security_grade_id"],
                    {}
                );
                employees.forEach((e) => (empMap[e.id] = e));
            }

            this.state.byEmployee = payslips.map((ps) => ({
                name: ps.employee_id[1],
                grade: empMap[ps.employee_id[0]]?.security_grade_id?.[1] || "—",
                gross: ps.total_earnings || 0,
                net: ps.net_pay || 0,
                normal_hrs: ps.normal_hours || 0,
                sat_hrs: ps.saturday_hours || 0,
                sun_hrs: ps.sunday_hours || 0,
                ph_hrs: ps.public_holiday_hours || 0,
                night_hrs: ps.night_hours || 0,
                ot_hrs: ps.overtime_hours || 0,
                state: ps.state,
            }));

            this.state.totals = {
                gross: this.state.byEmployee.reduce((s, p) => s + p.gross, 0),
                net: this.state.byEmployee.reduce((s, p) => s + p.net, 0),
                normal_hrs: this.state.byEmployee.reduce((s, p) => s + p.normal_hrs, 0),
                overtime_hrs: this.state.byEmployee.reduce((s, p) => s + p.ot_hrs, 0),
                premium_hrs: this.state.byEmployee.reduce(
                    (s, p) => s + p.sat_hrs + p.sun_hrs + p.ph_hrs + p.night_hrs,
                    0
                ),
            };

            // Load previous period totals for comparison
            const prevPeriod = this.previousPeriod;
            if (prevPeriod) {
                const prevPayslips = await this.orm.searchRead(
                    "security.payslip",
                    [["period_id", "=", prevPeriod.id]],
                    ["total_earnings", "net_pay"],
                    {}
                );
                this.state.prevTotals = {
                    gross: prevPayslips.reduce((s, p) => s + (p.total_earnings || 0), 0),
                    net: prevPayslips.reduce((s, p) => s + (p.net_pay || 0), 0),
                };
            } else {
                this.state.prevTotals = { gross: 0, net: 0 };
            }
        } catch (error) {
            this.notification.add("Failed to load period payslip data.", {
                type: "warning",
                title: "Load Error",
            });
            console.error("PayrollExpenditure.loadPeriodData error:", error);
            this.state.byEmployee = [];
            this.state.totals = { gross: 0, net: 0, normal_hrs: 0, overtime_hrs: 0, premium_hrs: 0 };
        }
    }

    // ── Actions ─────────────────────────────────────────────────────────────

    async selectPeriod(id) {
        this.state.selectedPeriodId = id;
        this.state.loading = true;
        await this.loadPeriodData(id);
        this.state.loading = false;
    }

    async openPeriod() {
        if (!this.state.selectedPeriodId) return;
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.payroll.period",
            res_id: this.state.selectedPeriodId,
            views: [[false, "form"]],
        });
    }

    setTab(t) {
        this.state.activeTab = t;
    }

    setEmployeeFilter(f) {
        this.state.employeeFilter = f;
    }

    exportExpenditureCsv() {
        const period = this.selectedPeriod;
        if (!period || !this.state.byEmployee.length) return;
        const header = ["Employee", "Grade", "Gross", "Net Pay", "Normal Hrs", "Sat Hrs", "Sun Hrs", "PH Hrs", "Night Hrs", "OT Hrs", "Status"];
        const rows = this.filteredEmployees.map((e) => [
            e.name,
            e.grade,
            e.gross,
            e.net,
            e.normal_hrs,
            e.sat_hrs,
            e.sun_hrs,
            e.ph_hrs,
            e.night_hrs,
            e.ot_hrs,
            e.state,
        ]);
        const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `payroll_expenditure_${period.name.replace(/\s+/g, "_")}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // ── Formatting helpers ───────────────────────────────────────────────────

    formatCurrency(v) {
        const sym = this.state.currencySymbol || "ZMW";
        if (!v && v !== 0) return `${sym} 0.00`;
        return (
            `${sym} ` +
            Number(v).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })
        );
    }

    formatHours(v) {
        if (!v && v !== 0) return "0.0";
        return Number(v).toFixed(1);
    }

    formatPct(pct) {
        if (pct === null || pct === undefined) return "—";
        return (pct >= 0 ? "+" : "") + pct.toFixed(1) + "%";
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
    .add("security_payroll_core.payroll_expenditure", PayrollExpenditure);
