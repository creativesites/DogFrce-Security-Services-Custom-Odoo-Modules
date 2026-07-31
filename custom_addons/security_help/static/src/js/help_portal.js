/** @odoo-module **/

import { Component, useState, onWillStart, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class HelpPortal extends Component {
    static template = "security_help.HelpPortal";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.companyCountryCode = "";
        this.state = useState({
            categories: [],
            articles: [],
            activeCatId: null,
            activeArticleId: null,
            activeArticle: null,
            searchQuery: "",
            searchResults: [],
            searching: false,
            // Custom Flow Interactivity State
            activeFlowId: "onboarding",
            activeStepIdx: 0,
            technicalView: false,
        });
        this._searchTimer = null;
        this.flows = HelpPortal.flows;

        onWillStart(async () => {
            this.companyCountryCode = await this.orm.call(
                "security.help.article",
                "get_company_country_code",
                []
            );
            await this._loadCategories();
        });
    }

    _countryDomain() {
        // Show categories/articles with no country restriction OR matching this company's country.
        return ["|", ["country_code", "=", false], ["country_code", "=", this.companyCountryCode]];
    }

    async _loadCategories() {
        const cats = await this.orm.searchRead(
            "security.help.category",
            this._countryDomain(),
            ["id", "name", "icon", "color", "article_count"],
            { order: "sequence asc, name asc" }
        );
        this.state.categories = cats;
    }

    async selectCategory(catId) {
        this.state.activeCatId = catId;
        this.state.activeArticleId = null;
        this.state.activeArticle = null;
        this.state.searchQuery = "";
        this.state.searching = false;
        this.state.searchResults = [];

        const domain = [["category_id", "=", catId], ...this._countryDomain()];
        const arts = await this.orm.searchRead(
            "security.help.article",
            domain,
            ["id", "title", "summary"],
            { order: "sequence asc, title asc" }
        );
        this.state.articles = arts;
    }

    async openArticle(articleId) {
        this.state.activeArticleId = articleId;
        this.state.activeArticle = null;

        const [art] = await this.orm.read("security.help.article", [articleId], [
            "id", "title", "summary", "body", "category_id",
        ]);
        this.state.activeArticle = { ...art, body: markup(art.body || "") };
    }

    goBack() {
        this.state.activeArticleId = null;
        this.state.activeArticle = null;
    }

    onSearchInput(ev) {
        const q = ev.target.value;
        this.state.searchQuery = q;
        clearTimeout(this._searchTimer);
        if (!q.trim()) {
            this.state.searching = false;
            this.state.searchResults = [];
            return;
        }
        this._searchTimer = setTimeout(() => this._runSearch(q), 300);
    }

    onSearchKeydown(ev) {
        if (ev.key === "Escape") {
            this.state.searchQuery = "";
            this.state.searching = false;
            this.state.searchResults = [];
        }
    }

    async _runSearch(q) {
        if (!q.trim()) return;
        this.state.searching = true;
        this.state.activeCatId = null;
        this.state.activeArticleId = null;
        this.state.activeArticle = null;
        const results = await this.orm.call(
            "security.help.article",
            "search_articles",
            [q, this.companyCountryCode]
        );
        this.state.searchResults = results;
    }

    // Interactive Flow Methods
    selectFlowTab(flowId) {
        this.state.activeFlowId = flowId;
        this.state.activeStepIdx = 0;
    }

    selectFlowStep(idx) {
        this.state.activeStepIdx = idx;
    }

    toggleTechnicalView(view) {
        this.state.technicalView = view;
    }

    resetToWelcome() {
        this.state.activeCatId = null;
        this.state.activeArticleId = null;
        this.state.activeArticle = null;
        this.state.searchQuery = "";
        this.state.searching = false;
        this.state.searchResults = [];
    }
}

