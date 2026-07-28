/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("deployguard_supervisor_tour", {
    url: "/web",
    steps: () => [
        {
            trigger: "body",
            content: "Welcome to the DogForce team! Let's get you set up in 2 minutes.",
            position: "bottom",
        },
        {
            trigger: ".o_posting_console_card, .o_tour_posting_console_nav, a:contains('Posting Sheets')",
            content: "Your main tool is the Posting Sheet. Open it to manage guard check-ins at client sites.",
            position: "bottom",
        },
        {
            trigger: ".o_tour_posting_present_btn, button:contains('Present')",
            content: "Mark a guard present by tapping here. Their shift start and end times auto-fill.",
            position: "right",
        },
        {
            trigger: ".o_tour_posting_awol_btn, button:contains('AWOL')",
            content: "If a guard doesn't show up, tap AWOL. DeployGuard immediately suggests an eligible standby replacement.",
            position: "left",
        },
    ]
});
