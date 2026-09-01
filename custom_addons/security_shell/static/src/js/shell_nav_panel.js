/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class ShellNavPanel extends Component {
    static template = "security_shell.ShellNavPanel";
    static props = { "*": true };

    setup() {
        this.shell = useService("deployguard_shell");
        this.action = useService("action");
        let company = null;
        try {
            company = useService("company");
        } catch {
            company = null;
        }
        this.company = company;
        this.uiState = useState({ companyMenuOpen: false });
    }

    get catalog() {
        return this.shell.getVisibleCatalog();
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
        return this.shell.isGroupOpen(group.key);
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
        return !this.shell.isResolved(leaf.action);
    }

    onLeafClick(leaf) {
        if (leaf.soon || this.isMissing(leaf)) {
            return;
        }
        this.action.doAction(leaf.action, { clearBreadcrumbs: true }).catch((e) => {
            console.error("DeployGuard Shell: failed to open", leaf.action, e);
        });
    }
}
