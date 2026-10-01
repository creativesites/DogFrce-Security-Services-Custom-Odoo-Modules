/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ClientSitesWorkbench extends Component {
    static template = "security_operations.ClientSitesWorkbench";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            filter: "all", // "all", "needs_setup", "coverage_risk", "expiring", "no_supervisor"
            searchQuery: "",
            clients: [],
            sites: [],
            collapsedClients: {},
            metrics: {
                totalClients: 0,
                totalSites: 0,
                readySites: 0,
                needsSetupSites: 0,
                coverageRiskSites: 0,
                expiringContracts: 0,
                noSupervisorSites: 0,
            },
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            // Load sites
            const sites = await this.orm.searchRead(
                "security.client.site",
                [["active", "=", true]],
                [
                    "name", "code", "partner_id", "location", "supervisor_id",
                    "contract_id", "is_contract_managed", "setup_status",
                    "contract_status", "risk_level", "site_type"
                ]
            );

            // Fetch counts of posts & shifts per site
            const postCounts = await this.orm.readGroup(
                "security.post",
                [["active", "=", true]],
                ["site_id"],
                ["site_id"]
            );
            const postCountMap = {};
            for (const pc of postCounts) {
                if (pc.site_id) {
                    postCountMap[pc.site_id[0]] = pc.site_id_count;
                }
            }

            const reqCounts = await this.orm.readGroup(
                "security.shift.requirement",
                [["active", "=", true]],
                ["site_id"],
                ["site_id"]
            );
            const reqCountMap = {};
            for (const rc of reqCounts) {
                if (rc.site_id) {
                    reqCountMap[rc.site_id[0]] = rc.site_id_count;
                }
            }

            let readyCount = 0;
            let needsSetupCount = 0;
            let coverageRiskCount = 0;
            let expiringCount = 0;
            let noSupervisorCount = 0;

            const clientMap = {};

            for (const site of sites) {
                site.postCount = postCountMap[site.id] || 0;
                site.reqCount = reqCountMap[site.id] || 0;
                // slots/mo rough approximation: requirements * 30 days
                site.approxMonthlySlots = site.reqCount * 30;

                // Evaluate status metrics
                const isReady = site.setup_status === "ready";
                const hasCoverageRisk = site.postCount === 0 || site.reqCount === 0;
                const isExpiring = site.contract_status === "expiring_soon";
                const hasNoSupervisor = !site.supervisor_id;

                if (isReady) readyCount++;
                if (!isReady) needsSetupCount++;
                if (hasCoverageRisk) coverageRiskCount++;
                if (isExpiring) expiringCount++;
                if (hasNoSupervisor) noSupervisorCount++;

                // Group by client
                const clientId = site.partner_id ? site.partner_id[0] : 0;
                const clientName = site.partner_id ? site.partner_id[1] : "Unassigned Client";

                if (!clientMap[clientId]) {
                    clientMap[clientId] = {
                        id: clientId,
                        name: clientName,
                        sites: [],
                        hasActiveContract: false,
                        contractId: site.contract_id ? site.contract_id[0] : null,
                        contractName: site.contract_id ? site.contract_id[1] : null,
                    };
                }

                if (site.contract_id) {
                    clientMap[clientId].hasActiveContract = true;
                    clientMap[clientId].contractId = site.contract_id[0];
                    clientMap[clientId].contractName = site.contract_id[1];
                }

                clientMap[clientId].sites.push(site);
            }

            this.state.sites = sites;
            this.state.clients = Object.values(clientMap);
            this.state.metrics = {
                totalClients: this.state.clients.length,
                totalSites: sites.length,
                readySites: readyCount,
                needsSetupSites: needsSetupCount,
                coverageRiskSites: coverageRiskCount,
                expiringContracts: expiringCount,
                noSupervisorSites: noSupervisorCount,
            };
        } catch (e) {
            console.error("Error loading Client Sites Workbench:", e);
            this.notification.add(`Failed to load sites: ${e.message}`, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    setFilter(filter) {
        this.state.filter = filter;
    }

    toggleCollapse(clientId) {
        this.state.collapsedClients[clientId] = !this.state.collapsedClients[clientId];
    }

    get filteredClients() {
        const query = (this.state.searchQuery || "").toLowerCase().trim();
        const filter = this.state.filter;

        return this.state.clients.map(client => {
            // Filter sites
            const matchingSites = client.sites.filter(site => {
                // Search query match
                if (query) {
                    const matchSite = (site.name || "").toLowerCase().includes(query);
                    const matchCode = (site.code || "").toLowerCase().includes(query);
                    const matchLoc = (site.location || "").toLowerCase().includes(query);
                    const matchClient = (client.name || "").toLowerCase().includes(query);
                    if (!matchSite && !matchCode && !matchLoc && !matchClient) {
                        return false;
                    }
                }

                // Filter chip match
                if (filter === "needs_setup") {
                    return site.setup_status !== "ready";
                }
                if (filter === "coverage_risk") {
                    return site.postCount === 0 || site.reqCount === 0;
                }
                if (filter === "expiring") {
                    return site.contract_status === "expiring_soon";
                }
                if (filter === "no_supervisor") {
                    return !site.supervisor_id;
                }
                return true;
            });

            return {
                ...client,
                sites: matchingSites,
            };
        }).filter(client => client.sites.length > 0);
    }

    openContractSetup(site) {
        if (site.contract_id) {
            this.actionService.doAction({
                type: "ir.actions.client",
                tag: "security_operations.contract_workspace",
                context: { active_id: site.contract_id[0] },
            });
        } else {
            this.notification.add("This site is not linked to an active contract.", { type: "warning" });
        }
    }

    openSiteOps(siteId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.site",
            res_id: siteId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSiteHub(siteId) {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "security_operations.site_hub",
            context: { active_id: siteId },
        });
    }

    async generateRoster(siteId) {
        try {
            await this.orm.call("security.client.site", "action_generate_next_month_roster", [[siteId]]);
            this.notification.add("Roster generation initiated for 21st–20th cycle.", { type: "success" });
        } catch (e) {
            this.notification.add(e.message || "Could not generate roster.", { type: "danger" });
        }
    }

    openSetupWizard(siteId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.site.setup.wizard",
            views: [[false, "form"]],
            target: "new",
            context: { default_site_id: siteId },
        });
    }

    openClientOnboarding() {
        this.actionService.doAction("security_client_onboarding.action_security_client_onboarding_wizard");
    }

    openContractList() {
        this.actionService.doAction("security_operations.action_security_client_contract");
    }
}

registry.category("actions").add("security_operations.client_sites_workbench", ClientSitesWorkbench);
