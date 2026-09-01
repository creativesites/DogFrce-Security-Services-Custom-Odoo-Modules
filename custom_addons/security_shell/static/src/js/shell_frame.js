/** @odoo-module **/

import { onMounted, onWillUnmount, useState } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { WebClient } from "@web/webclient/webclient";
import { ShellRail } from "./shell_rail";
import { ShellNavPanel } from "./shell_nav_panel";
import { ShellCommandPalette } from "./shell_command_palette";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        const shellService = useService("deployguard_shell");
        // shellService's reactive state has no callback of its own. Owl's
        // reactive tracking is per-proxy-instance, not per-target — reads
        // must go through a proxy that was itself created with useState(),
        // or no render ever gets subscribed. Without this, WebClient's own
        // template (t-if="shell.state.expanded" / "shell.state.paletteOpen",
        // inserted via t-inherit) never re-renders when those flags change,
        // even though the state itself mutates fine.
        this.shell = { ...shellService, state: useState(shellService.state) };
        this.shellActionService = useService("action");

        this._onShellKeyDown = this._onShellKeyDown.bind(this);
        this._onShellUiUpdated = this._onShellUiUpdated.bind(this);

        onMounted(() => {
            window.addEventListener("keydown", this._onShellKeyDown);
            try {
                this.env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", this._onShellUiUpdated);
            } catch (e) {
                // Bus API shape changed upstream — highlighting degrades gracefully.
            }
            this._onShellUiUpdated();
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this._onShellKeyDown);
            try {
                this.env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", this._onShellUiUpdated);
            } catch (e) {
                // no-op
            }
        });
    },

    _onShellUiUpdated() {
        try {
            const controller = this.shellActionService.currentController;
            const action = controller && controller.action;
            if (!action) {
                return;
            }
            this.shell.setActiveController(action.id, action.tag);
        } catch (e) {
            // Never let highlighting bugs break navigation.
        }
    },

    _onShellKeyDown(ev) {
        const isCmdK = (ev.metaKey || ev.ctrlKey) && ev.key.toLowerCase() === "k";
        if (isCmdK) {
            ev.preventDefault();
            this.shell.state.paletteOpen = !this.shell.state.paletteOpen;
            return;
        }
        if (ev.key === "Escape" && this.shell.state.paletteOpen) {
            this.shell.state.paletteOpen = false;
        }
    },
});

WebClient.components = {
    ...WebClient.components,
    ShellRail,
    ShellNavPanel,
    ShellCommandPalette,
};
