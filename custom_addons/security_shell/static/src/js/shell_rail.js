/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

/** Curated quick-jump list — a subset of the full nav_catalog, matching
 * HANDOFF §5.2 point 4 exactly: "Home · Operations · Rostering · People ·
 * Payroll & Finance · Reports". */
const RAIL_ITEMS = [
    { key: "home", label: "Home", icon: "home" },
    { key: "operations", label: "Operations", icon: "operations", groupKey: "operations" },
    { key: "rostering", label: "Rostering", icon: "rostering", groupKey: "rostering" },
    { key: "people", label: "People", icon: "people", groupKey: "people" },
    { key: "payroll_finance", label: "Payroll & Finance", icon: "payroll", groupKey: "payroll_finance", owner: true },
    { key: "reporting_platform", label: "Reports", icon: "reports", groupKey: "reporting_platform" },
];

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

        onMounted(() => {
            // Activate shell CSS (hides Odoo navbar, enables shell layout).
            // Only fires after all component setup has succeeded.
            document.body.classList.add("dgs-shell-active");
        });

        onWillUnmount(() => {
            document.body.classList.remove("dgs-shell-active");
        });
    }

    get railItems() {
        return RAIL_ITEMS.filter((item) => !item.owner || this.shell.state.roles.isOwner);
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

    get logoUrl() {
        return "/security_theme/static/src/img/deployguard.png";
    }

    isActive(item) {
        if (item.key === "home") {
            return this.shell.state.isHome;
        }
        return this.shell.state.activeGroupKey === item.groupKey;
    }

    onItemClick(item) {
        if (item.key === "home") {
            this.action.doAction("security_base.action_deployguard_main_command_center", {
                clearBreadcrumbs: true,
            });
            return;
        }
        this.shell.setExpanded(true);
        this.shell.openGroup(item.groupKey);
    }

    onToggleClick() {
        this.shell.toggleExpanded();
    }

    onAppSwitcherClick() {
        // Reuses the existing DogForce app launcher overlay (security_theme).
        const navbar = document.querySelector(".o_main_navbar .dfal-apps-toggler");
        if (navbar) {
            navbar.click();
        }
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
