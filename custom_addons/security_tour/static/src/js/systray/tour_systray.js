/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class TourSystrayMenu extends Component {
    static template = "security_tour.TourSystray";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.tourService = useService("tour_service");
        this.state = useState({
            open: false,
            tours: [],
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

    toggleDropdown() {
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
