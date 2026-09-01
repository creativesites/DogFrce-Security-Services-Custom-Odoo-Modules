/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class ShellNavPanel extends Component {
    static template = "security_shell.ShellNavPanel";
    static props = { "*": true };

    setup() {
        const shellService = useService("deployguard_shell");
        // shellService's reactive state has no callback of its own (it's a
        // shared singleton, not owned by any one component). Owl's reactive
        // tracking is per-proxy-instance, not per-target — reads must go
        // through a proxy that was itself created with useState(), or no
        // render ever gets subscribed. Wrapping .state locally (methods are
        // plain closures over the shared raw state, so they still mutate it
        // correctly) is what actually wires this component's re-render for
        // group toggles, search, resolved actions, and payload updates.
        this.shell = { ...shellService, state: useState(shellService.state) };
        this.action = useService("action");
        this.menuService = useService("menu");
        let company = null;
        try {
            company = useService("company");
        } catch {
            company = null;
        }
        this.company = company;
        this.uiState = useState({ companyMenuOpen: false, fullMenuOpen: false, fullMenuQuery: "" });
    }

    get catalog() {
        return this.shell.getVisibleCatalog(this.shell.state);
    }

    get companyName() {
        return user.activeCompany?.name || "DeployGuard Security";
    }

    get sitesCount() {
        return this.shell.state.payload?.sites_count;
    }

    get availableCompanies() {
        if (!this.company) {
            return [];
        }
        try {
            return Object.values(this.company.availableCompanies || {});
        } catch {
            return [];
        }
    }

    toggleCompanyMenu() {
        this.uiState.companyMenuOpen = !this.uiState.companyMenuOpen;
    }

    selectCompany(companyId) {
        this.uiState.companyMenuOpen = false;
        if (this.company && companyId !== user.activeCompany?.id) {
            try {
                this.company.setCompanies("loginto", companyId);
            } catch (e) {
                console.warn("DeployGuard Shell: company switch failed", e);
            }
        }
    }

    onSearchInput(ev) {
        this.shell.state.searchQuery = ev.target.value;
    }

    isGroupOpen(group) {
        // Read through this.shell.state (this component's own useState-
        // wrapped proxy) rather than delegating to shellService's
        // isGroupOpen(), which reads via a different, untracked reactive
        // proxy closed over inside the service — that read wouldn't
        // register as a dependency of THIS component's render.
        return !!this.shell.state.openGroups[group.key];
    }

    toggleGroup(group) {
        this.shell.toggleGroup(group.key);
    }

    onHomeClick() {
        this.action.doAction("security_base.action_deployguard_main_command_center", {
            clearBreadcrumbs: true,
        });
    }

    leafCount(leaf) {
        const counts = this.shell.state.payload?.nav_counts;
        if (!leaf.countKey || !counts) {
            return null;
        }
        const value = counts[leaf.countKey];
        return typeof value === "number" ? value : null;
    }

    isMissing(leaf) {
        if (leaf.soon) {
            return false;
        }
        if (!leaf.action) {
            return true;
        }
        if (this.shell.state.resolving) {
            return false;
        }
        return !this.shell.isResolved(leaf.action, this.shell.state);
    }

    onLeafClick(leaf) {
        if (leaf.soon || this.isMissing(leaf)) {
            return;
        }
        this.action.doAction(leaf.action, { clearBreadcrumbs: true }).catch((e) => {
            console.error("DeployGuard Shell: failed to open", leaf.action, e);
        });
    }

    /** Completeness guarantee: the curated tree is a deliberate subset
     * (HANDOFF §5.5). "Full menu" falls back to Odoo's own menu service —
     * every menu item the user's groups grant them, exactly as before the
     * shell existed — so nothing is ever unreachable, curated or not. */
    toggleFullMenu() {
        this.uiState.fullMenuOpen = !this.uiState.fullMenuOpen;
        this.uiState.fullMenuQuery = "";
    }

    onFullMenuSearch(ev) {
        this.uiState.fullMenuQuery = ev.target.value;
    }

    get fullMenuGroups() {
        let allMenus = [];
        try {
            allMenus = this.menuService.getAll() || [];
        } catch (e) {
            console.warn("DeployGuard Shell: menu service unavailable for full menu", e);
            return [];
        }
        const query = (this.uiState.fullMenuQuery || "").trim().toLowerCase();
        const byId = new Map(allMenus.map((m) => [m.id, m]));
        const apps = new Map();

        for (const item of allMenus) {
            const hasAction = item.actionID || (item.action && item.action !== "");
            if (!hasAction || item.id === "root") {
                continue;
            }
            if (query && !item.name.toLowerCase().includes(query)) {
                continue;
            }
            const app = byId.get(item.appID) || item;
            const appLabel = app.name || "Other";
            if (!apps.has(item.appID)) {
                apps.set(item.appID, { key: item.appID, label: appLabel, items: [] });
            }
            apps.get(item.appID).items.push(item);
        }

        return [...apps.values()]
            .filter((g) => g.items.length)
            .sort((a, b) => a.label.localeCompare(b.label));
    }

    onFullMenuItemClick(item) {
        this.menuService.selectMenu(item);
        this.uiState.fullMenuOpen = false;
    }
}
