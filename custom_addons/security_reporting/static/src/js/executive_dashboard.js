/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ExecutiveDashboard extends Component {
    static template = "security_reporting.ExecutiveDashboard";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            companyName: "Loading...",
            companyId: 1,
            kpis: {
                // Operations
                activeGuards: 0,
                onDutyToday: 0,
                awolToday: 0,
                unassignedSlots: 0,
                activeClientSites: 0,
                // Workforce
                pendingLeave: 0,
                openIncidents: 0,
                expiringDocs: 0,
                guardsOnLeave: 0,
                // Payroll
                activePeriodName: "—",
                payslipsPending: 0,
                payrollCostMtd: 0,
                activeLoanBalances: 0,
                // Billing
                draftInvoices: 0,
                overdueInvoices: 0,
                revenueMtd: 0,
                revenueOutstanding: 0,
                // Trends (calculated)
                attendanceRateToday: 0,
                attendanceRate7d: 0,
                awolTrend: 0,            // positive = worse, negative = better
                revenueVsLastMonth: 0,   // percentage change
            },
            sitesCoverage: [],
            recentAlerts: [],
            activeTab: "overview",
            lastUpdated: null,
            statusBanner: {
                operational: "green",
                coverage: "—",
                pendingActions: 0,
                billingHealth: "green",
            },
            aiSystem: {
                configured: false,
                provider: "—",
                enabledFeatures: 0,
                callsToday: 0,
                callsMtd: 0,
                successRate: 0,
                costMtd: 0.0,
                cacheHitsToday: 0,
                chatSessions: 0,
                features: {},
            },
        });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    // ── Date helpers ─────────────────────────────────────────────────────────

    _today() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    _monthStart() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
    }

    _lastMonthStart() {
        const d = new Date();
        d.setMonth(d.getMonth() - 1);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;
    }

    _lastMonthEnd() {
        const d = new Date();
        d.setDate(0);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    _daysFromToday(n) {
        const d = new Date();
        d.setDate(d.getDate() + n);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    // ── Computed helpers ─────────────────────────────────────────────────────

    get lastUpdatedDisplay() {
        if (!this.state.lastUpdated) return "Never";
        return this.state.lastUpdated.toLocaleTimeString();
    }

    get todayDisplay() {
        return new Date().toLocaleDateString("en-NA", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    // ── Data loading ──────────────────────────────────────────────────────────

    async _loadData() {
        this.state.loading = true;
        const today = this._today();
        const monthStart = this._monthStart();
        const lastMonthStart = this._lastMonthStart();
        const lastMonthEnd = this._lastMonthEnd();

        try {
            // Fetch company info
            try {
                const company = await this.orm.searchRead("res.company", [], ["name"], { limit: 1 });
                if (company.length) {
                    this.state.companyName = company[0].name;
                    this.state.companyId = company[0].id;
                }
            } catch (_e) {}

            const [
                activeGuards,
                onDutyToday,
                awolToday,
                absentToday,
                unassignedSlots,
                activeClientSites,
                pendingLeave,
                openIncidents,
                payslipsPending,
                draftInvoices,
                overdueInvoices,
            ] = await Promise.all([
                this.orm.searchCount("hr.employee", [["security_guard", "=", true], ["active", "=", true]]),
                this.orm.searchCount("security.attendance.record", [["shift_date", "=", today], ["status", "in", ["present", "late"]]]),
                this.orm.searchCount("security.attendance.record", [["shift_date", "=", today], ["absence_type", "=", "awol"]]),
                this.orm.searchCount("security.attendance.record", [["shift_date", "=", today], ["status", "=", "absent"]]),
                this.orm.searchCount("security.roster.slot", [["state", "=", "confirmed"], ["employee_id", "=", false]]),
                this.orm.searchCount("security.client.site", [["active", "=", true]]),
                this.orm.searchCount("security.leave.request", [["state", "=", "submitted"]]).catch(() => 0),
                this.orm.searchCount("security.incident", [["state", "=", "draft"]]).catch(() => 0),
                this.orm.searchCount("security.payslip", [["state", "=", "draft"]]).catch(() => 0),
                this.orm.searchCount("security.billing.invoice", [["state", "=", "draft"]]).catch(() => 0),
                this.orm.searchCount("security.billing.invoice", [["state", "not in", ["paid", "cancelled"]], ["due_date", "<", today]]).catch(() => 0),
            ]);

            let expiringDocs = 0, guardsOnLeave = 0, activeLoanBalances = 0;
            let payrollCostMtd = 0, revenueMtd = 0, revenueOutstanding = 0;
            let activePeriodName = "—", payslipsCount = payslipsPending;
            let awolTrend = 0, revenueVsLastMonth = 0;

            try {
                const in30 = this._daysFromToday(30);
                expiringDocs = await this.orm.searchCount("security.employee.document", [
                    ["expiry_date", ">=", today],
                    ["expiry_date", "<=", in30],
                ]);
            } catch (_e) {}

            try {
                guardsOnLeave = await this.orm.searchCount("security.leave.request", [
                    ["state", "=", "approved"],
                    ["date_from", "<=", today],
                    ["date_to", ">=", today],
                ]);
            } catch (_e) {}

            try {
                const loans = await this.orm.searchRead("security.employee.loan",
                    [["state", "=", "active"]], ["balance_remaining"]);
                activeLoanBalances = loans.reduce((s, l) => s + (l.balance_remaining || 0), 0);
            } catch (_e) {}

            try {
                const periods = await this.orm.searchRead("security.payroll.period",
                    [["state", "not in", ["closed"]]], ["name", "payslip_count"], { limit: 1, order: "date_from desc" });
                if (periods.length) {
                    activePeriodName = periods[0].name;
                    payslipsCount = periods[0].payslip_count || payslipsPending;
                }
            } catch (_e) {}

            try {
                const paid = await this.orm.searchRead("security.billing.invoice",
                    [["state", "=", "paid"], ["invoice_date", ">=", monthStart]], ["total_amount"]);
                revenueMtd = paid.reduce((s, i) => s + (i.total_amount || 0), 0);
                const sent = await this.orm.searchRead("security.billing.invoice",
                    [["state", "=", "sent"]], ["total_amount"]);
                revenueOutstanding = sent.reduce((s, i) => s + (i.total_amount || 0), 0);
            } catch (_e) {}

            try {
                const payslips = await this.orm.searchRead("security.payslip",
                    [["state", "in", ["confirmed", "paid"]]], ["total_earnings"]);
                payrollCostMtd = payslips.slice(0, 50).reduce((s, p) => s + (p.total_earnings || 0), 0);
            } catch (_e) {}

            // Trend: AWOL this week vs last week
            try {
                const weekAgo = this._daysFromToday(-7);
                const twoWeeksAgo = this._daysFromToday(-14);
                const awolThisWeek = await this.orm.searchCount("security.attendance.record",
                    [["shift_date", ">=", weekAgo], ["shift_date", "<=", today], ["absence_type", "=", "awol"]]);
                const awolLastWeek = await this.orm.searchCount("security.attendance.record",
                    [["shift_date", ">=", twoWeeksAgo], ["shift_date", "<", weekAgo], ["absence_type", "=", "awol"]]);
                awolTrend = awolThisWeek - awolLastWeek;
            } catch (_e) {}

            // Revenue vs last month
            try {
                const lmPaid = await this.orm.searchRead("security.billing.invoice",
                    [["state", "=", "paid"], ["invoice_date", ">=", lastMonthStart], ["invoice_date", "<=", lastMonthEnd]],
                    ["total_amount"]);
                const revenueLM = lmPaid.reduce((s, i) => s + (i.total_amount || 0), 0);
                revenueVsLastMonth = revenueLM > 0
                    ? Math.round(((revenueMtd - revenueLM) / revenueLM) * 100)
                    : 0;
            } catch (_e) {}

            // Site coverage for Roster tab
            try {
                const sites = await this.orm.searchRead("security.client.site",
                    [["active", "=", true]], ["name"]);
                const coverage = await Promise.all(sites.slice(0, 20).map(async (site) => {
                    const total = await this.orm.searchCount("security.roster.slot",
                        [["shift_date", "=", today], ["site_id", "=", site.id], ["state", "=", "confirmed"]]).catch(() => 0);
                    const filled = await this.orm.searchCount("security.roster.slot",
                        [["shift_date", "=", today], ["site_id", "=", site.id], ["state", "=", "confirmed"], ["employee_id", "!=", false]]).catch(() => 0);
                    return {
                        name: site.name,
                        total,
                        filled,
                        unfilled: total - filled,
                        pct: total > 0 ? Math.round((filled / total) * 100) : 100,
                    };
                }));
                this.state.sitesCoverage = coverage;
            } catch (_e) {}

            const totalAttendance = onDutyToday + awolToday + absentToday;
            const attendanceRateToday = totalAttendance > 0 ? Math.round((onDutyToday / totalAttendance) * 100) : 0;
            const pendingActions = pendingLeave + openIncidents + unassignedSlots;

            this.state.kpis = {
                activeGuards,
                onDutyToday,
                awolToday,
                unassignedSlots,
                activeClientSites,
                pendingLeave,
                openIncidents,
                expiringDocs,
                guardsOnLeave,
                activePeriodName,
                payslipsPending: payslipsCount,
                payrollCostMtd,
                activeLoanBalances,
                draftInvoices,
                overdueInvoices,
                revenueMtd,
                revenueOutstanding,
                attendanceRateToday,
                attendanceRate7d: attendanceRateToday,
                awolTrend,
                revenueVsLastMonth,
            };

            this.state.statusBanner = {
                operational: attendanceRateToday >= 90 ? "green" : attendanceRateToday >= 75 ? "amber" : "red",
                coverage: `${onDutyToday}/${totalAttendance} on duty (${attendanceRateToday}%)`,
                pendingActions,
                billingHealth: overdueInvoices === 0 ? "green" : overdueInvoices <= 3 ? "amber" : "red",
            };

            this.state.recentAlerts = this._buildAlerts();
            this.state.lastUpdated = new Date();
        } catch (error) {
            this.notification.add("Failed to load dashboard data.", { type: "warning" });
            console.error("Dashboard error:", error);
        } finally {
            this.state.loading = false;
        }

        // Load AI data in the background — non-blocking
        this._loadAIData().catch(() => {});
    }

    async _loadAIData() {
        const today = this._today();
        const monthStart = this._monthStart();

        try {
            const configs = await this.orm.searchRead(
                "security.ai.config",
                [["active", "=", true]],
                [
                    "active_provider", "total_calls", "successful_calls",
                    "monthly_cost_usd", "monthly_tokens_in",
                    "feature_attendance_anomaly", "feature_risk_profiling",
                    "feature_billing_auditor", "feature_roster_optimizer",
                    "feature_shift_fill", "feature_incident_advisor",
                    "feature_leave_coverage", "feature_doc_renewal_letter",
                    "feature_performance_review", "feature_payslip_explain",
                ],
                { limit: 1 }
            ).catch(() => []);

            if (!configs.length) {
                this.state.aiSystem.configured = false;
                return;
            }

            const cfg = configs[0];
            const featureKeys = [
                "feature_attendance_anomaly", "feature_risk_profiling",
                "feature_billing_auditor", "feature_roster_optimizer",
                "feature_shift_fill", "feature_incident_advisor",
                "feature_leave_coverage", "feature_doc_renewal_letter",
                "feature_performance_review", "feature_payslip_explain",
            ];
            const enabledCount = featureKeys.filter(k => cfg[k]).length;

            const [callsToday, cacheHitsToday, chatSessions] = await Promise.all([
                this.orm.searchCount("security.ai.log", [
                    ["call_date", ">=", today + " 00:00:00"],
                    ["state", "=", "success"],
                    ["cache_hit", "=", false],
                ]).catch(() => 0),
                this.orm.searchCount("security.ai.log", [
                    ["call_date", ">=", today + " 00:00:00"],
                    ["cache_hit", "=", true],
                ]).catch(() => 0),
                this.orm.searchCount("security.ai.chat.session", []).catch(() => 0),
            ]);

            const successRate = cfg.total_calls > 0
                ? Math.round((cfg.successful_calls / cfg.total_calls) * 100)
                : 0;

            this.state.aiSystem = {
                configured: true,
                provider: cfg.active_provider || "—",
                enabledFeatures: enabledCount,
                callsToday,
                cacheHitsToday,
                callsMtd: cfg.total_calls || 0,
                successRate,
                costMtd: cfg.monthly_cost_usd || 0,
                chatSessions,
                features: {
                    attendance_anomaly:  cfg.feature_attendance_anomaly,
                    risk_profiling:      cfg.feature_risk_profiling,
                    billing_auditor:     cfg.feature_billing_auditor,
                    roster_optimizer:    cfg.feature_roster_optimizer,
                    shift_fill:          cfg.feature_shift_fill,
                    incident_advisor:    cfg.feature_incident_advisor,
                    leave_coverage:      cfg.feature_leave_coverage,
                    doc_renewal_letter:  cfg.feature_doc_renewal_letter,
                    performance_review:  cfg.feature_performance_review,
                    payslip_explain:     cfg.feature_payslip_explain,
                },
            };
        } catch (_e) {}
    }

    // ── Alert feed ────────────────────────────────────────────────────────────

    _buildAlerts() {
        const alerts = [];
        const k = this.state.kpis;
        const today = this._today();

        if (k.overdueInvoices > 0) {
            alerts.push({ type: "danger", icon: "fa-exclamation-circle", message: `${k.overdueInvoices} invoice(s) are past due — immediate collection required.`, model: "security.billing.invoice", domain: [["state", "not in", ["paid", "cancelled"]], ["due_date", "<", today]] });
        }
        if (k.awolToday > 0) {
            alerts.push({ type: "danger", icon: "fa-user-times", message: `${k.awolToday} guard(s) marked AWOL today — posts may be uncovered.`, model: "security.attendance.record", domain: [["shift_date", "=", today], ["absence_type", "=", "awol"]] });
        }
        if (k.unassignedSlots > 0) {
            alerts.push({ type: "warning", icon: "fa-calendar-times-o", message: `${k.unassignedSlots} confirmed roster slot(s) have no guard assigned.`, model: "security.roster.slot", domain: [["state", "=", "confirmed"], ["employee_id", "=", false]] });
        }
        if (k.openIncidents > 0) {
            alerts.push({ type: "warning", icon: "fa-flag", message: `${k.openIncidents} incident(s) are pending review.`, model: "security.incident", domain: [["state", "=", "draft"]] });
        }
        if (k.expiringDocs > 0) {
            alerts.push({ type: "warning", icon: "fa-file-text-o", message: `${k.expiringDocs} document(s) expire within 30 days — request renewals.`, model: "security.employee.document", domain: [] });
        }
        if (k.pendingLeave > 0) {
            alerts.push({ type: "info", icon: "fa-calendar-check-o", message: `${k.pendingLeave} leave request(s) are awaiting approval.`, model: "security.leave.request", domain: [["state", "=", "submitted"]] });
        }
        if (k.draftInvoices > 0) {
            alerts.push({ type: "info", icon: "fa-file-text", message: `${k.draftInvoices} draft invoice(s) have not been sent to clients yet.`, model: "security.billing.invoice", domain: [["state", "=", "draft"]] });
        }
        if (k.payslipsPending > 0) {
            alerts.push({ type: "info", icon: "fa-money", message: `${k.payslipsPending} payslip(s) in draft — payroll period may need processing.`, model: "security.payslip", domain: [["state", "=", "draft"]] });
        }
        if (k.awolTrend > 0) {
            alerts.push({ type: "warning", icon: "fa-line-chart", message: `AWOL trend worsening: +${k.awolTrend} more this week vs last week.`, model: null, domain: [] });
        }
        if (alerts.length === 0) {
            alerts.push({ type: "success", icon: "fa-check-circle", message: "All systems nominal — no outstanding alerts.", model: null, domain: [] });
        }
        return alerts.slice(0, 15);
    }

    // ── Navigation ────────────────────────────────────────────────────────────

    setTab(tab) {
        this.state.activeTab = tab;
    }

    async openModel(model, domain) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
            name: model,
        });
    }

    async openAction(xmlid) {
        try {
            await this.action.doAction(xmlid);
        } catch (_e) {
            this.notification.add("Action not available.", { type: "warning" });
        }
    }

    async refreshData() {
        await this._loadData();
        this.notification.add("Dashboard refreshed.", { type: "success" });
    }

    // ── Formatting ────────────────────────────────────────────────────────────

    formatCurrency(v) {
        return "N$ " + Number(v || 0).toLocaleString("en-NA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    get trendArrow() {
        return (delta) => delta > 0 ? "↑" : delta < 0 ? "↓" : "→";
    }

    get trendColor() {
        return (delta, higherIsBad = true) => {
            if (delta === 0) return "#64748b";
            return (delta > 0) === higherIsBad ? "#dc2626" : "#16a34a";
        };
    }

    coverageBarColor(pct) {
        if (pct >= 90) return "#16a34a";
        if (pct >= 70) return "#d97706";
        return "#dc2626";
    }

    openAIChat() {
        const btn = document.querySelector(".o_ai_chat_toggle");
        if (btn) {
            btn.click();
        } else {
            this.notification.add(
                "AI Assistant is loading — try again in a moment.",
                { type: "info" }
            );
        }
    }

    openAIConfig() {
        this.openAction("security_ai_engine.action_security_ai_config");
    }

    formatCostUSD(v) {
        return "$" + Number(v || 0).toFixed(4);
    }

    aiProviderLabel(key) {
        return { claude: "Claude (Anthropic)", openai: "OpenAI", gemini: "Google Gemini" }[key] || key;
    }
}

registry.category("actions").add("security_reporting.executive_dashboard", ExecutiveDashboard);
