/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class ShellRail extends Component {
    static template = "security_shell.ShellRail";
    static props = { "*": true };

    setup() {
        const shellService = useService("deployguard_shell");
        // shellService's reactive state has no callback of its own (it's a
        // shared singleton, not owned by any one component). Owl's reactive
        // tracking is per-proxy-instance, not per-target — reads must go
        // through a proxy that was itself created with useState(), or no
        // render ever gets subscribed. Wrapping .state locally (methods are
        // plain closures over the shared raw state, so they still mutate it
        // correctly) is what actually wires this component's re-render.
        this.shell = { ...shellService, state: useState(shellService.state) };
        this.action = useService("action");
        this.menuService = useService("menu");
        useBus(this.env.bus, "MENUS:APP-CHANGED", () => this.render(true));
        this.uiState = useState({ appSwitcherOpen: false });

        onMounted(() => {
            // Activate shell CSS (hides Odoo navbar, enables shell layout).
            // Only fires after all component setup has succeeded.
            document.body.classList.add("dgs-shell-active");
        });

        onWillUnmount(() => {
            document.body.classList.remove("dgs-shell-active");
        });
    }

    get currentApp() {
        return this.menuService.getCurrentApp() || this.menuService.getApps()[0] || null;
    }

    /** Rail quick-jump icons — the current app's real top-level menu
     * sections, live from menuService (never a hand-maintained list that
     * can drift out of sync with what actually exists). */
    get railItems() {
        const app = this.currentApp;
        if (!app) {
            return [];
        }
        const tree = this.menuService.getMenuAsTree(app.id);
        return (tree.childrenTree || [])
            .filter((node) => node.id !== "root")
            .map((node) => ({
                id: node.id,
                label: node.name,
                initial: (node.name || "?").trim().charAt(0).toUpperCase(),
                children: (node.childrenTree || []).slice(0, 12),
                hasAction: !!node.actionID,
            }));
    }

    get apps() {
        return this.menuService.getApps();
    }

    get userInitials() {
        const name = user.name || "";
        return name
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((part) => part[0].toUpperCase())
            .join("") || "?";
    }

    /** The site's own logo (company branding), not a fixed DeployGuard
     * asset — this tile is now the app switcher, so it should show what the
     * customer actually operates under. */
    get logoUrl() {
        const companyId = user.activeCompany?.id;
        return companyId ? `/web/image/res.company/${companyId}/logo` : "/web/static/img/logo.png";
    }

    isActive(item) {
        // activeGroupKey is still populated from the old curated-catalog
        // resolver (shell_service.js's findByActionResId), which doesn't
        // know about live menu ids — rail highlighting against the real
        // tree is a follow-up, not wired yet. Never mis-highlight in the
        // meantime.
        return false;
    }

    onItemClick(item) {
        this.shell.setExpanded(true);
        this.shell.toggleMenuNode(item.id);
        if (item.hasAction) {
            this.menuService.selectMenu(this.menuService.getMenu(item.id));
        }
    }

    onFlyoutChildClick(child) {
        this.menuService.selectMenu(child);
    }

    onHomeClick() {
        this.action.doAction("security_base.action_deployguard_main_command_center", {
            clearBreadcrumbs: true,
        });
    }

    onToggleClick() {
        this.shell.toggleExpanded();
    }

    toggleAppSwitcher() {
        this.uiState.appSwitcherOpen = !this.uiState.appSwitcherOpen;
    }

    onAppClick(app) {
        this.uiState.appSwitcherOpen = false;
        this.menuService.selectMenu(app);
    }

    onSettingsClick() {
        this.action.doAction("base_setup.action_general_configuration", {
            clearBreadcrumbs: true,
        });
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
}
