/** @odoo-module **/

/**
 * The curated global nav tree — data only. Labels and grouping are the
 * design deliverable (HANDOFF-deployguard-shell.md §5.5) and deliberately
 * don't match Odoo's raw menu order.
 *
 * Leaf shape: { key, label, action?, soon?, owner?, countKey? }
 * - action:   "<module>.<xmlid>" of an existing action. Omitted for `soon`
 *             leaves and for leaves whose feature has no dedicated action
 *             yet (they render the same as `soon` — see shell_nav_panel.js).
 * - soon:     true for the six planned modules (Armed Response, Armoury,
 *             Fleet & Tracking, Client Portal, Recruitment, Documents-soon
 *             entries) — renders a SOON chip, never clickable.
 * - owner:    true restricts the leaf to security_base.group_security_owner.
 * - countKey: key into the shell service's nav_counts payload for the live
 *             count pill.
 */
export const NAV_CATALOG = [
    {
        key: "operations",
        label: "Operations",
        children: [
            {
                key: "live_control",
                label: "Live control",
                children: [
                    { key: "command_centre", label: "Command Centre", action: "security_operations.action_ops_dashboard" },
                    { key: "site_hub", label: "Interactive Site Hub", action: "security_operations.action_security_site_hub" },
                    { key: "incidents", label: "Incidents", action: "security_discipline.action_security_incident", countKey: "incidents" },
                    { key: "whatsapp_control_room", label: "WhatsApp Control Room", action: "security_ai_whatsapp_bridge.action_whatsapp_chat_workspace_client" },
                    { key: "whatsapp_dashboard", label: "WhatsApp Dashboard", action: "security_ai_whatsapp_bridge.action_whatsapp_dashboard_client" },
                ],
            },
            {
                key: "sites_posts",
                label: "Sites & posts",
                children: [
                    { key: "site_register", label: "Site register", action: "security_operations.action_security_client_site" },
                    { key: "posts", label: "Posts", action: "security_operations.action_security_post" },
                    { key: "shift_templates", label: "Shift templates", action: "security_operations.action_security_shift_template" },
                ],
            },
            {
                key: "planning",
                label: "Planning",
                children: [
                    { key: "demand_planning", label: "Demand planning", action: "security_operations.action_security_demand_plan", owner: true },
                    { key: "telephony", label: "Telephony", soon: true },
                ],
            },
            {
                key: "armed_response",
                label: "Armed response",
                children: [
                    { key: "unit_dispatch_board", label: "Unit dispatch board", soon: true },
                    { key: "live_callout_map", label: "Live callout map", soon: true },
                    { key: "armoury_ledger", label: "Armoury ledger", soon: true },
                ],
            },
        ],
    },
    {
        key: "rostering",
        label: "Rostering",
        children: [
            {
                key: "rostering_planning",
                label: "Planning",
                children: [
                    { key: "rostering_hub", label: "Rostering Hub", action: "security_shift_planner.action_rostering_hub" },
                    { key: "roster_board", label: "Roster Board", action: "security_shift_planner.action_roster_board" },
                    { key: "ai_shift_suggestions", label: "AI shift suggestions", action: "security_ai_engine.action_security_smart_recommendation", countKey: "ai_suggestions" },
                ],
            },
            {
                key: "review_publish",
                label: "Review & publish",
                children: [
                    { key: "weekly_roster_review", label: "Weekly roster review", action: "security_shift_planner.action_security_roster_week" },
                    { key: "roster_gaps", label: "Roster gaps", action: "security_operations.action_security_roster_slot", countKey: "unassigned_slots" },
                    { key: "roster_export", label: "Roster export", action: "security_client_reports.action_security_roster_export_wizard" },
                ],
            },
        ],
    },
    {
        key: "attendance",
        label: "Attendance",
        children: [
            {
                key: "attendance_live",
                label: "Live",
                children: [
                    { key: "attendance_grid", label: "Attendance grid", action: "security_attendance.action_attendance_summary_grid" },
                    { key: "checkin_checkout", label: "Check-in / check-out", action: "security_attendance.action_attendance_posting_console" },
                ],
            },
            {
                key: "attendance_exceptions",
                label: "Exceptions",
                children: [
                    { key: "awol_register", label: "AWOL register", action: "security_attendance.action_security_attendance_record", countKey: "awol" },
                    { key: "late_arrivals", label: "Late arrivals", action: "security_attendance.action_security_attendance_record", countKey: "late_arrivals" },
                    { key: "overtime_approvals", label: "Overtime approvals", action: "security_attendance.action_security_attendance_record", countKey: "overtime_approvals" },
                ],
            },
            {
                key: "discipline",
                label: "Discipline",
                children: [
                    { key: "disciplinary_cases", label: "Disciplinary cases", action: "security_discipline.action_security_incident" },
                    { key: "payroll_deductions", label: "Payroll deductions", action: "security_loans.action_security_loan_deduction", owner: true },
                ],
            },
        ],
    },
    {
        key: "people",
        label: "People",
        children: [
            {
                key: "workforce",
                label: "Workforce",
                children: [
                    { key: "employee_records", label: "Employee records", action: "hr.open_view_employee_list_my" },
                    { key: "guard_directory", label: "Guard directory", action: "security_base.action_workforce_dashboard" },
                    { key: "grades_attributes", label: "Grades & attributes", action: "security_base.action_security_grade" },
                ],
            },
            {
                key: "recruitment",
                label: "Recruitment",
                children: [
                    { key: "applicant_pipeline", label: "Applicant pipeline", soon: true },
                    { key: "vacancies", label: "Vacancies", soon: true },
                ],
            },
            {
                key: "compliance",
                label: "Compliance",
                children: [
                    { key: "documents_certifications", label: "Documents & certifications", action: "security_documents.action_security_employee_document", countKey: "expiring_docs" },
                    { key: "document_register", label: "Document register", soon: true },
                    { key: "leave", label: "Leave", action: "security_leave.action_security_leave_request", countKey: "pending_leave" },
                ],
            },
            {
                key: "assets",
                label: "Assets",
                children: [
                    { key: "equipment_issue_return", label: "Equipment issue / return", action: "security_equipment.action_security_equipment_return_wizard" },
                    { key: "armoury", label: "Armoury", soon: true },
                ],
            },
        ],
    },
    {
        key: "payroll_finance",
        label: "Payroll & finance",
        owner: true,
        children: [
            {
                key: "payroll",
                label: "Payroll",
                children: [
                    { key: "payroll_command_centre", label: "Payroll command centre", action: "security_payroll_core.action_security_payroll_command_center" },
                    { key: "payslip_designer", label: "Payslip designer", action: "security_payroll_core.action_payslip_designer" },
                    { key: "loans", label: "Loans", action: "security_loans.action_security_employee_loan" },
                ],
            },
            {
                key: "billing",
                label: "Billing",
                children: [
                    { key: "billing_invoicing", label: "Billing & invoicing", action: "security_billing.action_security_billing_invoice", countKey: "draft_invoices" },
                    { key: "zra_smart_invoice", label: "ZRA Smart Invoice", action: "security_zra_invoice.action_security_zra_submission" },
                    { key: "reconciliation", label: "Reconciliation", action: "security_reconciliation_core.action_security_reconciliation_jobs" },
                    { key: "accounting_controls", label: "Accounting controls", action: "security_accounting_controls.action_security_client_payment" },
                ],
            },
        ],
    },
    {
        key: "fleet",
        label: "Fleet",
        children: [
            {
                key: "vehicles",
                label: "Vehicles",
                children: [
                    { key: "vehicle_register", label: "Vehicle register", action: "security_fleet.action_security_vehicle" },
                    { key: "fuel_inspections", label: "Fuel & inspections", action: "security_fleet.action_security_vehicle_fuel_log" },
                ],
            },
            {
                key: "transport",
                label: "Transport",
                children: [
                    { key: "shuttle_routes", label: "Shuttle routes", action: "security_fleet.action_security_shuttle_route" },
                    { key: "fleet_tracking_map", label: "Fleet & tracking map", soon: true },
                ],
            },
        ],
    },
    {
        key: "clients",
        label: "Clients",
        children: [
            {
                key: "onboarding",
                label: "Onboarding",
                children: [
                    { key: "client_onboarding_wizard", label: "Client onboarding wizard", action: "security_client_onboarding.action_security_client_onboarding_wizard" },
                    { key: "contracts_rate_cards", label: "Contracts & rate cards", action: "security_operations.action_security_client_contract" },
                ],
            },
            {
                key: "client_reporting",
                label: "Client reporting",
                children: [
                    { key: "client_service_reports", label: "Client service reports", action: "security_client_reports.action_security_client_service_report" },
                    { key: "client_portal", label: "Client portal", soon: true },
                    { key: "crm_bridge", label: "CRM bridge", owner: true },
                ],
            },
        ],
    },
    {
        key: "reporting_platform",
        label: "Reporting & platform",
        children: [
            {
                key: "reporting",
                label: "Reporting",
                children: [
                    { key: "executive_analytics", label: "Executive analytics", action: "security_reporting.action_security_executive_dashboard", owner: true },
                    { key: "compliance_intelligence", label: "Compliance intelligence", action: "security_documents.action_security_compliance_dashboard" },
                    { key: "roster_client_reports", label: "Roster & client reports", action: "security_reporting.action_security_roster_reporting" },
                ],
            },
            {
                key: "platform",
                label: "Platform",
                children: [
                    { key: "notifications", label: "Notifications", action: "security_notifications.action_security_notifications" },
                    { key: "ai_assistant", label: "AI assistant", action: "security_ai_engine.action_security_ai_chat_session" },
                    { key: "whatsapp_settings", label: "WhatsApp settings", action: "security_ai_whatsapp_bridge.action_security_whatsapp_config_server" },
                    { key: "help_centre", label: "Help Centre", action: "security_help.action_help_portal" },
                    { key: "product_tour", label: "Product tour", action: "security_tour.action_security_tour_definition" },
                    { key: "licensing", label: "Licensing", action: "security_licensing.action_security_license", owner: true },
                    { key: "backup_offsite_sync", label: "Backup & offsite sync", action: "security_backup_vault.action_security_backup_record", owner: true },
                    { key: "users_roles", label: "Users & roles", action: "base.action_res_users", owner: true },
                    { key: "white_label_theming", label: "White-label theming", action: "security_theme.action_theme_settings", owner: true },
                ],
            },
        ],
    },
];

/** Flat list of every non-soon leaf's action xmlid, for the single batched
 * ir.model.data resolution lookup on boot (shell_service.js). */
export function collectActionXmlIds(catalog = NAV_CATALOG) {
    const xmlids = new Set();
    for (const group of catalog) {
        for (const subgroup of group.children) {
            for (const leaf of subgroup.children) {
                if (leaf.action) {
                    xmlids.add(leaf.action);
                }
            }
        }
    }
    return [...xmlids];
}
