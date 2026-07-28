/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("deployguard_manager_tour", {
    url: "/web",
    steps: () => [
        {
            trigger: "body",
            content: "Welcome to the DogForce Manager Command Center! Let's get your roster workflow set up.",
            position: "bottom",
        },
        {
            trigger: ".o_roster_board, .o_tour_roster_board, a:contains('Roster Board')",
            content: "Here's your Command Center – the Roster Board. See all your client posts at a glance.",
            position: "bottom",
        },
        {
            trigger: ".rb-stat-card, .o_tour_unassigned_cell, .rh-stat-card-amber",
            content: "Red and amber cells highlight missing guard coverage. Click any cell to assign or replace.",
            position: "right",
        },
        {
            trigger: ".o_roster_auto_fill_btn, button:contains('Auto-Assign')",
            content: "Click 'Auto-Assign' and let AI assign available guards based on proximity, grade, and fairness.",
            position: "bottom",
        },
    ]
});
