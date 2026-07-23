/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class OpsDashboard extends Component {
    static template = "security_operations.OpsDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        const now = new Date();
        const pad = n => String(n).padStart(2, "0");
        this._today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;

        this.state = useState({
            loading: true,
            data: null,
            filterSite: "all",
            filterShift: "all",
            searchQuery: "",
            selectedAlert: null,
            selectedSite: null,
            suggestions: [],
            loadingSuggestions: false,
            filling: false,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "security.operations.dashboard",
                "get_dashboard_data",
                [],
                {
                    site_id: this.state.filterSite,
                    shift_filter: this.state.filterShift,
                }
            );
            this.state.data = data;

            if (this.state.selectedAlert) {
                const updated = data.awol_alerts.find(a => a.slot_id === this.state.selectedAlert.slot_id);
                this.state.selectedAlert = updated || null;
            }
        } finally {
            this.state.loading = false;
        }
    }

    // ── Filters & Search ──

    onSiteFilterChange(ev) {
        this.state.filterSite = ev.target.value;
        this.loadData();
    }

    onShiftFilterChange(ev) {
        this.state.filterShift = ev.target.value;
        this.loadData();
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value.toLowerCase().trim();
    }

    get filteredAlerts() {
        if (!this.state.data?.awol_alerts) return [];
        const q = this.state.searchQuery;
        if (!q) return this.state.data.awol_alerts;
        return this.state.data.awol_alerts.filter(
            a => a.guard.toLowerCase().includes(q) ||
                 a.site.toLowerCase().includes(q) ||
                 a.post.toLowerCase().includes(q)
        );
    }

    get filteredSites() {
        if (!this.state.data?.attention_sites) return [];
        const q = this.state.searchQuery;
        if (!q) return this.state.data.attention_sites;
        return this.state.data.attention_sites.filter(
            s => s.site.toLowerCase().includes(q) ||
                 s.location.toLowerCase().includes(q) ||
                 s.supervisor.toLowerCase().includes(q)
        );
    }

    // ── Selection & Shift Command Inspector ──

    async selectAlert(alert) {
        this.state.selectedSite = null;
        this.state.selectedAlert = alert;
        await this.loadSuggestions(alert.slot_id);
    }

    selectSite(site) {
        this.state.selectedAlert = null;
        this.state.selectedSite = site;
        this.state.suggestions = [];
    }

    closeInspector() {
        this.state.selectedAlert = null;
        this.state.selectedSite = null;
        this.state.suggestions = [];
    }

    async loadSuggestions(slotId) {
        this.state.loadingSuggestions = true;
        try {
            const candidates = await this.orm.call(
                "security.operations.dashboard",
                "action_get_slot_suggestions",
                [slotId]
            );
            this.state.suggestions = candidates || [];
        } finally {
            this.state.loadingSuggestions = false;
        }
    }

    // ── Quick Actions ──

    async assignReplacement(slotId, candidateId) {
        const ok = await this.orm.call(
            "security.operations.dashboard",
            "action_quick_assign_replacement",
            [slotId, candidateId]
        );
        if (ok) {
            this.notification.add("Replacement guard assigned successfully.", { type: "success" });
            this.closeInspector();
            await this.loadData();
        }
    }

    async autoFillGaps() {
        this.state.filling = true;
        try {
            const filled = await this.orm.call(
                "security.operations.dashboard",
                "action_auto_fill_gaps",
                [],
                { site_id: this.state.filterSite }
            );
            this.notification.add(`Auto-filled ${filled} unassigned shift gaps.`, { type: "success" });
            await this.loadData();
        } finally {
            this.state.filling = false;
        }
    }

    // ── Navigation ──

    openRosterBoard() {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "security_shift_planner.roster_board",
        });
    }

    openLiveOps() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Live Operations Command",
            res_model: "security.roster.slot",
            domain: [["shift_date", "=", this._today]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openSlotForm(slotId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.roster.slot",
            res_id: slotId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSiteForm(siteId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.site",
            res_id: siteId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("security_operations.ops_dashboard", OpsDashboard);
