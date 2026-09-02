/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

/** Maps a real (live, not hand-listed) section name to one of a small,
 * coherent icon set by keyword — so new sections that appear in Odoo's
 * menu tree still get a sensible icon instead of a random letter, without
 * needing a name-by-name lookup table to keep in sync. */
const ICON_RULES = [
    [/operation/i, "operations"],
    [/roster|schedul|shift/i, "calendar"],
    [/workforce|people|employee|guard/i, "people"],
    [/payroll|finance|billing|invoic/i, "payroll"],
    [/client|site\b/i, "building"],
    [/equipment|asset/i, "package"],
    [/fleet|transport|vehicle/i, "truck"],
    [/report|analytic|dashboard/i, "chart"],
    [/whatsapp|message|chat/i, "message"],
    [/help/i, "help"],
    [/config|setting|admin/i, "settings"],
    [/notification/i, "bell"],
    [/reconcil|migration|sync/i, "link"],
];

function iconForLabel(label) {
    const match = ICON_RULES.find(([re]) => re.test(label || ""));
    return match ? match[1] : "folder";
}

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
                icon: iconForLabel(node.name),
                children: (node.childrenTree || []).slice(0, 12),
                hasAction: !!node.actionID,
            }));
    }

    get userName() {
        return user.name || "My profile";
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

    isActive(item) {
        const st = this.shell.state;
        return st.activeMenuId === item.id || st.activeMenuAncestorIds.includes(item.id);
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

    onAppLauncherClick() {
        this.shell.toggleAppLauncher();
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
