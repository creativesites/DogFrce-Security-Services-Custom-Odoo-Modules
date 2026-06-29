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
            allSites: [],
            createDialog: {
                visible: false,
                partnerId: null,
                siteId: null,
                month: "",
                year: "",
                creating: false,
                error: "",
            },
        });

        onWillStart(async () => {
            await Promise.all([this.loadBatches(), this.loadAllSites()]);
        });
    }

    // ─── Data loaders ──────────────────────────────────────────────

    async loadBatches() {
        const batches = await this.orm.searchRead(
            "security.roster.batch",
            [["state", "not in", ["cancelled"]]],
            ["id", "name", "date_from", "date_to", "site_id", "state"],
            { order: "date_from desc", limit: 50 }
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

    // ─── Event handlers ─────────────────────────────────────────────

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

    openCreateDialog() {
        const now = new Date();
        let nextM = now.getMonth() + 2;
        let nextY = now.getFullYear();
        if (nextM > 12) { nextM = 1; nextY++; }
        const dlg = this.state.createDialog;
        dlg.visible = true;
        dlg.partnerId = null;
        dlg.siteId = null;
        dlg.month = String(nextM).padStart(2, "0");
        dlg.year = String(nextY);
        dlg.creating = false;
        dlg.error = "";
    }

    closeCreateDialog() {
        this.state.createDialog.visible = false;
    }

    onDialogPartnerChange(ev) {
        const val = parseInt(ev.target.value);
        this.state.createDialog.partnerId = isNaN(val) ? null : val;
        this.state.createDialog.siteId = null;
        this.state.createDialog.error = "";
    }

    onDialogSiteChange(ev) {
        const val = parseInt(ev.target.value);
        this.state.createDialog.siteId = isNaN(val) ? null : val;
    }

    onDialogMonthChange(ev) { this.state.createDialog.month = ev.target.value; }
    onDialogYearChange(ev)  { this.state.createDialog.year  = ev.target.value; }

    async confirmCreateBatch() {
        const dlg = this.state.createDialog;
        if (!dlg.partnerId) { dlg.error = "Please select a client."; return; }
        if (!dlg.month || !dlg.year) { dlg.error = "Please select a month and year."; return; }
        const y = parseInt(dlg.year);
        const m = parseInt(dlg.month);
        const dateFrom = `${y}-${String(m).padStart(2, "0")}-01`;
        const lastDay = new Date(y, m, 0).getDate();
        const dateTo = `${y}-${String(m).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
        dlg.creating = true;
        dlg.error = "";
        try {
            const result = await this.orm.call(
                "security.roster.batch",
                "action_quick_create_batch",
                [],
                { partner_id: dlg.partnerId, site_id: dlg.siteId || false, date_from: dateFrom, date_to: dateTo }
            );
            dlg.visible = false;
            await this.loadBatches();
            this.state.batchId = result.batch_id;
            await this.loadBoard();
            this.notification.add(
                `Roster created: ${result.batch_name} (${result.slot_count} slot${result.slot_count !== 1 ? "s" : ""})`,
                { type: "success" }
            );
        } catch (e) {
            dlg.error = e.message || "Failed to create roster. Ensure shift requirements are configured for this site.";
            dlg.creating = false;
        }
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
