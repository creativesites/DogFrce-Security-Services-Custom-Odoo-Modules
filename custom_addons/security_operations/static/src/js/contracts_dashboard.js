/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class ContractsDashboard extends Component {
    static template = "security_operations.ContractsDashboard";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            filter: "all", // all, ready, needs_setup, active, draft
            searchQuery: "",
            contracts: [],
            stats: {
                total: 0,
                active: 0,
                draft: 0,
                ready: 0,
                avgReadiness: 0,
                totalSites: 0,
                totalPosts: 0,
                totalSlots: 0,
            },
            aiLoading: false,
            aiSummary: "",
            aiSuggestions: "",
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const rawContracts = await this.orm.searchRead(
                "security.client.contract",
                [],
                [
                    "name", "partner_id", "state", "date_start", "date_end",
                    "readiness_pct", "setup_issues_count", "sites_count",
                    "posts_count", "requirements_count", "estimated_monthly_slots",
                    "billing_frequency"
                ],
                { order: "readiness_pct desc, name asc" }
            );

            this.state.contracts = rawContracts;

            const total = rawContracts.length;
            const active = rawContracts.filter(c => c.state === "active").length;
            const draft = rawContracts.filter(c => c.state === "draft").length;
            const ready = rawContracts.filter(c => (c.readiness_pct || 0) >= 80).length;
            const avgReadiness = total ? Math.round(rawContracts.reduce((acc, c) => acc + (c.readiness_pct || 0), 0) / total) : 0;
            const totalSites = rawContracts.reduce((acc, c) => acc + (c.sites_count || 0), 0);
            const totalPosts = rawContracts.reduce((acc, c) => acc + (c.posts_count || 0), 0);
            const totalSlots = rawContracts.reduce((acc, c) => acc + (c.estimated_monthly_slots || 0), 0);

            this.state.stats = {
                total, active, draft, ready, avgReadiness,
                totalSites, totalPosts, totalSlots
            };

            // Fetch AI insights from shell data or generate if empty
            const payload = await this.orm.call("security.shell.data", "get_home_payload", ["today"]);
            if (payload && payload.contracts) {
                this.state.aiSummary = payload.contracts.ai_summary || "";
                this.state.aiSuggestions = payload.contracts.ai_suggestions || "";
            }
        } catch (e) {
            console.error("Failed to load contracts dashboard data:", e);
            this.notification.add("Failed to load contract dashboard data", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    get filteredContracts() {
        let list = this.state.contracts;
        const q = (this.state.searchQuery || "").trim().toLowerCase();
        if (q) {
            list = list.filter(c => {
                const name = (c.name || "").toLowerCase();
                const partner = (c.partner_id ? c.partner_id[1] : "").toLowerCase();
                return name.includes(q) || partner.includes(q);
            });
        }

        switch (this.state.filter) {
            case "ready":
                return list.filter(c => (c.readiness_pct || 0) >= 80);
            case "needs_setup":
                return list.filter(c => (c.readiness_pct || 0) < 80);
            case "active":
                return list.filter(c => c.state === "active");
            case "draft":
                return list.filter(c => c.state === "draft");
            default:
                return list;
        }
    }

    setFilter(filterName) {
        this.state.filter = filterName;
    }

    openContract(contractId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.contract",
            res_id: contractId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openWorkspace(contractId) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "security_operations.contract_workspace",
            params: { contract_id: contractId },
            target: "current",
        });
    }

    createNewContract() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.contract",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async refreshAiInsights() {
        if (this.state.aiLoading) return;
        this.state.aiLoading = true;
        try {
            const res = await this.orm.call("security.shell.data", "action_refresh_contracts_ai_insights", []);
            if (res) {
                this.state.aiSummary = res.summary;
                this.state.aiSuggestions = res.suggestions;
                this.notification.add("Gemini AI contract analysis updated successfully", { type: "success" });
            }
        } catch (e) {
            console.error("AI insights generation failed:", e);
            this.notification.add("AI analysis request failed", { type: "danger" });
        } finally {
            this.state.aiLoading = false;
        }
    }
}

registry.category("actions").add("security_operations.contracts_dashboard", ContractsDashboard);
