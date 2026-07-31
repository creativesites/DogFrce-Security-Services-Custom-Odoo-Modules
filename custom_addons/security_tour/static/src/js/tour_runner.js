/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { TourCtaModal } from "./tour_cta_modal";

// Helper function to safely find DOM target elements across native CSS selectors and text matches
export function findTargetElement(selectorString) {
    if (!selectorString) return null;

    const selectors = selectorString.split(",").map((s) => s.trim());

    for (const sel of selectors) {
        try {
            if (!sel.includes(":contains")) {
                const el = document.querySelector(sel);
                if (el && el.offsetWidth > 0 && el.offsetHeight > 0) {
                    return el;
                }
            } else {
                const match = sel.match(/^([a-zA-Z0-9_.-]+)?:contains\(['"](.+)['"]\)/);
                if (match) {
                    const tag = match[1] || "*";
                    const searchText = match[2].toLowerCase();
                    const candidates = document.querySelectorAll(tag);

                    for (const candidate of candidates) {
                        const text = (candidate.textContent || "").toLowerCase();
                        if (text.includes(searchText) && candidate.offsetWidth > 0 && candidate.offsetHeight > 0) {
                            return candidate;
                        }
                    }
                }
            }
        } catch (_e) {
            // Ignore syntax errors and proceed to next candidate
        }
    }
    return null;
}

// Defined Tour Steps with Failsafe Selectors
export const TOUR_DEFINITIONS = {
    deployguard_prospect_demo_tour: {
        name: "3-Minute Prospect Demo Tour",
        isProspect: true,
        steps: [
            {
                title: "Welcome to DogForce",
                content: "DogForce eliminates ghost guards, prevents double-booking, and automates your security payroll natively. Let's explore the core platform in 3 minutes!",
                actionXmlId: null,
                targetSelector: null,
            },
            {
                title: "Rostering Hub — Auto-fill Magic",
                content: "Click 'Auto-Assign' and DogForce's AI engine fills every empty shift with the best available guard in seconds based on grade, proximity, and rest rules.",
                actionXmlId: "security_shift_planner.action_rostering_hub",
                targetSelector: ".rh-btn-success, .rh-topbar-actions, .rh-topbar, .rh-shell, .o_content",
            },
            {
                title: "WhatsApp Field Command",
                content: "Supervisors don't need a heavy mobile app. They simply send a WhatsApp message like 'STATUS' or 'AWOL John' – and DogForce updates attendance instantly.",
                actionXmlId: "security_ai_whatsapp_bridge.action_whatsapp_dashboard_client",
                targetSelector: ".o_whatsapp_simulator_card, .ws-shell, .o_content",
            },
            {
                title: "Native Tax & Statutory Payroll",
                content: "All guard hours auto-calculate from confirmed rosters. Statutory compliance (NAPSA, NHIMA, PAYE) is natively computed and 100% audit-ready.",
                actionXmlId: "security_payroll_core.action_security_payroll_command_center",
                targetSelector: ".pcc-main, .pcc-shell, .o_content",
            },
            {
                title: "Revenue & Billing Command",
                content: "Track every invoice, billing rate, and outstanding client revenue in real-time. Zero unbilled guard shifts.",
                actionXmlId: "security_billing.action_revenue_dashboard",
                targetSelector: ".rev-header, .rev-shell, .o_content",
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
                targetSelector: ".ps-site-card, .ps-grid, .ps-shell, .o_content",
            },
            {
                title: "Marking Guards Present",
                content: "Tap 'Present' when a guard arrives at their post. Their shift times auto-fill based on roster rules.",
                actionXmlId: "security_attendance.action_attendance_posting_console",
                targetSelector: ".ps-btn-present, button:contains('Present'), .ps-grid, .o_content",
            },
            {
                title: "AWOL Standby Replacements",
                content: "If a guard fails to show, tap 'AWOL'. DogForce immediately calculates the nearest eligible standby guard.",
                actionXmlId: "security_attendance.action_attendance_posting_console",
                targetSelector: ".ps-btn-awol, button:contains('AWOL'), .ps-grid, .o_content",
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
                targetSelector: ".rb-shell, .o_roster_board, .o_content",
            },
            {
                title: "Gap & Conflict Detection",
                content: "Red and amber cells highlight missing guard slots. Click any cell to assign or swap guards.",
                actionXmlId: "security_shift_planner.action_roster_board",
                targetSelector: ".rb-stat-card, .rb-shell, .o_content",
            },
            {
                title: "AI Auto-Assignment",
                content: "Click 'Auto-Assign' to let DogForce assign eligible guards based on reliability, rest hours, and grade requirements.",
                actionXmlId: "security_shift_planner.action_roster_board",
                targetSelector: ".rb-btn-auto, button:contains('Auto-Assign'), .rb-shell, .o_content",
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
                targetSelector: ".ed-shell, .ed-kpi-grid, .o_content",
            },
            {
                title: "AI Anomaly Detection",
                content: "DogForce's AI automatically flags cost spikes, unbilled shifts, and overtime anomalies before payroll runs.",
                actionXmlId: "security_reporting.action_security_executive_dashboard",
                targetSelector: ".ed-anomaly-panel, .ed-shell, .o_content",
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
            hasTarget: false,
            targetRect: { top: 0, left: 0, width: 0, height: 0 },
        });

        // Explicitly bind methods to 'this'
        this.nextStep = this.nextStep.bind(this);
        this.prevStep = this.prevStep.bind(this);
        this.closeTour = this.closeTour.bind(this);
        this.closeCtaModal = this.closeCtaModal.bind(this);
        this.startTour = this.startTour.bind(this);

        window.__deployguard_tour_runner__ = this;
    }

    async startTour(technicalName) {
        const def = TOUR_DEFINITIONS[technicalName];
        if (!def) {
            console.warn(`[DogForce Tour] Unknown tour identifier: ${technicalName}`);
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

    get progressPercent() {
        if (this.totalSteps <= 0) return 0;
        return Math.round(((this.state.stepIndex + 1) / this.totalSteps) * 100);
    }

    async _renderCurrentStep() {
        this.state.hasTarget = false;
        const step = this.currentStep;

        // 1. Navigate to action if step specifies an actionXmlId
        if (step.actionXmlId) {
            try {
                await this.actionService.doAction(step.actionXmlId, { clearBreadcrumbs: true });
            } catch (_e) {
                // Ignore navigation error if already on view
            }
        }

        // 2. Locate target element and compute spotlight cutout coordinates
        setTimeout(() => {
            if (step.targetSelector) {
                const elem = findTargetElement(step.targetSelector);
                if (elem) {
                    elem.scrollIntoView({ behavior: "smooth", block: "center" });
                    
                    // Allow smooth scroll to settle
                    setTimeout(() => {
                        const rect = elem.getBoundingClientRect();
                        this.state.targetRect = {
                            top: Math.max(8, rect.top - 6),
                            left: Math.max(8, rect.left - 6),
                            width: Math.min(window.innerWidth - 16, rect.width + 12),
                            height: Math.min(window.innerHeight - 16, rect.height + 12),
                        };
                        this.state.hasTarget = true;
                    }, 250);
                } else {
                    this.state.hasTarget = false;
                }
            } else {
                this.state.hasTarget = false;
            }
        }, 500);
    }

    async nextStep() {
        if (this.state.stepIndex + 1 < this.totalSteps) {
            this.state.stepIndex += 1;
            await this._renderCurrentStep();
        } else {
            await this._finishTour();
        }
    }

    async prevStep() {
        if (this.state.stepIndex > 0) {
            this.state.stepIndex -= 1;
            await this._renderCurrentStep();
        }
    }

    async _finishTour() {
        this.state.hasTarget = false;
        const tourId = this.state.tourId;
        const isProspect = TOUR_DEFINITIONS[tourId] && TOUR_DEFINITIONS[tourId].isProspect;

        this.state.active = false;

        try {
            await this.orm.call("res.users", "action_complete_tour", [tourId]);
        } catch (_e) {}

        if (isProspect) {
            this.state.showCtaModal = true;
        }
    }

    closeTour() {
        this.state.hasTarget = false;
        this.state.active = false;
    }

    closeCtaModal() {
        this.state.showCtaModal = false;
    }

    get spotlightStyle() {
        const r = this.state.targetRect;
        return `top: ${r.top}px; left: ${r.left}px; width: ${r.width}px; height: ${r.height}px;`;
    }

    get popoverStyle() {
        return "position: fixed; bottom: 28px; right: 28px; z-index: 100000;";
    }
}

registry.category("main_components").add("DogForceTourRunner", {
    Component: TourRunnerOverlay,
});
