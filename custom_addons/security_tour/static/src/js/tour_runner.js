/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { TourCtaModal } from "./tour_cta_modal";

// Defined Tour Steps
export const TOUR_DEFINITIONS = {
    deployguard_prospect_demo_tour: {
        name: "3-Minute Prospect Demo Tour",
        isProspect: true,
        steps: [
            {
                title: "Welcome to DeployGuard",
                content: "DeployGuard eliminates ghost guards, prevents double-booking, and automates your security payroll natively. Let's explore the core platform in 3 minutes!",
                actionXmlId: null,
                targetSelector: null,
            },
            {
                title: "Rostering Hub — Auto-fill Magic",
                content: "Click 'Auto-Assign' and DeployGuard's AI engine fills every empty shift with the best available guard in seconds based on grade, proximity, and rest rules.",
                actionXmlId: "security_shift_planner.action_rostering_hub",
                targetSelector: ".o_roster_auto_fill_btn, .rh-topbar-actions button.rh-btn-success, button:contains('Auto-Assign')",
            },
            {
                title: "WhatsApp Field Command",
                content: "Supervisors don't need a heavy mobile app. They simply send a WhatsApp message like 'STATUS' or 'AWOL John' – and DeployGuard updates attendance instantly.",
                actionXmlId: "security_ai_whatsapp_bridge.action_whatsapp_dashboard_client",
                targetSelector: ".o_whatsapp_simulator_card, .o_tour_whatsapp_sim, div:contains('WhatsApp')",
            },
            {
                title: "Native Tax & Statutory Payroll",
                content: "All guard hours auto-calculate from confirmed rosters. Statutory compliance (NAPSA, NHIMA, PAYE) is natively computed and 100% audit-ready.",
                actionXmlId: "security_payroll_core.action_security_payroll_command_center",
                targetSelector: ".o_payroll_statutory_badge, .o_tour_payroll_stat, div:contains('Payroll')",
            },
            {
                title: "Revenue & Billing Command",
                content: "Track every invoice, billing rate, and outstanding client revenue in real-time. Zero unbilled guard shifts.",
                actionXmlId: "security_billing.action_revenue_dashboard",
                targetSelector: ".o_revenue_summary_card, .o_tour_revenue_card, div:contains('Revenue')",
            },
        ]
    },
    deployguard_supervisor_tour: {
        name: "Field Supervisor Onboarding",
        isProspect: false,
        steps: [
            {
                title: "Field Operator Console",
                content: "Welcome to the DogForce Supervisor Console! Let's get you set up to manage site postings and attendance in 2 minutes.",
                actionXmlId: null,
                targetSelector: null,
            },
            {
                title: "Posting Sheet Console",
                content: "Your primary workspace is the Posting Sheet. Open today's sheet to record check-ins and site shifts.",
                actionXmlId: "security_attendance.action_attendance_posting_console",
                targetSelector: ".o_posting_console_card, .o_tour_posting_console_nav",
            },
            {
                title: "Marking Guards Present",
                content: "Tap 'Present' when a guard arrives at their post. Their shift times auto-fill based on roster rules.",
                actionXmlId: "security_attendance.action_attendance_posting_console",
                targetSelector: ".o_tour_posting_present_btn, button:contains('Present')",
            },
            {
                title: "AWOL Standby Replacements",
                content: "If a guard fails to show, tap 'AWOL'. DeployGuard immediately calculates the nearest eligible standby guard.",
                actionXmlId: "security_attendance.action_attendance_posting_console",
                targetSelector: ".o_tour_posting_awol_btn, button:contains('AWOL')",
            },
        ]
    },
    deployguard_manager_tour: {
        name: "Operations Manager Command",
        isProspect: false,
        steps: [
            {
                title: "Roster Board Command Center",
                content: "Welcome, Manager! Here is your Roster Board where you manage site coverage across all client locations.",
                actionXmlId: "security_shift_planner.action_roster_board",
                targetSelector: ".o_roster_board, .rb-shell",
            },
            {
                title: "Gap & Conflict Detection",
                content: "Red and amber cells highlight missing guard slots. Click any cell to assign or swap guards.",
                actionXmlId: "security_shift_planner.action_roster_board",
                targetSelector: ".rb-stat-card, .o_tour_unassigned_cell",
            },
            {
                title: "AI Auto-Assignment",
                content: "Click 'Auto-Assign' to let DeployGuard assign eligible guards based on reliability, rest hours, and grade requirements.",
                actionXmlId: "security_shift_planner.action_roster_board",
                targetSelector: "button:contains('Auto-Assign')",
            },
            {
                title: "Roster Confirmation Lock",
                content: "When coverage is 100%, confirm the roster to publish schedules directly to field supervisors.",
                actionXmlId: "security_shift_planner.action_roster_board",
                targetSelector: "button:contains('Confirm')",
            },
        ]
    },
    deployguard_owner_tour: {
        name: "Executive & Owner Command",
        isProspect: false,
        steps: [
            {
                title: "Executive Business Health",
                content: "Welcome, Executive! Track attendance rates, payroll expense, and live revenue totals updated in real time.",
                actionXmlId: "security_reporting.action_security_executive_dashboard",
                targetSelector: ".o_exec_dashboard_health, .o_tour_exec_health_card",
            },
            {
                title: "AI Anomaly Detection",
                content: "DeployGuard's AI automatically flags cost spikes, unbilled shifts, and overtime anomalies before payroll runs.",
                actionXmlId: "security_reporting.action_security_executive_dashboard",
                targetSelector: ".o_ai_anomaly_card, .o_tour_ai_anomaly_card",
            },
            {
                title: "Zuri AI Assistant",
                content: "Ask Zuri natural language questions like 'Which sites are understaffed today?' or 'Generate monthly revenue forecast'.",
                actionXmlId: "security_reporting.action_security_executive_dashboard",
                targetSelector: ".o_zuri_chat_input, .o_tour_zuri_chat_launcher",
            },
        ]
    }
};

