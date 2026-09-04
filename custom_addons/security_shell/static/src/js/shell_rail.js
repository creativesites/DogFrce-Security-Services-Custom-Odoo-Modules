/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { useService, useBus } from "@web/core/utils/hooks";
import { usePopover } from "@web/core/popover/popover_hook";
import { user } from "@web/core/user";
import { ShellRailFlyout } from "./shell_rail_flyout";
import { ShellProfileCard } from "./shell_profile_card";

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

/** Fully-expanded, depth-annotated flatten of a menu node's subtree for the
 * hover preview — deliberately not click-to-drill like the sidebar tree,
 * since this is a transient hover surface where drilling would cost more
 * hovers than it saves. Capped so a huge section (Configuration) doesn't
 * produce a popover taller than the screen. */
function flattenPreview(node, cap = 40) {
    const rows = [];
    const walk = (n, depth) => {
        if (rows.length >= cap) {
            return;
        }
        for (const child of n.childrenTree || []) {
            if (rows.length >= cap) {
                return;
            }
            const hasChildren = !!(child.childrenTree && child.childrenTree.length);
            rows.push({
                id: child.id,
                label: child.name,
                depth,
                clickable: !!child.actionID,
                menu: child,
            });
            if (hasChildren) {
                walk(child, depth + 1);
            }
        }
    };
    walk(node, 0);
    return rows;
}

const HOVER_OPEN_DELAY = 220;
const HOVER_CLOSE_DELAY = 160;

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

        // Every rail icon's hover feedback (plain name tooltip or a full
        // section preview) goes through one popover instance, portalled by
        // Odoo's own popover service instead of living inside
        // .dgs-rail-sections — that container scrolls vertically once there
        // are more top-level sections than fit on screen, and CSS overflow
        // clipping on a scrolling ancestor silently crops a plain
        // position:absolute/fixed descendant, which is exactly why a
        // hand-rolled CSS-only flyout there couldn't be trusted to show.
        this.flyout = usePopover(ShellRailFlyout, {
            position: "right",
            holdOnHover: true,
            animation: true,
            arrow: true,
            popoverClass: "dgs-rail-popover-shell",
        });
        this._openTimer = null;
        this._closeTimer = null;

        // Click-triggered (not hover), auto-closes on click-away by default —
        // the right behavior for an actionable menu (log out, preferences)
        // rather than a transient preview.
        this.profileMenu = usePopover(ShellProfileCard, {
            position: "right-end",
            animation: true,
            arrow: true,
            popoverClass: "dgs-profile-popover-shell",
        });

        this.sectionsRef = useRef("sections");

        // Keep the active section's icon in view without the user having to
        // scroll for it — most relevant right after navigating somewhere
        // deep in a long rail.
        useEffect(
            () => {
                const el = this.sectionsRef.el?.querySelector(".dgs-rail-item.active");
                el?.scrollIntoView({ block: "nearest" });
            },
            () => [this.shell.state.activeMenuId]
        );

        onMounted(() => {
            // Activate shell CSS (hides Odoo navbar, enables shell layout).
            // Only fires after all component setup has succeeded.
            document.body.classList.add("dgs-shell-active");
        });

        onWillUnmount(() => {
            document.body.classList.remove("dgs-shell-active");
            clearTimeout(this._openTimer);
            clearTimeout(this._closeTimer);
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
                menu: node,
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

    /** ev.currentTarget + either a plain label (simple tooltip) or a menu
     * node (full subtree preview). Used for every rail control, so hovering
     * any icon — including Home, the app switcher, Settings, the avatar —
     * always says what it is; the ones with a real menu node additionally
     * preview their contents for "long hover, then navigate" without a
     * click. */
    onHoverStart(ev, { label, node }) {
        clearTimeout(this._closeTimer);
        clearTimeout(this._openTimer);
        const target = ev.currentTarget;
        this._openTimer = setTimeout(() => {
            const nodes = node ? flattenPreview(node) : [];
            this.flyout.open(target, {
                label: label || node?.name,
                nodes,
                onNavigate: (previewNode) => this.menuService.selectMenu(previewNode.menu),
                onHoverStart: () => clearTimeout(this._closeTimer),
                onHoverEnd: () => this.scheduleClose(),
                close: () => this.flyout.close(),
            });
        }, HOVER_OPEN_DELAY);
    }

    onHoverEnd() {
        clearTimeout(this._openTimer);
        this.scheduleClose();
    }

    scheduleClose() {
        clearTimeout(this._closeTimer);
        this._closeTimer = setTimeout(() => this.flyout.close(), HOVER_CLOSE_DELAY);
    }

    onItemClick(item) {
        clearTimeout(this._openTimer);
        this.flyout.close();
        this.shell.setExpanded(true);
        this.shell.toggleMenuNode(item.id);
        if (item.hasAction) {
            this.menuService.selectMenu(this.menuService.getMenu(item.id));
        }
    }

    onHomeClick() {
        this.flyout.close();
        this.action.doAction("security_base.action_deployguard_main_command_center", {
            clearBreadcrumbs: true,
        });
    }

    onToggleClick() {
        this.shell.toggleExpanded();
    }

    onAppLauncherClick() {
        this.flyout.close();
        this.shell.toggleAppLauncher();
    }

    onSettingsClick() {
        this.flyout.close();
        this.action.doAction("base_setup.action_general_configuration", {
            clearBreadcrumbs: true,
        });
    }

    onAvatarClick(ev) {
        this.flyout.close();
        clearTimeout(this._openTimer);
        if (this.profileMenu.isOpen) {
            this.profileMenu.close();
            return;
        }
        this.profileMenu.open(ev.currentTarget, {});
    }
}
