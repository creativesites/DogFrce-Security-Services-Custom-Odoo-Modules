/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class TourCtaModal extends Component {
    static template = "security_tour.TourCtaModal";
    static props = {
        close: Function,
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            name: "",
            phone: "",
            submitting: false,
            submitted: false,
        });
    }

    async submitLead() {
        if (!this.state.name || !this.state.phone) {
            this.notification.add("Please enter your name and contact phone number.", { type: "warning" });
            return;
        }

        this.state.submitting = true;
        try {
            // Save lead inquiry notification
            await this.orm.create("security.notification", [{
                title: `Demo Tour Trial Request: ${this.state.name}`,
                body: `Prospect ${this.state.name} requested a trial setup. Phone: ${this.state.phone}`,
                notification_type: 'system',
                severity: 'high',
            }]);
            this.state.submitted = true;
        } catch (_e) {
            this.state.submitted = true;
        } finally {
            this.state.submitting = false;
        }
    }

    close() {
        this.props.close();
    }
}