export class TourRunnerOverlay extends Component {
    static template = "security_tour.TourRunnerOverlay";
    static components = { TourCtaModal };
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.state = useState({
            active: false,
            tourId: null,
            tourName: "",
            stepIndex: 0,
            showCtaModal: false,
        });

        // Explicitly bind methods to 'this' so OWL event listeners never lose context
        this.nextStep = this.nextStep.bind(this);
        this.closeTour = this.closeTour.bind(this);
        this.closeCtaModal = this.closeCtaModal.bind(this);
        this.startTour = this.startTour.bind(this);

        // Store reference globally so systray launcher can start tours
        window.__deployguard_tour_runner__ = this;
    }

    async startTour(technicalName) {
        const def = TOUR_DEFINITIONS[technicalName];
        if (!def) {
            console.warn(`[DeployGuard Tour] Unknown tour identifier: ${technicalName}`);
            return;
        }

        this.state.tourId = technicalName;
        this.state.tourName = def.name;
        this.state.stepIndex = 0;
        this.state.active = true;
        this.state.showCtaModal = false;

        await this._renderCurrentStep();
    }

    get currentStep() {
        if (!this.state.tourId || !TOUR_DEFINITIONS[this.state.tourId]) {
            return {};
        }
        const steps = TOUR_DEFINITIONS[this.state.tourId].steps;
        return steps[this.state.stepIndex] || {};
    }

    get totalSteps() {
        if (!this.state.tourId || !TOUR_DEFINITIONS[this.state.tourId]) {
            return 0;
        }
        return TOUR_DEFINITIONS[this.state.tourId].steps.length;
    }

    async _renderCurrentStep() {
        this._removeHighlights();
        const step = this.currentStep;

        // 1. Navigate to action if step specifies an actionXmlId
        if (step.actionXmlId) {
            try {
                await this.actionService.doAction(step.actionXmlId, { clearBreadcrumbs: true });
            } catch (_e) {
                // Ignore navigation error if already on view
            }
        }

        // 2. Wait briefly for OWL view rendering
        setTimeout(() => {
            if (step.targetSelector) {
                const elem = document.querySelector(step.targetSelector);
                if (elem) {
                    elem.classList.add("o_tour_highlight_pulse");
                    elem.scrollIntoView({ behavior: "smooth", block: "center" });
                }
            }
        }, 600);
    }

    async nextStep() {
        if (this.state.stepIndex + 1 < this.totalSteps) {
            this.state.stepIndex += 1;
            await this._renderCurrentStep();
        } else {
            await this._finishTour();
        }
    }

    async _finishTour() {
        this._removeHighlights();
        const tourId = this.state.tourId;
        const isProspect = TOUR_DEFINITIONS[tourId] && TOUR_DEFINITIONS[tourId].isProspect;

        this.state.active = false;

        // Mark tour as completed on user record
        try {
            await this.orm.call("res.users", "action_complete_tour", [tourId]);
        } catch (_e) {}

        if (isProspect) {
            this.state.showCtaModal = true;
        }
    }

    closeTour() {
        this._removeHighlights();
        this.state.active = false;
    }

    closeCtaModal() {
        this.state.showCtaModal = false;
    }

    _removeHighlights() {
        document.querySelectorAll(".o_tour_highlight_pulse").forEach((el) => {
            el.classList.remove("o_tour_highlight_pulse");
        });
    }

    get popoverStyle() {
        // Floating position styling
        return "position: fixed; bottom: 24px; right: 24px; z-index: 100000; width: 360px;";
    }
}

// Add TourRunnerOverlay to main web client body via service
export const tourRunnerService = {
    dependencies: ["action", "orm"],
    start(env) {
        // Mounted by top-level web client
    }
};

registry.category("main_components").add("DeployGuardTourRunner", {
    Component: TourRunnerOverlay,
});
