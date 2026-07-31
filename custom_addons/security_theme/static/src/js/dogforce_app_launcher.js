/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class DogForceAppLauncher extends Component {
    static template = "security_theme.DogForceAppLauncher";
    static props = {
        closeLauncher: { type: Function, optional: true },
    };

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.state = useState({
            searchQuery: "",
        });

        this.onKeyDown = this.onGlobalKeyDown.bind(this);

        onMounted(() => {
            window.addEventListener("keydown", this.onKeyDown);
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this.onKeyDown);
        });
    }

    get companyName() {
        return user.activeCompany?.name || "DogForce Security";
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
        }
    }
}
