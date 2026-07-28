/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("deployguard_prospect_demo_tour", {
    url: "/web",
    rainbowMan: true,
    steps: () => [
        {
            trigger: "body",
            content: "Welcome to DeployGuard! Let's see how it eliminates ghost guards and automates your payroll in about 3 minutes.",
            position: "bottom",
        },
        {
            trigger: ".o_roster_auto_fill_btn, .rh-topbar-actions button.rh-btn-success, button:contains('Auto-Assign')",
            content: "Rostering Hub — Click 'Auto-Assign' and DeployGuard fills every empty shift with the best available guard in seconds. Zero spreadsheets.",
            position: "bottom",
        },
        {
            trigger: ".o_menu_entry_whatsapp, .o_whatsapp_simulator_card, a:contains('WhatsApp')",
            content: "Your supervisors don't need an app. They just text WhatsApp commands like 'STATUS' or 'AWOL John' – DeployGuard updates live.",
            position: "right",
        },
        {
            trigger: ".o_menu_entry_payroll, .o_payroll_statutory_badge, a:contains('Payroll')",
            content: "All guard hours are calculated straight from the roster. NAPSA, NHIMA, and PAYE statutory rules are natively handled and audit-ready.",
            position: "bottom",
        },
        {
            trigger: ".o_menu_entry_revenue_dashboard, .o_revenue_summary_card, a:contains('Revenue')",
            content: "Track every invoice, guard billing rate, and outstanding revenue in real-time. Zero under-billing.",
            position: "left",
        },
        {
            trigger: "body",
            content: "Ready to see it with your own data? Let me help schedule your free trial setup!",
            position: "bottom",
        },
    ]
});
