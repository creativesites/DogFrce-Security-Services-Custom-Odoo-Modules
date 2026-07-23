/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * RosterBoard — Tier-3 OWL client action.
 *
 * An interactive weekly/monthly timeline showing all roster slots for a batch.
 * - Rows:  Sites → Posts
 * - Cols:  Dates within the batch's date range
 * - Cells: One card per slot (assigned guard name, or "Unassigned")
 *
 * Clicking an unassigned slot opens GuardPoolSidebar which shows ranked
 * suggestions from the Python scoring engine (SecurityRosterSlot.action_suggest_guards).
 * Clicking "Assign" calls action_assign_to_slot via ORM, which returns either
 * a display_notification dict (on error) or null (on success).
 */
class RosterBoard extends Component {
    static props = { "*": true };
    static template = "security_shift_planner.RosterBoard";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: false,
            autoFilling: false,
            autoAssigning: false,
            isMobile: window.innerWidth < 768,
            showBatchesDrawer: false,
            batchesFilter: "all",
            batchesSearch: "",
            companyCycle: {
                startDay: 21,
                endDay: 20,
                autoGenerate: true,
            },
            batches: [],
            batchId: null,
            batchDateFrom: null,
            batchDateTo: null,
            dates: [],
            sites: [],
            posts: [],
            slots: [],
            filterSiteId: null,
            showGapsOnly: false,
            selectedSlot: null,
            suggestions: [],
            suggestionsLoaded: false,
            loadingSuggestions: false,
            stats: { assigned: 0, unassigned: 0, criticalGaps: 0 },
            assignError: null,   // { guardName, message } shown inline in Guard Pool
            contextMenu: { visible: false, x: 0, y: 0, slot: null },
            // Phase 4: drag-and-drop + swap dialog
            dragOverSlotId: null,
            swapDialog: { visible: false, slot: null, reason: "" },
            // Create-batch dialog
            createDialog: {
                visible: false,
                partnerId: null,
                siteId: null,
                cycleMode: "default", // default, current, next, custom
                month: "",
                year: "",
                dateFrom: "",
                dateTo: "",
                autoGenerateSlots: true,
                copySourceId: null,
                creating: false,
                validating: false,
                error: "",
                validation: {
                    valid: true,
                    errors: [],
                    warnings: [],
                    estimated_slots: 0,
                    duration_days: 30,
                    sites_count: 0,
                    posts_count: 0,
                },
            },
            createSlot: {
                open: false,
                allSites: [],
                allPosts: [],
                shiftTemplates: [],
                employees: [],
                form: {
                    client_id: null,
                    site_id: null,
                    post_id: null,
                    shift_template_id: null,
                    employee_id: null,
                    shift_date: null,
                    count: 1,
                },
                saving: false,
                dataLoaded: false,
            },
        });

        const handleResize = () => {
            this.state.isMobile = window.innerWidth < 768;
        };
        window.addEventListener("resize", handleResize);

        onWillStart(async () => {
            await Promise.all([this.loadCompanyCycle(), this.loadBatches(), this.loadAllSites()]);
        });
    }

    // ─── Data loaders ──────────────────────────────────────────────

    async loadCompanyCycle() {
        try {
            const defaults = await this.orm.call(
                "res.config.settings",
                "get_company_roster_cycle_defaults",
                []
            );
            if (defaults) {
                this.state.companyCycle.startDay = defaults.start_day;
                this.state.companyCycle.endDay = defaults.end_day;
                this.state.companyCycle.autoGenerate = defaults.auto_generate;
            }
        } catch {
            // fallback defaults (21st to 20th)
        }
    }

    async loadBatches() {
        const batches = await this.orm.searchRead(
            "security.roster.batch",
            [],
            ["id", "name", "date_from", "date_to", "partner_id", "site_id", "state", "unassigned_count", "critical_gap_count", "fill_rate"],
            { order: "date_from desc", limit: 100 }
        );
        this.state.batches = batches;
    }

    async loadAllSites() {
        const sites = await this.orm.searchRead(
            "security.client.site",
            [["active", "=", true]],
            ["id", "name", "partner_id"],
            { order: "name" }
        );
        this.state.allSites = sites;
    }

    async loadBoard() {
        if (!this.state.batchId) return;
        this.state.loading = true;
        this.state.selectedSlot = null;
        this.state.suggestions = [];
        this.state.suggestionsLoaded = false;
        this.state.assignError = null;

        const batch = this.state.batches.find((b) => b.id === this.state.batchId);
        if (!batch) { this.state.loading = false; return; }

        this.state.batchDateFrom = batch.date_from;
        this.state.batchDateTo = batch.date_to;
        this.state.dates = this._buildDateRange(batch.date_from, batch.date_to);

        // Load all slots for this batch (include cancelled so we can grey them out)
        const slots = await this.orm.searchRead(
            "security.roster.slot",
            [["batch_id", "=", this.state.batchId]],
            [
                "id", "shift_date", "site_id", "post_id", "post_type_id",
                "shift_template_id", "employee_id", "state", "suggestion_count",
                "fairness_warning", "critical_gap",
            ]
        );

        // Fetch shift template hours for display
        const templateIds = [...new Set(
            slots.map((s) => s.shift_template_id && s.shift_template_id[0]).filter(Boolean)
        )];
        let templateMap = {};
        if (templateIds.length) {
            const templates = await this.orm.searchRead(
                "security.shift.template",
                [["id", "in", templateIds]],
                ["id", "start_hour", "end_hour"]
            );
            templates.forEach((t) => { templateMap[t.id] = t; });
        }

        // Enrich slots
        this.state.slots = slots.map((s) => {
            const tmpl = s.shift_template_id ? templateMap[s.shift_template_id[0]] : null;
            return {
                id: s.id,
                shift_date: s.shift_date,
                site_id: s.site_id ? s.site_id[0] : null,
                site_name: s.site_id ? s.site_id[1] : "—",
                post_id: s.post_id ? s.post_id[0] : null,
                post_name: s.post_id ? s.post_id[1] : "—",
                employee_id: s.employee_id ? s.employee_id[0] : null,
                employee_name: s.employee_id ? s.employee_id[1] : null,
                state: s.state,
                suggestion_count: s.suggestion_count,
                conflict: !!s.fairness_warning,
                critical_gap: !!s.critical_gap,
                shift_label: tmpl ? this._formatShift(tmpl) : "",
            };
        });

        // Build site/post index
        const siteMap = {};
        const postMap = {};
        this.state.slots.forEach((s) => {
            if (s.site_id && !siteMap[s.site_id]) {
                siteMap[s.site_id] = { id: s.site_id, name: s.site_name };
            }
            if (s.post_id && !postMap[s.post_id]) {
                postMap[s.post_id] = { id: s.post_id, name: s.post_name, site_id: s.site_id };
            }
        });
        this.state.sites = Object.values(siteMap).sort((a, b) => a.name.localeCompare(b.name));
        this.state.posts = Object.values(postMap);

        // Stats (exclude cancelled from counts)
        const activeSlots = this.state.slots.filter((s) => s.state !== "cancelled");
        this.state.stats.assigned = activeSlots.filter((s) => s.employee_id).length;
        this.state.stats.unassigned = activeSlots.filter((s) => !s.employee_id).length;
        this.state.stats.criticalGaps = activeSlots.filter((s) => !s.employee_id && s.critical_gap).length;

        this.state.loading = false;
    }

    // Reload only the slot data for the current batch (used after assign/unassign/auto-fill)
    async loadSlots(batchId) {
        const slots = await this.orm.searchRead(
            "security.roster.slot",
            [["batch_id", "=", batchId]],
            [
                "id", "shift_date", "site_id", "post_id", "post_type_id",
                "shift_template_id", "employee_id", "state", "suggestion_count",
                "fairness_warning", "critical_gap",
            ]
        );

        const templateIds = [...new Set(
            slots.map((s) => s.shift_template_id && s.shift_template_id[0]).filter(Boolean)
        )];
        let templateMap = {};
        if (templateIds.length) {
            const templates = await this.orm.searchRead(
                "security.shift.template",
                [["id", "in", templateIds]],
                ["id", "start_hour", "end_hour"]
            );
            templates.forEach((t) => { templateMap[t.id] = t; });
        }

        this.state.slots = slots.map((s) => {
            const tmpl = s.shift_template_id ? templateMap[s.shift_template_id[0]] : null;
            return {
                id: s.id,
                shift_date: s.shift_date,
                site_id: s.site_id ? s.site_id[0] : null,
                site_name: s.site_id ? s.site_id[1] : "—",
                post_id: s.post_id ? s.post_id[0] : null,
                post_name: s.post_id ? s.post_id[1] : "—",
                employee_id: s.employee_id ? s.employee_id[0] : null,
                employee_name: s.employee_id ? s.employee_id[1] : null,
                state: s.state,
                suggestion_count: s.suggestion_count,
                conflict: !!s.fairness_warning,
                critical_gap: !!s.critical_gap,
                shift_label: tmpl ? this._formatShift(tmpl) : "",
            };
        });

        const activeSlots = this.state.slots.filter((s) => s.state !== "cancelled");
        this.state.stats.assigned = activeSlots.filter((s) => s.employee_id).length;
        this.state.stats.unassigned = activeSlots.filter((s) => !s.employee_id).length;
        this.state.stats.criticalGaps = activeSlots.filter((s) => !s.employee_id && s.critical_gap).length;
    }

    // ─── Computed getters ───────────────────────────────────────────

    get visibleSites() {
        let sites = this.state.sites;
        if (this.state.filterSiteId) {
            sites = sites.filter((s) => s.id === this.state.filterSiteId);
        }
        if (this.state.showGapsOnly) {
            sites = sites.filter((s) => this._siteHasGap(s.id));
        }
        return sites;
    }

    get batchesList() {
        let list = this.state.batches;
        if (this.state.batchesFilter && this.state.batchesFilter !== "all") {
            list = list.filter((b) => b.state === this.state.batchesFilter);
        }
        if (this.state.batchesSearch && this.state.batchesSearch.trim()) {
            const q = this.state.batchesSearch.trim().toLowerCase();
            list = list.filter((b) => {
                const name = (b.name || "").toLowerCase();
                const site = Array.isArray(b.site_id) ? b.site_id[1].toLowerCase() : "";
                const partner = Array.isArray(b.partner_id) ? b.partner_id[1].toLowerCase() : "";
                return name.includes(q) || site.includes(q) || partner.includes(q);
            });
        }
        return list;
    }

    get assignmentPercent() {
        const total = this.state.stats.assigned + this.state.stats.unassigned;
        if (!total) return 0;
        return Math.round((this.state.stats.assigned / total) * 100);
    }

    get selectedBatchName() {
        if (!this.state.batchId) return "";
        const b = this.state.batches.find((b) => b.id === this.state.batchId);
        return b ? b.name : "";
    }

    get clientsForCreate() {
        const seen = new Set();
        const result = [];
        for (const s of this.state.createSlot.allSites) {
            if (!s.partner_id) continue;
            const pid = Array.isArray(s.partner_id) ? s.partner_id[0] : s.partner_id;
            if (seen.has(pid)) continue;
            seen.add(pid);
            result.push({
                id: pid,
                name: Array.isArray(s.partner_id) ? s.partner_id[1] : String(s.partner_id),
            });
        }
        return result.sort((a, b) => a.name.localeCompare(b.name));
    }

    get sitesForCreate() {
        const clientId = this.state.createSlot.form.client_id;
        if (!clientId) return this.state.createSlot.allSites;
        return this.state.createSlot.allSites.filter((s) => {
            if (!s.partner_id) return false;
            const pid = Array.isArray(s.partner_id) ? s.partner_id[0] : s.partner_id;
            return pid === parseInt(clientId);
        });
    }

    get postsForCreate() {
        const siteId = this.state.createSlot.form.site_id;
        if (!siteId) return this.state.createSlot.allPosts;
        return this.state.createSlot.allPosts.filter((p) => {
            if (!p.site_id) return false;
            const sid = Array.isArray(p.site_id) ? p.site_id[0] : p.site_id;
            return sid === parseInt(siteId);
        });
    }

    get selectedBatch() {
        if (!this.state.batchId) return null;
        return this.state.batches.find((b) => b.id === this.state.batchId) || null;
    }

    get unassignedCount() {
        return this.state.slots.filter(
            (s) => !s.employee_id && s.state !== "cancelled"
        ).length;
    }

    batchStateColor(state) {
        const colors = {
            draft:      "#94a3b8",
            generated:  "#3b82f6",
            submitted:  "#f59e0b",
            approved:   "#8b5cf6",
            confirmed:  "#16a34a",
            cancelled:  "#ef4444",
        };
        return colors[state] || "#64748b";
    }

    getPostsForSite(siteId) {
        const posts = this.state.posts.filter((p) => p.site_id === siteId);
        if (this.state.showGapsOnly) {
            return posts.filter((p) => this._postHasGap(siteId, p.id));
        }
        return posts;
    }

    _siteHasGap(siteId) {
        return this.state.slots.some(
            (s) => s.site_id === siteId && !s.employee_id && s.state !== "cancelled"
        );
    }

    _postHasGap(siteId, postId) {
        return this.state.slots.some(
            (s) => s.site_id === siteId && s.post_id === postId && !s.employee_id && s.state !== "cancelled"
        );
    }

    toggleGapsOnly() {
        this.state.showGapsOnly = !this.state.showGapsOnly;
    }

    getSlotsForCell(siteId, postId, dateStr) {
        return this.state.slots.filter(
            (s) => s.site_id === siteId && s.post_id === postId && s.shift_date === dateStr
        );
    }

    scoreColor(score) {
        if (score >= 80) return "#16a34a";
        if (score >= 50) return "#ca8a04";
        return "#dc2626";
    }

    scoreBarColor(score) {
        if (score >= 80) return "#16a34a";
        if (score >= 50) return "#f59e0b";
        return "#ef4444";
    }

    get createDialogPartners() {
        const seen = new Set();
        const partners = [];
        for (const s of this.state.allSites) {
            if (s.partner_id && !seen.has(s.partner_id[0])) {
                seen.add(s.partner_id[0]);
                partners.push({ id: s.partner_id[0], name: s.partner_id[1] });
            }
        }
        return partners.sort((a, b) => a.name.localeCompare(b.name));
    }

    get createDialogSites() {
        const pid = this.state.createDialog.partnerId;
        if (!pid) return [];
        return this.state.allSites.filter((s) => s.partner_id && s.partner_id[0] === pid);
    }

    get dialogMonthOptions() {
        return [
            { value: "01", label: "January" }, { value: "02", label: "February" },
            { value: "03", label: "March" }, { value: "04", label: "April" },
            { value: "05", label: "May" }, { value: "06", label: "June" },
            { value: "07", label: "July" }, { value: "08", label: "August" },
            { value: "09", label: "September" }, { value: "10", label: "October" },
            { value: "11", label: "November" }, { value: "12", label: "December" },
        ];
    }

    get dialogYearOptions() {
        const y = new Date().getFullYear();
        return [String(y - 1), String(y), String(y + 1), String(y + 2)];
    }

    // ─── Batches Manager Drawer / Modal / Bottom Sheet ────────────────

    openBatchesManager() {
        this.state.showBatchesDrawer = true;
    }

    closeBatchesManager() {
        this.state.showBatchesDrawer = false;
    }

    setBatchesFilter(filter) {
        this.state.batchesFilter = filter;
    }

    onBatchesSearchInput(ev) {
        this.state.batchesSearch = ev.target.value;
    }

    async selectBatchFromManager(batchId) {
        this.state.batchId = batchId;
        this.state.showBatchesDrawer = false;
        await this.loadBoard();
    }

    async autoFillBatchFromManager(batchId) {
        try {
            this.notification.add("Running auto-fill scoring engine...", { type: "info" });
            const result = await this.orm.call(
                "security.roster.batch",
                "action_auto_fill_slots",
                [[batchId]]
            );
            await this.loadBatches();
            if (this.state.batchId === batchId) {
                await this.loadBoard();
            }
            if (result && result.params) {
                this.notification.add(result.params.message || "Auto-fill complete.", {
                    title: result.params.title || "Auto-Fill",
                    type: result.params.type || "success",
                });
            }
        } catch (e) {
            this.notification.add("Auto-fill failed: " + (e.message || e), { type: "danger" });
        }
    }

    async duplicateBatch(batchId) {
        const batch = this.state.batches.find((b) => b.id === batchId);
        if (!batch) return;
        this.closeBatchesManager();
        this.openCreateDialog(batch);
    }

    async cancelBatch(batchId) {
        try {
            await this.orm.write("security.roster.batch", [batchId], { state: "cancelled" });
            await this.loadBatches();
            if (this.state.batchId === batchId) {
                this.state.batchId = null;
                this.state.slots = [];
            }
            this.notification.add("Batch cancelled.", { type: "info" });
        } catch (e) {
            this.notification.add("Could not cancel batch: " + (e.message || e), { type: "danger" });
        }
    }

    // ─── Batch Creation & Cycle Calculation ───────────────────────────

    async openCreateDialog(sourceBatch = null) {
        const now = new Date();
        let targetM = now.getMonth() + 1; // current month
        let targetY = now.getFullYear();

        if (sourceBatch) {
            // Next month relative to source batch
            const sDate = new Date(sourceBatch.date_to + "T00:00:00");
            sDate.setDate(sDate.getDate() + 5);
            targetM = sDate.getMonth() + 1;
            targetY = sDate.getFullYear();
        }

        const dlg = this.state.createDialog;
        dlg.visible = true;
        dlg.partnerId = sourceBatch ? (Array.isArray(sourceBatch.partner_id) ? sourceBatch.partner_id[0] : sourceBatch.partner_id) : null;
        dlg.siteId = sourceBatch ? (Array.isArray(sourceBatch.site_id) ? sourceBatch.site_id[0] : sourceBatch.site_id) : null;
        dlg.month = String(targetM).padStart(2, "0");
        dlg.year = String(targetY);
        dlg.cycleMode = "default";
        dlg.autoGenerateSlots = this.state.companyCycle.autoGenerate;
        dlg.copySourceId = sourceBatch ? sourceBatch.id : null;
        dlg.creating = false;
        dlg.error = "";

        await this.updateCycleDates();
    }

    closeCreateDialog() {
        this.state.createDialog.visible = false;
    }

    async onCycleModeChange(mode) {
        this.state.createDialog.cycleMode = mode;
        const now = new Date();
        if (mode === "current") {
            this.state.createDialog.month = String(now.getMonth() + 1).padStart(2, "0");
            this.state.createDialog.year = String(now.getFullYear());
        } else if (mode === "next") {
            let nextM = now.getMonth() + 2;
            let nextY = now.getFullYear();
            if (nextM > 12) { nextM = 1; nextY++; }
            this.state.createDialog.month = String(nextM).padStart(2, "0");
            this.state.createDialog.year = String(nextY);
        }
        await this.updateCycleDates();
    }

    async onDialogPartnerChange(ev) {
        const val = parseInt(ev.target.value);
        this.state.createDialog.partnerId = isNaN(val) ? null : val;
        this.state.createDialog.siteId = null;
        await this.validateCreateBatch();
    }

    async onDialogSiteChange(ev) {
        const val = parseInt(ev.target.value);
        this.state.createDialog.siteId = isNaN(val) ? null : val;
        await this.validateCreateBatch();
    }

    async onDialogMonthChange(ev) {
        this.state.createDialog.month = ev.target.value;
        await this.updateCycleDates();
    }

    async onDialogYearChange(ev) {
        this.state.createDialog.year = ev.target.value;
        await this.updateCycleDates();
    }

    async onDialogDateFromChange(ev) {
        this.state.createDialog.dateFrom = ev.target.value;
        this.state.createDialog.cycleMode = "custom";
        await this.validateCreateBatch();
    }

    async onDialogDateToChange(ev) {
        this.state.createDialog.dateTo = ev.target.value;
        this.state.createDialog.cycleMode = "custom";
        await this.validateCreateBatch();
    }

    async updateCycleDates() {
        const dlg = this.state.createDialog;
        if (dlg.cycleMode !== "custom" && dlg.month && dlg.year) {
            try {
                const res = await this.orm.call(
                    "res.config.settings",
                    "get_company_roster_cycle_defaults",
                    [],
                    { month: dlg.month, year: dlg.year }
                );
                if (res) {
                    dlg.dateFrom = res.date_from;
                    dlg.dateTo = res.date_to;
                }
            } catch {
                // fallback standard 1st to end of month
                const y = parseInt(dlg.year);
                const m = parseInt(dlg.month);
                dlg.dateFrom = `${y}-${String(m).padStart(2, "0")}-01`;
                const lastDay = new Date(y, m, 0).getDate();
                dlg.dateTo = `${y}-${String(m).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
            }
        }
        await this.validateCreateBatch();
    }

    async validateCreateBatch() {
        const dlg = this.state.createDialog;
        dlg.validating = true;
        dlg.error = "";
        try {
            const res = await this.orm.call(
                "security.roster.batch",
                "validate_batch_creation",
                [],
                {
                    partner_id: dlg.partnerId || false,
                    site_id: dlg.siteId || false,
                    date_from: dlg.dateFrom,
                    date_to: dlg.dateTo,
                }
            );
            dlg.validation = res;
        } catch {
            dlg.validation = { valid: true, errors: [], warnings: [], estimated_slots: 0 };
        } finally {
            dlg.validating = false;
        }
    }

    async confirmCreateBatch() {
        const dlg = this.state.createDialog;
        if (!dlg.partnerId && !dlg.siteId) {
            dlg.error = "Please select a client or client site.";
            return;
        }
        if (!dlg.dateFrom || !dlg.dateTo) {
            dlg.error = "Please specify Start Date and End Date.";
            return;
        }

        if (dlg.validation && !dlg.validation.valid) {
            dlg.error = (dlg.validation.errors || []).join(" ");
            return;
        }

        dlg.creating = true;
        dlg.error = "";
        try {
            const result = await this.orm.call(
                "security.roster.batch",
                "action_quick_create_batch",
                [],
                {
                    partner_id: dlg.partnerId || false,
                    site_id: dlg.siteId || false,
                    date_from: dlg.dateFrom,
                    date_to: dlg.dateTo,
                    auto_generate: dlg.autoGenerateSlots,
                    copy_source_id: dlg.copySourceId || false,
                }
            );
            dlg.visible = false;
            if (this.state.showBatchesDrawer) {
                this.state.showBatchesDrawer = false;
            }
            await this.loadBatches();
            this.state.batchId = result.batch_id;
            await this.loadBoard();
            this.notification.add(
                `Roster Batch created: ${result.batch_name} (${result.slot_count} slot${result.slot_count !== 1 ? "s" : ""})`,
                { type: "success" }
            );
        } catch (e) {
            dlg.error = e.message || "Failed to create roster batch.";
        } finally {
            dlg.creating = false;
        }
    }

    // ─── Board Event handlers ─────────────────────────────────────────────

    async onBatchChange(ev) {
        const val = ev.target.value;
        this.state.batchId = val ? parseInt(val) : null;
        this.state.filterSiteId = null;
        this.state.slots = [];
        this.state.sites = [];
        this.state.posts = [];
        this.state.dates = [];
        this.state.assignError = null;
        if (this.state.batchId) {
            await this.loadBoard();
        }
    }

    onSiteFilterChange(ev) {
        const val = ev.target.value;
        this.state.filterSiteId = val ? parseInt(val) : null;
    }

    async refreshBoard() {
        await this.loadBoard();
    }

    async autoFillSlots() {
        if (!this.state.batchId || this.state.autoFilling) return;
        this.state.autoFilling = true;
        try {
            const result = await this.orm.call(
                "security.roster.batch",
                "action_auto_fill_slots",
                [[this.state.batchId]]
            );
            // Reload board so critical-gap cells and assignments are reflected
            await this.loadBoard();
            if (result && result.params) {
                this.notification.add(result.params.message || "Auto-fill complete.", {
                    title: result.params.title || "Auto-Fill",
                    type: result.params.type || "success",
                    sticky: !!result.params.sticky,
                });
            }
        } catch (e) {
            this.notification.add("Auto-fill failed: " + (e.message || e), { type: "danger" });
        } finally {
            this.state.autoFilling = false;
        }
    }

    selectSlot(slot) {
        this.state.selectedSlot = slot;
        this.state.suggestions = [];
        this.state.suggestionsLoaded = false;
        this.state.assignError = null;  // clear error on new slot selection
    }

    closeSidebar() {
        this.state.selectedSlot = null;
        this.state.suggestions = [];
        this.state.suggestionsLoaded = false;
        this.state.assignError = null;
    }

    async loadSuggestions() {
        const slot = this.state.selectedSlot;
        if (!slot) return;
        this.state.loadingSuggestions = true;
        this.state.assignError = null;
        try {
            // Trigger scoring engine
            await this.orm.call("security.roster.slot", "action_suggest_guards", [[slot.id]]);
            // Read the generated suggestions
            const rawSugs = await this.orm.searchRead(
                "security.slot.suggestion",
                [["slot_id", "=", slot.id]],
                ["id", "rank", "employee_id", "employee_grade_id", "score", "score_breakdown"],
                { order: "rank" }
            );
            this.state.suggestions = rawSugs.map((s) => ({
                id: s.id,
                rank: s.rank,
                employee_id: s.employee_id[0],
                employee_name: s.employee_id[1],
                grade: s.employee_grade_id ? s.employee_grade_id[1] : null,
                score: s.score,
                score_breakdown: s.score_breakdown,
            }));
            this.state.suggestionsLoaded = true;
        } catch (e) {
            this.notification.add("Could not load suggestions: " + (e.message || e), { type: "warning" });
        } finally {
            this.state.loadingSuggestions = false;
        }
    }

    /**
     * Assign a guard to the selected slot via the suggestion record.
     *
     * Calls action_assign_to_slot on the matching security.slot.suggestion record.
     * The Python method returns:
     *   - null / False  → success
     *   - { tag: "display_notification", params: { title, message, type, sticky } }
     *                   → business-rule error (e.g. guard already assigned elsewhere)
     *
     * On error: show the notification inline (assignError) and as a toast.
     * On success: reload slot data and show a success toast.
     */
    async assignGuard(suggestion) {
        const slot = this.state.selectedSlot;
        if (!slot) return;
        this.state.assignError = null;
        try {
            const result = await this.orm.call(
                "security.slot.suggestion",
                "action_assign_to_slot",
                [[suggestion.id]]
            );

            // Python returned a notification dict — assignment blocked by a business rule
            if (result && result.tag === "display_notification") {
                const params = result.params || {};
                this.state.assignError = {
                    guardName: suggestion.employee_name,
                    message: params.message || "Assignment not allowed.",
                };
                this.notification.add(params.message || "Assignment not allowed.", {
                    title: params.title || "Cannot Assign",
                    type: params.type || "danger",
                    sticky: params.sticky || false,
                });
                return; // do not reload on failure
            }

            // Success: reload slots from server to reflect the new assignment
            await this.loadSlots(this.state.batchId);
            this.state.selectedSlot = null;
            this.state.suggestions = [];
            this.state.suggestionsLoaded = false;
            this.state.assignError = null;
            this.notification.add(
                `${suggestion.employee_name} assigned successfully.`,
                { type: "success" }
            );
        } catch (e) {
            const msg = e.message || "Assignment failed.";
            this.state.assignError = {
                guardName: suggestion.employee_name,
                message: msg,
            };
            this.notification.add(msg, { type: "danger" });
        }
    }

    async unassignSlot() {
        const slot = this.state.selectedSlot;
        if (!slot) return;
        this.state.assignError = null;
        try {
            await this.orm.write("security.roster.slot", [slot.id], {
                employee_id: false,
                state: "draft",
            });
            const localSlot = this.state.slots.find((s) => s.id === slot.id);
            if (localSlot) {
                localSlot.employee_id = null;
                localSlot.employee_name = null;
                localSlot.state = "draft";
            }
            this.state.selectedSlot = { ...slot, employee_id: null, employee_name: null, state: "draft" };
            this.state.stats.assigned = Math.max(0, this.state.stats.assigned - 1);
            this.state.stats.unassigned++;
            this.notification.add("Guard unassigned.", { type: "info" });
        } catch (e) {
            this.notification.add("Unassign failed: " + (e.message || e), { type: "danger" });
        }
    }

    async openCreateSlot() {
        if (!this.state.createSlot.dataLoaded) {
            const [allSites, allPosts, templates, employees] = await Promise.all([
                this.orm.searchRead(
                    "security.client.site",
                    [["active", "=", true]],
                    ["id", "name", "partner_id"],
                    { order: "name" }
                ),
                this.orm.searchRead(
                    "security.post",
                    [["active", "=", true]],
                    ["id", "name", "site_id"],
                    { order: "name" }
                ),
                this.orm.searchRead(
                    "security.shift.template",
                    [],
                    ["id", "name"],
                    { order: "name" }
                ),
                this.orm.searchRead(
                    "hr.employee",
                    [["security_guard", "=", true], ["active", "=", true]],
                    ["id", "name"],
                    { order: "name", limit: 300 }
                ),
            ]);
            this.state.createSlot.allSites = allSites;
            this.state.createSlot.allPosts = allPosts;
            this.state.createSlot.shiftTemplates = templates;
            this.state.createSlot.employees = employees;
            this.state.createSlot.dataLoaded = true;
        }
        if (this.state.batchDateFrom) {
            this.state.createSlot.form.shift_date = this.state.batchDateFrom;
        }
        this.state.createSlot.open = true;
    }

    closeCreateSlot() {
        this.state.createSlot.open = false;
        this.state.createSlot.form = {
            client_id: null,
            site_id: null,
            post_id: null,
            shift_template_id: null,
            employee_id: null,
            shift_date: this.state.batchDateFrom || null,
            count: 1,
        };
    }

    onCreateClientChange(ev) {
        this.state.createSlot.form.client_id = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.createSlot.form.site_id = null;
        this.state.createSlot.form.post_id = null;
    }

    onCreateSiteChange(ev) {
        this.state.createSlot.form.site_id = ev.target.value ? parseInt(ev.target.value) : null;
        this.state.createSlot.form.post_id = null;
    }

    onCreatePostChange(ev) {
        this.state.createSlot.form.post_id = ev.target.value ? parseInt(ev.target.value) : null;
    }

    onCreateShiftTemplateChange(ev) {
        this.state.createSlot.form.shift_template_id = ev.target.value ? parseInt(ev.target.value) : null;
    }

    onCreateEmployeeChange(ev) {
        this.state.createSlot.form.employee_id = ev.target.value ? parseInt(ev.target.value) : null;
    }

    async submitCreateSlot() {
        const { form } = this.state.createSlot;
        if (!form.post_id) {
            this.notification.add("Please select a Post.", { type: "warning" });
            return;
        }
        if (!form.shift_template_id) {
            this.notification.add("Please select a Shift Template.", { type: "warning" });
            return;
        }
        if (!form.shift_date) {
            this.notification.add("Please select a Shift Date.", { type: "warning" });
            return;
        }
        const count = Math.max(1, Math.min(20, parseInt(form.count) || 1));
        this.state.createSlot.saving = true;
        try {
            const slotVals = Array.from({ length: count }, () => {
                const vals = {
                    shift_date: form.shift_date,
                    post_id: parseInt(form.post_id),
                    shift_template_id: parseInt(form.shift_template_id),
                };
                if (this.state.batchId) {
                    vals.batch_id = this.state.batchId;
                }
                if (form.employee_id) {
                    vals.employee_id = parseInt(form.employee_id);
                    vals.state = "assigned";
                }
                return vals;
            });
            await this.orm.create("security.roster.slot", slotVals);
            this.notification.add(count + " slot(s) created.", { type: "success", title: "Slots Created" });
            this.closeCreateSlot();
            if (this.state.batchId) {
                await this.loadSlots(this.state.batchId);
            }
        } catch (e) {
            this.notification.add("Failed to create slot: " + (e.message || e), { type: "danger" });
        } finally {
            this.state.createSlot.saving = false;
        }
    }

    // ─── Context menu ───────────────────────────────────────────────

    onSlotContextMenu(slot, ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.state.contextMenu = { visible: true, x: ev.clientX, y: ev.clientY, slot };
    }

    closeContextMenu() {
        this.state.contextMenu = { visible: false, x: 0, y: 0, slot: null };
    }

    async contextMenuSuggest() {
        const slot = this.state.contextMenu.slot;
        this.closeContextMenu();
        this.selectSlot(slot);
        await this.loadSuggestions();
    }

    async contextMenuUnassign() {
        const slot = this.state.contextMenu.slot;
        this.closeContextMenu();
        this.state.selectedSlot = slot;
        await this.unassignSlot();
    }

    contextMenuViewGuard() {
        const slot = this.state.contextMenu.slot;
        this.closeContextMenu();
        if (!slot || !slot.employee_id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.employee",
            res_id: slot.employee_id,
            views: [[false, "form"]],
            target: "new",
        });
    }

    openSwapDialog(slot) {
        this.closeContextMenu();
        this.state.swapDialog = { visible: true, slot, reason: "" };
    }

    closeSwapDialog() {
        this.state.swapDialog = { visible: false, slot: null, reason: "" };
    }

    async confirmSwap() {
        const { slot, reason } = this.state.swapDialog;
        if (!slot) return;
        this.closeSwapDialog();
        try {
            if (reason) {
                await this.orm.call(
                    "security.roster.slot",
                    "action_log_override",
                    [[slot.id], reason]
                );
            }
            await this.orm.write("security.roster.slot", [slot.id], {
                employee_id: false,
                state: "draft",
            });
            await this.loadSlots(this.state.batchId);
            const updated = this.state.slots.find((s) => s.id === slot.id);
            if (updated) this.selectSlot(updated);
            this.notification.add(
                "Guard removed. Pick a replacement from the suggestions panel.",
                { type: "info" }
            );
        } catch (e) {
            this.notification.add("Swap failed: " + (e.message || e), { type: "danger" });
        }
    }

    // ─── Drag-and-drop ──────────────────────────────────────────────

    onDragStartSuggestion(sug, ev) {
        ev.dataTransfer.setData(
            "application/json",
            JSON.stringify({ employee_id: sug.employee_id, employee_name: sug.employee_name })
        );
        ev.dataTransfer.effectAllowed = "move";
    }

    onDragOverSlot(slot, ev) {
        if (slot.state === "cancelled" || slot.employee_id) return;
        ev.preventDefault();
        this.state.dragOverSlotId = slot.id;
        ev.dataTransfer.dropEffect = "move";
    }

    onDragLeaveSlot() {
        this.state.dragOverSlotId = null;
    }

    async onDropSlot(slot, ev) {
        ev.preventDefault();
        this.state.dragOverSlotId = null;
        if (slot.state === "cancelled" || slot.employee_id) return;
        let data;
        try {
            data = JSON.parse(ev.dataTransfer.getData("application/json"));
        } catch {
            return;
        }
        if (!data || !data.employee_id) return;
        try {
            await this.orm.write("security.roster.slot", [slot.id], {
                employee_id: data.employee_id,
                state: "assigned",
                critical_gap: false,
            });
            await this.loadSlots(this.state.batchId);
            this.notification.add(
                `${data.employee_name} assigned to ${slot.post_name}.`,
                { type: "success" }
            );
        } catch (e) {
            this.notification.add(
                "Drop assignment failed: " + (e.message || e),
                { type: "danger" }
            );
        }
    }

    // ─── Auto-assign all ────────────────────────────────────────────

    async autoAssignAll() {
        const unassigned = this.state.slots.filter(
            (s) => !s.employee_id && s.state !== "cancelled"
        );
        if (!unassigned.length) {
            this.notification.add("All slots are already assigned.", { type: "info" });
            return;
        }
        this.state.autoAssigning = true;
        this.state.assignError = null;
        const slotIds = unassigned.map((s) => s.id);
        try {
            const result = await this.orm.call(
                "security.roster.slot",
                "action_auto_assign_all",
                [slotIds]
            );
            if (result && result.tag === "display_notification") {
                const p = result.params || {};
                this.notification.add(p.message || "Auto-assignment complete.", {
                    title: p.title || "Auto-Assign",
                    type: p.type || "success",
                    sticky: p.sticky || false,
                });
            }
            await this.loadSlots(this.state.batchId);
            this.state.selectedSlot = null;
            this.state.suggestions = [];
            this.state.suggestionsLoaded = false;
        } catch (e) {
            this.notification.add("Auto-assignment failed: " + (e.message || e), {
                type: "danger",
            });
        } finally {
            this.state.autoAssigning = false;
        }
    }

    // ─── Helpers ────────────────────────────────────────────────────

    _buildDateRange(dateFrom, dateTo) {
        const dates = [];
        const start = new Date(dateFrom + "T00:00:00");
        const end = new Date(dateTo + "T00:00:00");
        const cur = new Date(start);
        while (cur <= end) {
            dates.push(cur.toISOString().slice(0, 10));
            cur.setDate(cur.getDate() + 1);
        }
        return dates;
    }

    _formatShift(template) {
        const fmt = (h) => {
            const hh = Math.floor(h).toString().padStart(2, "0");
            const mm = Math.round((h % 1) * 60).toString().padStart(2, "0");
            return `${hh}:${mm}`;
        };
        return `${fmt(template.start_hour)}–${fmt(template.end_hour)}`;
    }

    formatDateShort(dateStr) {
        const d = new Date(dateStr + "T00:00:00");
        return d.toLocaleDateString("en-ZA", { day: "2-digit", month: "short" });
    }

    formatDateLong(dateStr) {
        if (!dateStr) return "";
        const d = new Date(dateStr + "T00:00:00");
        return d.toLocaleDateString("en-ZA", { weekday: "long", day: "2-digit", month: "long", year: "numeric" });
    }

    dayName(dateStr) {
        const d = new Date(dateStr + "T00:00:00");
        return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()];
    }

    isWeekend(dateStr) {
        const day = new Date(dateStr + "T00:00:00").getDay();
        return day === 0 || day === 6;
    }

    isToday(dateStr) {
        return dateStr === new Date().toISOString().slice(0, 10);
    }
}

registry.category("actions").add("security_shift_planner.roster_board", RosterBoard);
