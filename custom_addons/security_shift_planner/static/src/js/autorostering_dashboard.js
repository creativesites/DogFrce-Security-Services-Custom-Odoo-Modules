/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class AutoRosteringDashboard extends Component {
    static template = "security_shift_planner.AutoRosteringDashboard";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            runningRoster: false,
            activeTab: "contracts", // "contracts" | "batches"
            cycleType: "current", // "current" | "next"
            searchQuery: "",
            filterState: "all", // "all", "ready", "with_gaps", "perfect"
            data: {
                cycle_type: "current",
                cycle_label: "",
                date_from: "",
                date_to: "",
                stats: {
                    total_batches: 0,
                    total_slots: 0,
                    total_assigned: 0,
                    unassigned_gaps: 0,
                    overall_fill_rate: 0,
                    active_contracts: 0,
                    ready_contracts: 0,
                },
                contracts: [],
                batches: [],
            },
            lastResult: null,
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "security.roster.batch",
                "get_autoroster_dashboard_data",
                [this.state.cycleType]
            );
            if (data) {
                this.state.data = data;
            }
        } catch (error) {
            console.error("Failed to load autorostering data:", error);
            this.notification.add("Failed to load auto-rostering cycle data.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async setCycle(cycleType) {
        if (this.state.cycleType === cycleType) return;
        this.state.cycleType = cycleType;
        await this.loadData();
    }

    setActiveTab(tab) {
        this.state.activeTab = tab;
    }

    setFilter(filter) {
        this.state.filterState = filter;
    }

    get filteredContracts() {
        let list = this.state.data.contracts || [];
        const query = this.state.searchQuery.trim().toLowerCase();
        if (query) {
            list = list.filter(c =>
                (c.name && c.name.toLowerCase().includes(query)) ||
                (c.partner_name && c.partner_name.toLowerCase().includes(query))
            );
        }
        if (this.state.filterState === "ready") {
            list = list.filter(c => c.readiness_pct >= 100);
        } else if (this.state.filterState === "with_gaps") {
            list = list.filter(c => c.gaps_count > 0);
        } else if (this.state.filterState === "perfect") {
            list = list.filter(c => c.slots_count > 0 && c.gaps_count === 0);
        }
        return list;
    }

    get filteredBatches() {
        let list = this.state.data.batches || [];
        const query = this.state.searchQuery.trim().toLowerCase();
        if (query) {
            list = list.filter(b =>
                (b.name && b.name.toLowerCase().includes(query)) ||
                (b.site_name && b.site_name.toLowerCase().includes(query)) ||
                (b.partner_name && b.partner_name.toLowerCase().includes(query))
            );
        }
        return list;
    }

    async runFullAutoRoster() {
        if (this.state.runningRoster) return;
        this.state.runningRoster = true;
        this.state.lastResult = null;
        try {
            const result = await this.orm.call(
                "security.roster.batch",
                "action_run_cycle_autoroster",
                [this.state.cycleType]
            );
            if (result && result.success) {
                this.state.lastResult = result;
                this.notification.add(result.message || "Auto-rostering completed successfully!", {
                    type: "success",
                });
                await this.loadData();
            } else {
                this.notification.add((result && result.message) || "Auto-rostering completed with notices.", {
                    type: "warning",
                });
            }
        } catch (error) {
            console.error("Auto-roster execution error:", error);
            this.notification.add("Auto-rostering run encountered an error: " + (error.message || error), {
                type: "danger",
            });
        } finally {
            this.state.runningRoster = false;
        }
    }

    async runContractAutoRoster(contractId) {
        if (this.state.runningRoster) return;
        this.state.runningRoster = true;
        try {
            const result = await this.orm.call(
                "security.roster.batch",
                "action_run_cycle_autoroster",
                [this.state.cycleType, [contractId]]
            );
            if (result && result.success) {
                this.notification.add(result.message || "Contract roster generated successfully!", {
                    type: "success",
                });
                await this.loadData();
            }
        } catch (error) {
            console.error("Contract auto-roster error:", error);
            this.notification.add("Could not generate roster for contract: " + (error.message || error), {
                type: "danger",
            });
        } finally {
            this.state.runningRoster = false;
        }
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

    openContractWorkspace(contractId) {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "security_operations.contract_workspace",
            name: "Contract Workspace",
            context: {
                active_id: contractId,
                default_contract_id: contractId,
            },
        });
    }

    openBatch(batchId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.roster.batch",
            res_id: batchId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openRosteringHub() {
        this.action.doAction({
            type: "ir.actions.client",
            tag: "security_shift_planner.rostering_hub",
            name: "Rostering Hub",
        });
    }
}

registry.category("actions").add("security_shift_planner.autorostering_dashboard", AutoRosteringDashboard);
