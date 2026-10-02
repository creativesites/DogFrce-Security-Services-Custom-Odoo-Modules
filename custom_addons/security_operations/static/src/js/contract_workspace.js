/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class ContractWorkspace extends Component {
    static template = "security_operations.ContractWorkspace";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            contractId: this.props.action?.context?.active_id || null,
            contract: null,
            activeTab: "sites", // "sites", "recipe", "rates", "health", "preview"
            selectedSiteId: null,
            selectedSite: null,
            health: null,
            cyclePreview: null,
            rateCards: [],
            shiftTemplates: [],
            grades: [],
            employees: [],
            // Quick Add Modals/Forms
            showAddSite: false,
            newSiteName: "",
            newSiteLocation: "",
            newSiteSector: "commercial",
            showAddPost: false,
            newPostName: "",
            newPostGuards: 1,
            newPostGradeId: null,
            showAddShift: false,
            newShiftPostId: null,
            newShiftTemplateId: null,
            newShiftGuardCount: 1,
            newShiftGradeId: null,
        });

        onWillStart(() => this._loadData());
    }

    async _loadData() {
        if (!this.state.contractId) {
            this.state.loading = false;
            return;
        }

        try {
            // Load contract record
            const [contract] = await this.orm.read(
                "security.client.contract",
                [this.state.contractId],
                [
                    "name", "partner_id", "date_start", "date_end", "state",
                    "monthly_value", "currency_id", "sites_count", "posts_count",
                    "requirements_count", "estimated_monthly_slots", "readiness_pct",
                    "setup_issues_count", "setup_issues_json", "rate_line_ids", "note"
                ]
            );
            this.state.contract = contract;

            // Parse diagnostics
            if (contract.setup_issues_json) {
                try {
                    this.state.health = JSON.parse(contract.setup_issues_json);
                } catch (e) {
                    this.state.health = null;
                }
            }

            // Load sites under contract
            const sites = await this.orm.searchRead(
                "security.contract.site",
                [["contract_id", "=", this.state.contractId]],
                [
                    "name", "code", "location", "site_type", "supervisor_id",
                    "post_count", "requirement_count", "estimated_monthly_slots",
                    "readiness_state", "issue_count", "site_id"
                ]
            );
            this.state.contract.sites = sites;

            // Load rate cards
            const rateCards = await this.orm.searchRead(
                "security.contract.rate",
                [["contract_id", "=", this.state.contractId]],
                ["shift_category", "grade_id", "hourly_rate"]
            );
            this.state.rateCards = rateCards;

            // Pre-load metadata for quick selectors
            this.state.shiftTemplates = await this.orm.searchRead(
                "security.shift.template",
                [["active", "=", true]],
                ["name", "start_hour", "end_hour", "duration_hours"]
            );
            this.state.grades = await this.orm.searchRead(
                "security.grade",
                [],
                ["name", "code", "hourly_rate"]
            );
            this.state.employees = await this.orm.searchRead(
                "hr.employee",
                [["security_guard", "=", true], ["active", "=", true]],
                ["name"]
            );

            // Calculate 21st-20th cycle dates preview
            const cycle = await this.orm.call(
                "security.client.contract",
                "get_cycle_dates_for",
                [],
                { target_date: contract.date_start }
            );
            this.state.cyclePreview = {
                start: cycle[0],
                end: cycle[1],
            };

            // If a site was previously selected, reload it
            if (this.state.selectedSiteId) {
                await this._loadSelectedSite(this.state.selectedSiteId);
            }
        } catch (err) {
            console.error("Error loading Contract Workspace:", err);
            this.notification.add(`Failed to load contract: ${err.message}`, { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async _loadSelectedSite(siteId) {
        this.state.selectedSiteId = siteId;
        const [site] = await this.orm.read(
            "security.contract.site",
            [siteId],
            ["name", "code", "location", "site_type", "supervisor_id", "post_count", "requirement_count", "estimated_monthly_slots", "readiness_state"]
        );

        // Load posts for this site
        const posts = await this.orm.searchRead(
            "security.contract.post",
            [["contract_site_id", "=", siteId]],
            ["name", "code", "post_type_id", "min_grade_id", "required_guard_count"]
        );

        // Load requirements for each post
        for (const post of posts) {
            post.requirements = await this.orm.searchRead(
                "security.contract.shift.requirement",
                [["contract_post_id", "=", post.id]],
                [
                    "shift_template_id", "guard_count", "min_grade_id",
                    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                    "public_holiday", "is_ad_hoc",
                    "bill_rate", "bill_rate_override", "contract_bill_rate",
                    "pay_rate", "pay_rate_override", "contract_pay_rate",
                    "override_reason", "estimated_monthly_slots", "requirement_id"
                ]
            );
        }
        site.posts = posts;
        this.state.selectedSite = site;
        this.state.activeTab = "recipe";
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    selectSite(siteId) {
        this._loadSelectedSite(siteId);
    }

    backToSites() {
        this.state.selectedSiteId = null;
        this.state.selectedSite = null;
        this.state.activeTab = "sites";
        this._loadData();
    }

    async actionActivate() {
        try {
            await this.orm.call(
                "security.client.contract",
                "action_activate",
                [[this.state.contractId]]
            );
            this.notification.add("Contract activated successfully! Sites, posts, and shift requirements synchronized.", {
                type: "success",
            });
            await this._loadData();
        } catch (err) {
            this.notification.add(err.message || "Failed to activate contract. Please review setup health.", {
                type: "danger",
                sticky: true,
            });
        }
    }

    async actionSaveDraft() {
        this.notification.add("Contract configuration saved.", { type: "info" });
        await this._loadData();
    }

    async actionAddSite() {
        if (!this.state.newSiteName) {
            this.notification.add("Site name is required.", { type: "warning" });
            return;
        }
        try {
            await this.orm.create("security.contract.site", [{
                contract_id: this.state.contractId,
                name: this.state.newSiteName,
                location: this.state.newSiteLocation,
                site_type: this.state.newSiteSector,
            }]);
            this.state.showAddSite = false;
            this.state.newSiteName = "";
            this.state.newSiteLocation = "";
            this.notification.add("New site added to contract.", { type: "success" });
            await this._loadData();
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async actionDuplicateSite(siteId) {
        try {
            await this.orm.call("security.contract.site", "action_duplicate_site", [[siteId]]);
            this.notification.add("Site setup duplicated.", { type: "success" });
            await this._loadData();
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async actionAddPost() {
        if (!this.state.newPostName || !this.state.selectedSiteId) {
            this.notification.add("Post name is required.", { type: "warning" });
            return;
        }
        try {
            await this.orm.create("security.contract.post", [{
                contract_site_id: this.state.selectedSiteId,
                name: this.state.newPostName,
                required_guard_count: this.state.newPostGuards || 1,
                min_grade_id: this.state.newPostGradeId || false,
            }]);
            this.state.showAddPost = false;
            this.state.newPostName = "";
            this.notification.add("Post added.", { type: "success" });
            await this._loadSelectedSite(this.state.selectedSiteId);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async actionAddShift() {
        if (!this.state.newShiftPostId || !this.state.newShiftTemplateId) {
            this.notification.add("Shift template is required.", { type: "warning" });
            return;
        }
        try {
            await this.orm.create("security.contract.shift.requirement", [{
                contract_site_id: this.state.selectedSiteId,
                contract_post_id: this.state.newShiftPostId,
                shift_template_id: parseInt(this.state.newShiftTemplateId),
                guard_count: this.state.newShiftGuardCount || 1,
                min_grade_id: this.state.newShiftGradeId ? parseInt(this.state.newShiftGradeId) : false,
            }]);
            this.state.showAddShift = false;
            this.state.newShiftTemplateId = null;
            this.notification.add("Shift requirement added.", { type: "success" });
            await this._loadSelectedSite(this.state.selectedSiteId);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async actionDuplicateShift(reqId) {
        try {
            await this.orm.call("security.contract.shift.requirement", "action_duplicate_shift", [[reqId]]);
            this.notification.add("Shift duplicated.", { type: "success" });
            await this._loadSelectedSite(this.state.selectedSiteId);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async toggleDay(req, dayField) {
        const newVal = !req[dayField];
        try {
            await this.orm.write("security.contract.shift.requirement", [req.id], { [dayField]: newVal });
            req[dayField] = newVal;
            await this._loadSelectedSite(this.state.selectedSiteId);
            this.notification.add(`Updated ${dayField.replace('_', ' ')}: ${newVal ? 'Active' : 'Off'}`, { type: "info" });
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async changeGuardCount(req, delta) {
        const currentCount = req.guard_count || 1;
        const newCount = Math.max(1, currentCount + delta);
        if (newCount === currentCount) return;
        try {
            await this.orm.write("security.contract.shift.requirement", [req.id], { guard_count: newCount });
            req.guard_count = newCount;
            await this._loadSelectedSite(this.state.selectedSiteId);
            this.notification.add(`Guard count set to ${newCount}`, { type: "info" });
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async actionApplyAllDays(reqId) {
        try {
            await this.orm.call("security.contract.shift.requirement", "action_copy_to_all_days", [[reqId]]);
            this.notification.add("Applied to all Mon–Sun days and Public Holidays.", { type: "success" });
            await this._loadSelectedSite(this.state.selectedSiteId);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async actionSetWeekendAndHolidays(reqId) {
        try {
            await this.orm.call("security.contract.shift.requirement", "action_set_weekend_and_holidays", [[reqId]]);
            this.notification.add("Applied Weekend (Sat, Sun) + Public Holidays 24h schedule.", { type: "success" });
            await this._loadSelectedSite(this.state.selectedSiteId);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    async actionSetWeekdaysOnly(reqId) {
        try {
            await this.orm.call("security.contract.shift.requirement", "action_set_weekdays_only", [[reqId]]);
            this.notification.add("Applied Monday–Friday weekdays schedule.", { type: "success" });
            await this._loadSelectedSite(this.state.selectedSiteId);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    openRequirementForm(reqId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.contract.shift.requirement",
            res_id: reqId,
            views: [[false, "form"]],
            target: "new",
        });
    }

    async toggleRateOverride(req, field) {
        const val = !req[field];
        const vals = {};
        vals[field] = val;
        try {
            await this.orm.write("security.contract.shift.requirement", [req.id], vals);
            await this._loadSelectedSite(this.state.selectedSiteId);
        } catch (err) {
            this.notification.add(err.message, { type: "danger" });
        }
    }

    openOperationalSite(siteId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.site",
            res_id: siteId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openContractForm() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.contract",
            res_id: this.state.contractId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("security_operations.contract_workspace", ContractWorkspace);