// Complete operational flow diagrams with a Beginner vs Technical separation.
HelpPortal.flows = [
    {
        id: "onboarding",
        title: "Onboarding & Setup",
        icon: "fa-building-o",
        color: "#2563eb",
        description: "Initial setup lifecycle: onboarding a client, defining physical guard posts, setting grading rules, and creating schedule baselines.",
        steps: [
            {
                title: "Create Client Site",
                role: "Operations Manager / Director",
                ui_action: "Go to Operations > Client Sites and click 'New'.",
                beginner: "The foundation of DogForce is the Client Site. Enter the physical site name, coordinates, risk level, and general contact details. Geolocation coordinates (latitude/longitude) are critical because they enable the geofenced mobile check-ins and WhatsApp validation.",
                model: "security.client.site",
                states: "contract_status ('active', 'draft', 'expired'), risk_level ('low', 'medium', 'high', 'critical')",
                logic: "Calculates live security coverage based on today's scheduled roster slots. Non-stored search methods (_search_contract_status, _search_risk_level) resolve ORM search desync constraints when grouping and filtering client sites."
            },
            {
                title: "Define Site Posts",
                role: "Operations Manager",
                ui_action: "Open a Client Site, navigate to the 'Posts' tab, and click 'Add a line'.",
                beginner: "A client site may have multiple actual posts where guards are stationed (e.g. 'Main Gate', 'Control Room', 'Front Patrol'). Each post acts as a grouping category for shift scheduling and has its own target coordinates.",
                model: "security.post",
                states: "linked via site_id to security.client.site",
                logic: "Saves latitude/longitude coordinates specific to that post, overriding site-level defaults if specified, to ensure high-accuracy geofence checking."
            },
            {
                title: "Set Post Requirements",
                role: "Compliance Officer",
                ui_action: "Open a Post, navigate to 'Requirements', and specify the Grade and Certifications.",
                beginner: "To maintain compliance, specify the required headcount, minimum guard Grade (e.g., Grade A, B, C, D), and mandatory certifications (e.g., Armed License, Fire Safety, First Aid) that a scheduled guard must possess.",
                model: "security.site.requirement",
                states: "linked via post_id to security.post",
                logic: "Roster scheduling validators evaluate this record dynamically. If an assigned guard's grade is lower than the post requirement, the slot throws a 'Grade Mismatch' warning and triggers a compliance penalty score."
            },
            {
                title: "Create Shift Templates",
                role: "Roster Planner",
                ui_action: "Go to Operations > Shift Templates and define default start/end times.",
                beginner: "Create reusable shift patterns for the site posts (e.g., 'Day Shift 06:00-18:00', 'Night Shift 18:00-06:00'). These templates define the default active hours and lunch break windows, which are automatically expanded when generating a new roster batch.",
                model: "security.shift.template",
                states: "linked to security.client.site or security.post",
                logic: "Stores start_time and end_time as float hours (e.g. 6.0 and 18.0) and validates total shift hours. Used as the blueprint by the roster batch slot expander."
            }
        ]
    },
    {
        id: "scheduling",
        title: "Scheduling & Allocations",
        icon: "fa-calendar",
        color: "#1a3a5c",
        description: "Generating schedule rosters, running the AI auto-allocator, checking guard fatigue, and publishing weekly schedules.",
        steps: [
            {
                title: "Create Roster Batch",
                role: "Roster Planner",
                ui_action: "Go to Scheduling > Roster Batches and click 'New'.",
                beginner: "Create a new Roster Batch for a target week or month. This batch groups all roster slots for physical sites during that cycle, keeping schedules organised and allowing draft reviews before clients are notified.",
                model: "security.roster.batch",
                states: "state ('draft', 'published', 'closed')",
                logic: "Acts as a security and database transaction boundary. Prevents editing of historical slots once a batch is transitioned to 'closed' at the end of the month."
            },
            {
                title: "Generate Blank Slots",
                role: "Roster Planner",
                ui_action: "Inside a Roster Batch form, click the 'Generate Slots' button.",
                beginner: "Click the generator button to automatically expand all active site posts and shift templates into blank, unassigned schedule slots for every day of the selected period. This saves hours of manual entry.",
                model: "security.roster.slot",
                states: "Linked via batch_id. State is 'draft'.",
                logic: "Runs Python method action_generate_slots(). Queries all active security.post and security.shift.template records, then creates a security.roster.slot record for each day, post, and shift configuration."
            },
            {
                title: "Run AI Auto-Roster",
                role: "Operations Manager",
                ui_action: "Click the 'AI Auto-Schedule' button on the Roster Batch.",
                beginner: "Let the AI take over! The auto-roster algorithm automatically matches and assigns qualified guards to all unassigned slots. It balances rest days, leave records, distance from site, and overtime to select the best guard.",
                model: "security.roster.batch / security.roster.slot",
                states: "Assigns guard_id to security.roster.slot records.",
                logic: "Executes action_auto_schedule() on the batch, evaluating a greedy ranking matrix:\n- Score = Grade Match + Proximity + Reliability - Fatigue Penalty - Overtime Cost.\n- Ensures no guard exceeds maximum legal hours (48/60 hrs per week) and flags rest day violations."
            },
            {
                title: "Publish Schedule",
                role: "Operations Manager / Supervisor",
                ui_action: "Click the 'Publish Batch' button on the Roster Batch.",
                beginner: "Once you have reviewed the schedule and resolved any manual warning flags, click Publish. This changes the status to official, notifies the guards, and locks the roster structure in place.",
                model: "security.roster.batch",
                states: "state transitions from 'draft' to 'published'",
                logic: "Triggers DB signals that push schedule updates to the WhatsApp AI Bridge, dispatching automated schedule briefings to guards via the WhatsApp API."
            }
        ]
    },
    {
        id: "attendance",
        title: "Attendance & Alerts",
        icon: "fa-check-square-o",
        color: "#0891b2",
        description: "Tracking real-time check-ins, monitoring geofenced check-ins, issuing AWOL alarms, and logging disciplinary incidents.",
        steps: [
            {
                title: "Guard Check-In",
                role: "Guard / Supervisor / Dispatcher",
                ui_action: "Logged via the Mobile App, geofenced WhatsApp prompt, or the Posting Console.",
                beginner: "Guards check-in when arriving at their post. If checking in via mobile or WhatsApp, the system automatically verifies their GPS coordinates to make sure they are physically present at the site before registering attendance.",
                model: "security.attendance",
                states: "state ('checked_in', 'checked_out')",
                logic: "Compares latitude/longitude with security.post coordinates using the Haversine formula:\n- distance = 2 * r * arcsin(sqrt(sin²(Δlat/2) + cos(lat1)*cos(lat2)*sin²(Δlon/2))).\n- Rejects check-in if distance > 100 metres from post, unless supervisor bypasses."
            },
            {
                title: "AWOL Alert Trigger",
                role: "System (Automated)",
                ui_action: "No manual action required. Check the Live Operations Dashboard for alert banners.",
                beginner: "If a guard fails to check in within 30 minutes of their scheduled shift start time, the system sounds an alarm. It automatically changes the slot state to AWOL and alerts the dispatch team to find a replacement.",
                model: "security.roster.slot",
                states: "state changes from 'draft'/'published' to 'awol'",
                logic: "The automated cron job _cron_check_awol_slots() runs every 10 minutes, flags overdue slots, registers an alert on the security.event.bus, and reduces the absent guard's live reliability rating."
            },
            {
                title: "Dispatch Replacement",
                role: "Dispatcher / Supervisor",
                ui_action: "Open Roster Board, find the AWOL slot, click 'Assign Guard' and choose from the available standby pool.",
                beginner: "When an AWOL occurs, dispatchers use the Roster Board to instantly see nearby standby guards who are off-duty and qualified. Assigning a standby guard closes the alert and logs the replacement.",
                model: "security.roster.slot / security.attendance",
                states: "state is updated to 'covered_replacement'. Replaced guard flagged.",
                logic: "Updates slot's guard_id to the standby guard, logs a historical 'awol_replaced' event, and spawns a new security.attendance expectation for the replacement guard's check-in."
            },
            {
                title: "Raise Incident",
                role: "Supervisor / Operations Manager",
                ui_action: "Go to Operations > Disciplinary Incidents and click 'New'.",
                beginner: "If a guard was AWOL or violated dress code, conduct, or safety rules, supervisors log an Incident. The system issues automated warnings and deducts points from the guard's overall reliability rating.",
                model: "security.incident",
                states: "state ('open', 'under_investigation', 'resolved', 'dismissed')",
                logic: "A post-write trigger on security.incident subtracts points from hr.employee's reliability_score (e.g., AWOL = -10 pts, Dress Code = -2 pts). If score falls below 50, compliance rules prevent the guard from being auto-scheduled."
            }
        ]
    },
    {
        id: "payroll",
        title: "Billing & Payroll",
        icon: "fa-money",
        color: "#7c3aed",
        description: "Processing actual monthly hours worked, applying contract rate cards for billing, and calculating base wages, overtime, Sunday/holiday rates, and legal tax deductions.",
        steps: [
            {
                title: "Lock Roster Batch",
                role: "Payroll Officer / Billing Manager",
                ui_action: "Go to Scheduling > Roster Batches, select the batch, and click 'Close Batch'.",
                beginner: "At the end of the monthly billing cycle, close and lock the roster batch. This freezes all hours worked, manual replacements, and attendance logs so that billing and payroll are calculated from clean, audited data.",
                model: "security.roster.batch",
                states: "state transitions from 'published' to 'closed'",
                logic: "Disables write operations on all associated security.roster.slot records. Aggregates actual attendance hours and manual overrides into raw, immutable payroll/billing inputs."
            },
            {
                title: "Generate Client Invoices",
                role: "Billing Officer",
                ui_action: "Go to Billing > Invoices and click 'Generate Monthly Invoices'.",
                beginner: "The system reads actual roster hours worked and automatically applies the client site's service contract rate card. It generates highly itemized draft invoices separating normal hour billing, weekend premiums, and public holiday rates.",
                model: "account.move / account.move.line",
                states: "state ('draft', 'posted', 'cancel')",
                logic: "Iterates through closed roster slots. Cross-references actual hours against security.client.contract lines, applying contract billing rates (e.g., normal rate N$45/hr, Sunday/holiday rate N$90/hr) to build Invoice Lines."
            },
            {
                title: "Run Payroll Calculations",
                role: "Payroll Officer",
                ui_action: "Go to Payroll > Pay Runs, click 'Calculate Sheet'.",
                beginner: "Create a pay run for the employee batch and click calculate. The payroll engine automatically calculates base wage, overtime hours (1.5x), Sunday/holiday premium hours (2x), and subtracts legal tax deductions, social security (SSC), and uniform/loan advances.",
                model: "security.payroll.payslip",
                states: "state ('draft', 'calculated', 'approved', 'paid')",
                logic: "Evaluates standard Namibian & Zambian Labor Code algorithms:\n- Normal hours = up to 45 hrs/week.\n- Overtime hours calculated at 1.5x normal rate.\n- Sunday/Holiday hours calculated at 2.0x normal rate.\n- Deducts SSC (0.9% employee/employer matching) and calculates progressive PAYE brackets."
            },
            {
                title: "Disburse & Close",
                role: "Finance Director",
                ui_action: "Click 'Export EFT' on the Pay Run, then click 'Approve & Close'.",
                beginner: "After reviewing payslips, export the bank-compatible EFT electronic flat file to process bulk payments. Approving the pay run locks the payslips, posts financial ledger entries, and updates the general ledger.",
                model: "security.payroll.payrun",
                states: "state transitions to 'close'",
                logic: "Generates standard bank electronic payment formats (EFT txt/csv), locks payroll ledger entries, posts matching journal entries into general accounting, and archives the monthly employee payroll ledger."
            }
        ]
    }
];

registry.category("actions").add("security_help.HelpPortal", HelpPortal);
