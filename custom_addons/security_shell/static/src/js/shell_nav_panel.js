/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
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
        // The menu service isn't itself a reactive object, and switching apps
        // (via the app switcher) doesn't touch anything we track above, so
        // without this the panel would keep showing the previous app's tree
        // until something unrelated happened to force a re-render.
        useBus(this.env.bus, "MENUS:APP-CHANGED", () => this.render(true));
        let company = null;
        try {
            company = useService("company");
        } catch {
            company = null;
        }
        this.company = company;
        this.uiState = useState({ companyMenuOpen: false, fullMenuOpen: false, fullMenuQuery: "" });
    }

    get companyName() {
        return user.activeCompany?.name || "DeployGuard Security";
    }

    get logoUrl() {
        const companyId = user.activeCompany?.id;
        return companyId ? `/web/image/res.company/${companyId}/logo` : "/web/static/img/logo.png";
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

    onHomeClick() {
        this.action.doAction("security_base.action_deployguard_main_command_center", {
            clearBreadcrumbs: true,
        });
    }

    /** The app whose tree this panel renders — defaults to the current app
     * (as set by the app switcher / whatever action is showing), falling
     * back to the first available app if none is current yet. */
    get currentApp() {
        return this.menuService.getCurrentApp() || this.menuService.getApps()[0] || null;
    }

    isNodeOpen(id) {
        // Direct read through this.shell.state (this component's own
        // useState()-wrapped proxy) — see the note on the constructor above;
        // a method call into shellService would read via an untracked proxy.
        return !!this.shell.state.openMenuIds[id];
    }

    toggleNode(id) {
        this.shell.toggleMenuNode(id);
    }

    /** Flattens the LIVE menu tree (real names, real hierarchy, real access
     * control — Odoo already filtered it server-side to what this user's
     * groups grant) into a depth-annotated row list, honoring per-node
     * open/closed state. While searching, every branch containing a match
     * is force-shown and force-expanded; non-matching branches are pruned
     * entirely rather than just hidden, so results aren't buried. */
    get flatRows() {
        const app = this.currentApp;
        if (!app) {
            return [];
        }
        const tree = this.menuService.getMenuAsTree(app.id);
        const query = (this.shell.state.searchQuery || "").trim().toLowerCase();
        const rows = [];

        const subtreeMatches = (node) => {
            if (node.name && node.name.toLowerCase().includes(query)) {
                return true;
            }
            return (node.childrenTree || []).some(subtreeMatches);
        };

        const walk = (nodes, depth) => {
            for (const node of nodes) {
                if (node.id === "root") {
                    continue;
                }
                const children = node.childrenTree || [];
                const hasChildren = children.length > 0;
                const selfMatches = !query || (node.name || "").toLowerCase().includes(query);
                const childMatches = query && hasChildren && children.some(subtreeMatches);
                if (query && !selfMatches && !childMatches) {
                    continue;
                }
                const isOpen = query ? true : this.isNodeOpen(node.id);
                rows.push({
                    id: node.id,
                    label: node.name,
                    depth,
                    hasChildren,
                    isOpen,
                    hasAction: !!node.actionID,
                });
                if (hasChildren && isOpen) {
                    walk(children, depth + 1);
                }
            }
        };

        walk(tree.childrenTree || [], 0);
        return rows;
    }

    onRowClick(row) {
        if (row.hasChildren) {
            this.toggleNode(row.id);
            // A section header can also carry its own action (rare, but
            // real in this tree) — open it too, same as Odoo's own navbar.
        }
        if (row.hasAction) {
            this.menuService.selectMenu(this.menuService.getMenu(row.id));
        }
    }

    /** Secondary, always-complete fallback: every menu item across every
     * app, grouped by app — a global search that doesn't depend on which
     * app's tree the main panel happens to be showing right now. */
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
