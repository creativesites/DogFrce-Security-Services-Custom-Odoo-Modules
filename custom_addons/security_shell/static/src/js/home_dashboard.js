/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { NAV_CATALOG } from "./nav_catalog";

const REFRESH_MS = 60000;

const OWNER_QUICK_ACTIONS = [
    { key: "approve_overtime", label: "Approve overtime", subtitle: "Review pending hours", iconLetter: "C" },
    { key: "coverage_trend", label: "Coverage trend", subtitle: "Roster fill over time", iconLetter: "T" },
    { key: "run_payroll", label: "Run payroll", subtitle: "Open the payroll cycle", iconLetter: "P" },
    { key: "billing_status", label: "Billing status", subtitle: "Draft & sent invoices", iconLetter: "B" },
];

const MANAGER_QUICK_ACTIONS = [
    { key: "fill_roster_gaps", label: "Fill roster gaps", subtitle: "Unassigned posts", iconLetter: "G" },
    { key: "approve_overtime", label: "Approve overtime", subtitle: "Review pending hours", iconLetter: "C" },
    { key: "add_guard", label: "Add guard", subtitle: "New employee record", iconLetter: "A" },
    { key: "publish_week", label: "Publish week", subtitle: "Weekly roster review", iconLetter: "W" },
];

const STATUS_LABEL = {
    covered: "Covered",
    at_risk: "At risk",
    gaps: "Gaps",
};

export class HomeDashboard extends Component {
    static template = "security_shell.HomeDashboard";
    static props = { "*": true };

    setup() {
        const shellService = useService("deployguard_shell");
        this.shell = { ...shellService, state: useState(shellService.state) };
        this.action = useService("action");

        this.uiState = useState({
            period: "today",
            previewRole: "owner",
            loading: true,
        });

        onWillStart(async () => {
            await this.shell.loadPayload(this.uiState.period);
            this.uiState.loading = false;
        });

        this._onVisibilityChange = this._onVisibilityChange.bind(this);
        onMounted(() => {
            this._refreshTimer = setInterval(() => {
                if (document.visibilityState === "visible") {
                    this.shell.loadPayload(this.uiState.period);
                }
            }, REFRESH_MS);
            document.addEventListener("visibilitychange", this._onVisibilityChange);
        });

        onWillUnmount(() => {
            clearInterval(this._refreshTimer);
            document.removeEventListener("visibilitychange", this._onVisibilityChange);
        });
    }

    _onVisibilityChange() {
        if (document.visibilityState === "visible") {
            this.shell.loadPayload(this.uiState.period);
        }
    }

    get payload() {
        return this.shell.state.payload;
    }

    get roles() {
        return this.shell.state.roles;
    }

    get userName() {
        return user.name || "";
    }

    get userInitials() {
        return (user.name || "")
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((p) => p[0].toUpperCase())
            .join("") || "?";
    }

    get todayLabel() {
        return new Date().toLocaleDateString(undefined, {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    get sitesCount() {
        return this.payload?.sites_count;
    }

    /** Owners can preview the Manager layout; everyone else always sees
     * their real role — the toggle never changes what data is fetched. */
    get effectiveIsOwnerView() {
        return this.roles.isOwner && this.uiState.previewRole === "owner";
    }

    setPreviewRole(role) {
        if (this.roles.isOwner) {
            this.uiState.previewRole = role;
        }
    }

    setPeriod(period) {
        this.uiState.period = period;
        this.shell.loadPayload(period);
    }

    get quickActions() {
        return this.effectiveIsOwnerView ? OWNER_QUICK_ACTIONS : MANAGER_QUICK_ACTIONS;
    }

    onQuickAction(item) {
        const xmlid = this.payload?.actions?.[item.key];
        if (!xmlid) {
            return;
        }
        this.action.doAction(xmlid, { clearBreadcrumbs: true }).catch((e) => {
            console.error("DeployGuard Shell: quick action failed", xmlid, e);
        });
    }

    get coverage() {
        return this.payload?.coverage;
    }

    get coverageStatusLabel() {
        return STATUS_LABEL[this.coverage?.status] || "";
    }

    /** Bar heights (%) for the 56-bar histogram, floored so a 0% bar still
     * shows a sliver. */
    get histogramBars() {
        const histogram = this.coverage?.histogram || [];
        return histogram.map((pct) => Math.max(pct, 4));
    }

    get attentionRows() {
        const rows = this.payload?.attention || [];
        return rows.filter((row) => typeof row.count === "number" && row.count > 0);
    }

    onAttentionClick(row) {
        if (!row.action) {
            return;
        }
        this.action.doAction(row.action, { clearBreadcrumbs: true });
    }

    onViewAllAttention() {
        const first = this.attentionRows[0];
        if (first) {
            this.onAttentionClick(first);
        }
    }

    get moduleFamilies() {
        const catalog = this.shell.getVisibleCatalog(this.shell.state);
        return catalog.map((group) => ({
            key: group.key,
            label: group.label,
            leafCount: group.leafCount,
            tiles: group.children.flatMap((sg) => sg.children).map((leaf) => ({
                key: leaf.key,
                label: leaf.label,
                soon: !!leaf.soon,
                initials: leaf.label
                    .split(/\s+/)
                    .filter(Boolean)
                    .slice(0, 2)
                    .map((w) => w[0].toUpperCase())
                    .join(""),
                count: leaf.countKey ? this.payload?.nav_counts?.[leaf.countKey] : null,
                missing: !leaf.soon && (!leaf.action || !this.shell.isResolved(leaf.action, this.shell.state)),
            })),
        }));
    }

    onModuleTileClick(family, tile) {
        if (tile.soon || tile.missing) {
            return;
        }
        const leaf = NAV_CATALOG
            .find((g) => g.key === family.key)
            ?.children.flatMap((sg) => sg.children)
            .find((l) => l.key === tile.key);
        if (leaf?.action) {
            this.action.doAction(leaf.action, { clearBreadcrumbs: true });
        }
    }

    get metrics() {
        return this.payload?.metrics || [];
    }

    onBellClick() {
        this.action.doAction("security_notifications.action_security_notifications", {
            clearBreadcrumbs: true,
        }).catch(() => {});
    }

    onAvatarClick() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.users",
            res_id: user.userId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    onSearchFocus() {
        this.shell.state.paletteOpen = true;
    }
}

registry.category("actions").add("deployguard.main_command_center", HomeDashboard);
