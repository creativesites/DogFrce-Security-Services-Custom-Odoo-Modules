/** @odoo-module **/

import { Component, useState, onWillStart, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class TourSystrayMenu extends Component {
    static template = "security_tour.TourSystray";
    static props = {};

    setup() {
        this.rootRef = useRef("root");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.tourService = useService("tour_service");
        this.state = useState({
            open: false,
            tours: [],
        });

        // Close dropdown when clicking outside
        this.onOutsideClick = (ev) => {
            if (this.state.open && this.rootRef.el && !this.rootRef.el.contains(ev.target)) {
                this.state.open = false;
            }
        };

        onMounted(() => {
            document.addEventListener("click", this.onOutsideClick, true);
        });

        onWillUnmount(() => {
            document.removeEventListener("click", this.onOutsideClick, true);
        });

        onWillStart(async () => {
            await this.loadTours();
        });
    }

    async loadTours() {
        try {
            const list = await this.orm.call("security.tour.definition", "get_available_tours_rpc", []);
            this.state.tours = list;
        } catch (_e) {
            this.state.tours = [];
        }
    }

    toggleDropdown(ev) {
        if (ev) {
            ev.stopPropagation();
        }
        this.state.open = !this.state.open;
        if (this.state.open) {
            this.loadTours();
        }
    }

    async launchTour(technicalName) {
        this.state.open = false;
        if (window.__deployguard_tour_runner__) {
            window.__deployguard_tour_runner__.startTour(technicalName);
        } else if (this.tourService) {
            this.tourService.startTour(technicalName);
        }
    }
}

registry.category("systray").add("security_tour.systray", {
    Component: TourSystrayMenu,
    sequence: 15,
});
