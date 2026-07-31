/** @odoo-module **/

import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export class EquipmentMegaMenu extends Component {
    static template = "security_equipment.EquipmentMegaMenu";
    static props = { "*": true };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            activeTab: "launchpad", // 'launchpad' | 'catalog' | 'maintenance' | 'custody' | 'guidance'
            searchQuery: "",
        });

        this.onGlobalKeyDown = this.onGlobalKeyDown.bind(this);

        onMounted(() => {
            window.addEventListener("keydown", this.onGlobalKeyDown);
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this.onGlobalKeyDown);
        });
    }

    get companyName() {
        return user.activeCompany?.name || "DogForce Security";
    }

    onGlobalKeyDown(ev) {
        if (ev.key === "Escape") {
            this.close();
        }
    }

    close() {
        if (this.props.closeModal && typeof this.props.closeModal === "function") {
            this.props.closeModal();
        } else {
            try {
                this.action.doAction("security_equipment.action_security_equipment_item", { clearBreadcrumbs: true });
            } catch (e) {
                console.error("Failed to navigate to Equipment on close:", e);
            }
        }
    }

    async openAction(actionXmlId) {
        try {
            if (this.props.closeModal && typeof this.props.closeModal === "function") {
                this.props.closeModal();
            }
            await this.action.doAction(actionXmlId);
        } catch (e) {
            console.error("Failed to open action:", actionXmlId, e);
            if (this.notification) {
                this.notification.add("Action could not be opened: " + actionXmlId, { type: "danger" });
            }
        }
    }

    setTab(tabId) {
        this.state.activeTab = tabId;
    }

    matchesSearch(title, desc, keywords = []) {
        const query = (this.state.searchQuery || "").toLowerCase().trim();
        if (!query) return true;
        const text = `${title} ${desc} ${keywords.join(" ")}`.toLowerCase();
        return text.includes(query);
    }
}

registry.category("actions").add("security_equipment.equipment_mega_menu", EquipmentMegaMenu);
