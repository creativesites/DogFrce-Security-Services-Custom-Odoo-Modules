/** @odoo-module **/

import { Component, useState, useRef, onMounted } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { NAV_CATALOG } from "./nav_catalog";

export class ShellCommandPalette extends Component {
    static template = "security_shell.ShellCommandPalette";
    static props = { "*": true };

    setup() {
        const shellService = useService("deployguard_shell");
        this.shell = { ...shellService, state: useState(shellService.state) };
        this.action = useService("action");
        this.uiState = useState({ query: "" });
        this.inputRef = useRef("paletteInput");

        onMounted(() => {
            this.inputRef.el?.focus();
        });
    }

    get results() {
        const query = this.uiState.query.trim().toLowerCase();
        const isOwner = this.shell.state.roles.isOwner;
        const rows = [];
        for (const group of NAV_CATALOG) {
            if (group.owner && !isOwner) {
                continue;
            }
            for (const subgroup of group.children) {
                for (const leaf of subgroup.children) {
                    if (leaf.soon || !leaf.action) {
                        continue;
                    }
                    if (leaf.owner && !isOwner) {
                        continue;
                    }
                    if (!this.shell.isResolved(leaf.action, this.shell.state)) {
                        continue;
                    }
                    const haystack = `${group.label} ${subgroup.label} ${leaf.label}`.toLowerCase();
                    if (query && !haystack.includes(query)) {
                        continue;
                    }
                    rows.push({ group, subgroup, leaf });
                    if (rows.length >= 30) {
                        return rows;
                    }
                }
            }
        }
        return rows;
    }

    onInput(ev) {
        this.uiState.query = ev.target.value;
    }

    onRowClick(row) {
        this.close();
        this.action.doAction(row.leaf.action, { clearBreadcrumbs: true });
    }

    onKeyDown(ev) {
        if (ev.key === "Escape") {
            this.close();
        } else if (ev.key === "Enter") {
            const first = this.results[0];
            if (first) {
                this.onRowClick(first);
            }
        }
    }

    close() {
        this.shell.state.paletteOpen = false;
    }
}
