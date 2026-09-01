/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

/** Priority workspace cards. The Alt+<letter> badges are real shortcuts —
 * a single keydown listener below wires them up. A card whose action xmlid
 * doesn't resolve on this database is hidden rather than shown dead. */
export const PRIORITY_CARDS = [
    { key: "home", altKey: "h", action: "security_base.action_deployguard_main_command_center" },
    { key: "rostering", altKey: "r", action: "security_shift_planner.action_rostering_hub" },
    { key: "workforce", altKey: "w", action: "security_base.action_workforce_dashboard" },
    { key: "clients_sites", altKey: "c", action: "security_operations.action_clients_sites_mega_menu" },
    { key: "equipment", altKey: "e", action: "security_equipment.action_equipment_mega_menu" },
    { key: "fleet", altKey: "f", action: "security_fleet.action_fleet_mega_menu" },
];

export class DogForceAppLauncher extends Component {
    static template = "security_theme.DogForceAppLauncher";
    static props = {
        closeLauncher: { type: Function, optional: true },
    };

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            searchQuery: "",
            resolvedCards: {},
            hasCompanyLogo: false,
        });

        this.onKeyDown = this.onGlobalKeyDown.bind(this);

        onWillStart(async () => {
            await Promise.all([this._resolvePriorityCards(), this._checkCompanyLogo()]);
        });

        onMounted(() => {
            window.addEventListener("keydown", this.onKeyDown);
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this.onKeyDown);
        });
    }

    async _resolvePriorityCards() {
        const modules = [...new Set(PRIORITY_CARDS.map((c) => c.action.split(".")[0]))];
        const names = PRIORITY_CARDS.map((c) => c.action.split(".").slice(1).join("."));
        try {
            const records = await this.orm.searchRead(
                "ir.model.data",
                [["module", "in", modules], ["name", "in", names]],
                ["module", "name"]
            );
            const found = new Set(records.map((r) => `${r.module}.${r.name}`));
            for (const card of PRIORITY_CARDS) {
                this.state.resolvedCards[card.key] = found.has(card.action);
            }
        } catch (e) {
            console.warn("DogForce App Launcher: priority card resolution failed", e);
            for (const card of PRIORITY_CARDS) {
                this.state.resolvedCards[card.key] = true;
            }
        }
    }

    isCardVisible(key) {
        return this.state.resolvedCards[key] !== false;
    }

    async _checkCompanyLogo() {
        const companyId = user.activeCompany?.id;
        if (!companyId) {
            return;
        }
        try {
            const count = await this.orm.searchCount("res.company", [
                ["id", "=", companyId],
                ["logo", "!=", false],
            ]);
            this.state.hasCompanyLogo = count > 0;
        } catch (e) {
            this.state.hasCompanyLogo = false;
        }
    }

    get companyName() {
        return user.activeCompany?.name || "DogForce Security";
    }

    get companyLogoUrl() {
        return this.state.hasCompanyLogo
            ? `/web/image/res.company/${user.activeCompany.id}/logo`
            : "/security_theme/static/src/img/deployguard.png";
    }

    get apps() {
        const allApps = this.menuService.getApps() || [];
        const query = (this.state.searchQuery || "").trim().toLowerCase();
        if (!query) {
            return allApps;
        }
        return allApps.filter(app => {
            const name = (app.name || "").toLowerCase();
            const xmlid = (app.xmlid || "").toLowerCase();
            return name.includes(query) || xmlid.includes(query);
        });
    }

    getAppIconClass(app) {
        const name = (app.name || "").toLowerCase();
        const xmlid = (app.xmlid || "").toLowerCase();

        if (xmlid.includes("security_operations") || name.includes("operations")) {
            return { icon: "fa-shield", bg: "bg-gradient-blue" };
        }
        if (xmlid.includes("security_shift_planner") || name.includes("rostering") || name.includes("scheduling")) {
            return { icon: "fa-calendar", bg: "bg-gradient-purple" };
        }
        if (xmlid.includes("hr") || name.includes("workforce") || name.includes("employee")) {
            return { icon: "fa-users", bg: "bg-gradient-emerald" };
        }
        if (xmlid.includes("security_equipment") || name.includes("equipment") || name.includes("assets")) {
            return { icon: "fa-wrench", bg: "bg-gradient-amber" };
        }
        if (xmlid.includes("security_fleet") || name.includes("fleet") || name.includes("vehicle")) {
            return { icon: "fa-car", bg: "bg-gradient-rose" };
        }
        if (xmlid.includes("security_billing") || name.includes("billing") || name.includes("invoice") || name.includes("accounting")) {
            return { icon: "fa-university", bg: "bg-gradient-teal" };
        }
        if (xmlid.includes("setting") || name.includes("settings")) {
            return { icon: "fa-cogs", bg: "bg-gradient-slate" };
        }
        if (xmlid.includes("ai") || name.includes("assistant")) {
            return { icon: "fa-bolt", bg: "bg-gradient-indigo" };
        }
        return { icon: "fa-th-large", bg: "bg-gradient-primary" };
    }

    selectApp(app) {
        if (app) {
            this.menuService.selectMenu(app);
            this.close();
        }
    }

    openClientAction(actionXmlId) {
        this.actionService.doAction(actionXmlId, { clearBreadcrumbs: true });
        this.close();
    }

    close() {
        if (this.props.closeLauncher) {
            this.props.closeLauncher();
        }
    }

    onGlobalKeyDown(ev) {
        if (ev.key === "Escape") {
            this.close();
            return;
        }
        if (!ev.altKey) {
            return;
        }
        const key = (ev.key || "").toLowerCase();
        const card = PRIORITY_CARDS.find((c) => c.altKey === key);
        if (card && this.isCardVisible(card.key)) {
            ev.preventDefault();
            this.openClientAction(card.action);
        }
    }
}
