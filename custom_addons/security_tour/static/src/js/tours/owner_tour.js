/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("deployguard_owner_tour", {
    url: "/web",
    steps: () => [
        {
            trigger: "body",
            content: "Welcome, Executive! Your Executive Dashboard shows live company health and operations.",
            position: "bottom",
        },
        {
            trigger: ".o_exec_dashboard_health, .o_tour_exec_health_card, a:contains('Executive Dashboard')",
            content: "Attendance rates, payroll costs, and unbilled revenue – all live in real time.",
            position: "bottom",
        },
        {
            trigger: ".o_ai_anomaly_card, .o_tour_ai_anomaly_card, div:contains('Anomalies')",
            content: "The AI Engine flags cost spikes and overtime anomalies before they hit payroll.",
            position: "right",
        },
        {
            trigger: ".o_zuri_chat_input, .o_tour_zuri_chat_launcher, button:contains('Zuri')",
            content: "And you can ask Zuri questions like 'Which sites are understaffed today?' or 'Show monthly profit forecast'.",
            position: "left",
        },
    ]
});
