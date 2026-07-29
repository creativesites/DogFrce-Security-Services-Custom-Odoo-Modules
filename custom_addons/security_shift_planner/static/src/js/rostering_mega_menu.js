/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class RosteringMegaMenu extends Component {
    static template = "security_shift_planner.RosteringMegaMenu";
    static props = { "*": true };

    setup() {
        this.action = useService("action");
        this.state = useState({
            searchQuery: "",
        });
    }

    onKeyDown(ev) {
        if (ev.key === "Escape") {
            this.close();
        }
    }

    close() {
        if (this.props.closeModal) {
            this.props.closeModal();
        } else {
            this.action.doAction("security_shift_planner.action_rostering_hub");
        }
    }

    async openAction(actionXmlId) {
        if (this.props.closeModal) {
            this.props.closeModal();
        }
        await this.action.doAction(actionXmlId);
    }

    isGroupVisible(groupKey) {
        const query = (this.state.searchQuery || "").toLowerCase().trim();
        if (!query) return true;

        const groupTerms = {
            workspaces: ["workspace", "hub", "roster", "board", "checkin", "check-in", "weekly", "kanban", "schedule"],
            planning: ["plan", "planning", "demand", "ai", "smart", "recommendation", "overtime", "profit", "contract"],
            records: ["record", "batch", "slot", "slots", "wizard", "generate", "auto", "week"],
            config: ["config", "rule", "requirement", "post", "shift", "exclusion", "qualification", "cert", "hours"],
        };

        const terms = groupTerms[groupKey] || [];
        return terms.some((t) => t.includes(query) || query.includes(t));
    }
}

registry.category("actions").add("security_shift_planner.rostering_mega_menu", RosteringMegaMenu);
