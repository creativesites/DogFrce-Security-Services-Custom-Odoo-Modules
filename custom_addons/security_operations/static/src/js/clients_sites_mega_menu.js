/** @odoo-module **/

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

/**
 * Clients & Sites command center — cut down to four destinations plus one
 * primary action, per docs/ROSTERING_SIMPLIFICATION_PLAN.md Task 3.
 *
 * This used to be a 5-tab, 15-card launchpad the GM described as "let it be
 * clear, completely clear". There is now exactly one thing to do first (set
 * up a new client, via the onboarding wizard) and four places to go
 * afterwards (Clients, Sites, Contracts, Shift Requirements). Search and
 * tabs were removed with the cards they existed to filter.
 *
 * Soft dependency note: the primary CTA and the Clients card open actions
 * from security_client_onboarding, which security_operations does not
 * formally depend on (the dependency runs the other way — onboarding depends
 * on operations). If that module is ever uninstalled while this one stays
 * installed, `openAction` below degrades to a notification rather than a
 * crash. In practice the two are always installed together; see
 * DEPLOYMENT_SCOPE_AND_EXCLUSIONS.md, which should list
 * security_client_onboarding as part of the baseline and currently does not.
 */
export class ClientsSitesMegaMenu extends Component {
    static template = "security_operations.ClientsSitesMegaMenu";
    static props = { "*": true };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

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
                this.action.doAction("security_operations.action_security_client_site", { clearBreadcrumbs: true });
            } catch (e) {
                console.error("Failed to navigate to Client Sites on close:", e);
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
                this.notification.add("That screen isn't available right now.", { type: "danger" });
            }
        }
    }
}

registry.category("actions").add("security_operations.clients_sites_mega_menu", ClientsSitesMegaMenu);
