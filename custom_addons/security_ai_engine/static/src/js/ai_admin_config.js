/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class AIAdminDashboard extends Component {
    static props = { "*": true };
    static template = "security_ai_engine.AIAdminDashboard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            config: null,
            logs: [],
            stats: { total: 0, success: 0, error: 0 },
            testingConnection: false,
            activeTab: "overview",
        });

        onWillStart(async () => {
            await this._loadData();
        });
    }

    async _loadData() {
        this.state.loading = true;
        try {
            const configs = await this.orm.searchRead(
                "security.ai.config",
                [["active", "=", true]],
                ["name", "active_provider", "feature_attendance_anomaly",
                 "feature_risk_profiling", "feature_billing_auditor",
                 "feature_roster_optimizer", "max_tokens", "temperature",
                 "total_calls", "successful_calls", "failed_calls"],
                { limit: 1 }
            );
            this.state.config = configs.length ? configs[0] : null;

            if (this.state.config) {
                this.state.stats = {
                    total: this.state.config.total_calls,
                    success: this.state.config.successful_calls,
                    error: this.state.config.failed_calls,
                };
            }

            this.state.logs = await this.orm.searchRead(
                "security.ai.log",
                [],
                ["call_date", "feature", "provider", "model_name",
                 "duration_ms", "state", "error_message"],
                { limit: 50, order: "call_date desc" }
            );
        } catch (e) {
            this.notification.add("Failed to load AI Engine data.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async testConnection() {
        if (!this.state.config) return;
        this.state.testingConnection = true;
        try {
            const result = await this.orm.call(
                "security.ai.config",
                "action_test_connection",
                [[this.state.config.id]]
            );
            if (result?.params?.type === "success") {
                this.notification.add(result.params.message, { type: "success" });
            } else {
                this.notification.add(result?.params?.message || "Unexpected response.", { type: "warning" });
            }
        } catch (e) {
            this.notification.add(String(e.message || e), { type: "danger" });
        } finally {
            this.state.testingConnection = false;
        }
    }

    openConfig() {
        if (!this.state.config) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.ai.config",
            res_id: this.state.config.id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openLogs() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.ai.log",
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    get successRate() {
        const { total, success } = this.state.stats;
        if (!total) return "—";
        return Math.round((success / total) * 100) + "%";
    }

    get providerLabel() {
        const map = { claude: "Claude (Anthropic)", openai: "OpenAI", gemini: "Google Gemini" };
        return map[this.state.config?.active_provider] || "—";
    }

    get featureList() {
        if (!this.state.config) return [];
        return [
            { key: "feature_attendance_anomaly", label: "Attendance Anomaly Detection", enabled: this.state.config.feature_attendance_anomaly },
            { key: "feature_risk_profiling", label: "Guard Risk Profiling", enabled: this.state.config.feature_risk_profiling },
            { key: "feature_billing_auditor", label: "Billing Auditor", enabled: this.state.config.feature_billing_auditor },
            { key: "feature_roster_optimizer", label: "Roster Optimizer", enabled: this.state.config.feature_roster_optimizer },
        ];
    }

    get recentLogs() {
        return this.state.logs.slice(0, 20);
    }
}

registry.category("actions").add("security_ai_engine.ai_admin", AIAdminDashboard);
