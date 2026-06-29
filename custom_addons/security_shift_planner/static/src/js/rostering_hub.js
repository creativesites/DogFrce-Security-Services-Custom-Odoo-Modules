/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * RosteringHub — Single-page rostering workspace.
 *
 * Three views accessible via tab nav (desktop) / bottom nav (mobile):
 *   dashboard  — coverage stats, today's shifts, alerts, quick actions
 *   roster     — full monthly grid (desktop) / day-by-day card list (mobile)
 *   setup      — batch creation, slot generation, workflow (submit/approve/confirm)
 *
 * Guard assignment opens a right-panel drawer on desktop and a bottom-sheet on mobile.
 * Batch creation uses an inline modal — no navigation away from the page.
 */
class RosteringHub extends Component {
    static props = { "*": true };
    static template = "security_shift_planner.RosteringHub";

    setup() {
        this.orm          = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            // ── navigation
            view: "dashboard",          // "dashboard" | "roster" | "setup"

            // ── loading flags
            loading:       false,
            autoAssigning: false,
            generating:    false,
            creating:      false,

            // ── batch list
            batches: [],
            batchId: null,
            batch:   null,             // full batch object currently selected

            // ── grid data
            dates:        [],
            sites:        [],
            posts:        [],
            slots:        [],
            filterSiteId: null,
            mobileDayIdx: 0,           // index into dates[] for mobile day view

            // ── guard assignment panel
            selectedSlot:      null,
            panelOpen:         false,
            suggestions:       [],
            suggestionsLoaded: false,
            loadingSuggestions: false,
            assignError:       null,   // { guardName, message }

            // ── dashboard data
            stats: { total: 0, assigned: 0, unassigned: 0, conflicts: 0 },
            todaySlots: [],
            alerts:     [],

            // ── create-batch modal
            showCreate: false,
            newBatch:   { date_from: "", date_to: "", note: "" },
        });

        onWillStart(() => this.loadBatches());
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Data loaders
    // ─────────────────────────────────────────────────────────────────────────

    async loadBatches() {
        const batches = await this.orm.searchRead(
            "security.roster.batch",
            [["state", "not in", ["cancelled"]]],
            ["id", "name", "date_from", "date_to", "site_id", "state", "generated_slot_count"],
            { order: "date_from desc", limit: 60 }
        );
        this.state.batches = batches;

        if (batches.length && !this.state.batchId) {
            this.state.batchId = batches[0].id;
            this.state.batch   = batches[0];
            await this.loadBoardData();
        }
    }

    async loadBoardData() {
        if (!this.state.batchId) return;
        this.state.loading      = true;
        this.state.selectedSlot = null;
        this.state.panelOpen    = false;
        this.state.suggestions  = [];
        this.state.suggestionsLoaded = false;
        this.state.assignError  = null;

        const batch = this.state.batches.find(b => b.id === this.state.batchId);
        if (!batch) { this.state.loading = false; return; }
        this.state.batch = batch;
        this.state.dates = this._buildDateRange(batch.date_from, batch.date_to);
        if (this.state.mobileDayIdx >= this.state.dates.length)
            this.state.mobileDayIdx = 0;

        await this._fetchAndApplySlots();
        this.state.loading = false;
    }

    async loadSlotsOnly() {
        await this._fetchAndApplySlots();
    }

    async _fetchAndApplySlots() {
        const rawSlots = await this.orm.searchRead(
            "security.roster.slot",
            [["batch_id", "=", this.state.batchId]],
            ["id", "shift_date", "site_id", "post_id", "shift_template_id",
             "employee_id", "state", "suggestion_count", "fairness_warning"]
        );

        const tplIds = [...new Set(rawSlots.map(s => s.shift_template_id?.[0]).filter(Boolean))];
        const tplMap = {};
        if (tplIds.length) {
            (await this.orm.searchRead(
                "security.shift.template", [["id", "in", tplIds]],
                ["id", "start_hour", "end_hour"]
            )).forEach(t => { tplMap[t.id] = t; });
        }

        this.state.slots = rawSlots.map(s => {
            const tmpl = s.shift_template_id ? tplMap[s.shift_template_id[0]] : null;
            return {
                id:            s.id,
                shift_date:    s.shift_date,
                site_id:       s.site_id?.[0]   ?? null,
                site_name:     s.site_id?.[1]   ?? "—",
                post_id:       s.post_id?.[0]   ?? null,
                post_name:     s.post_id?.[1]   ?? "—",
                employee_id:   s.employee_id?.[0] ?? null,
                employee_name: s.employee_id?.[1] ?? null,
                state:         s.state,
                conflict:      !!s.fairness_warning,
                shift_label:   tmpl ? this._fmtShift(tmpl) : "",
            };
        });

        // Build site/post index
        const siteMap = {}, postMap = {};
        this.state.slots.forEach(s => {
            if (s.site_id && !siteMap[s.site_id])
                siteMap[s.site_id] = { id: s.site_id, name: s.site_name };
            if (s.post_id && !postMap[s.post_id])
                postMap[s.post_id] = { id: s.post_id, name: s.post_name, site_id: s.site_id };
        });
        this.state.sites = Object.values(siteMap).sort((a, b) => a.name.localeCompare(b.name));
        this.state.posts = Object.values(postMap);

        this._refreshStats();
        this._buildAlerts();
        this._buildTodaySlots();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Stats & alerts
    // ─────────────────────────────────────────────────────────────────────────

    _refreshStats() {
        const active   = this.state.slots.filter(s => s.state !== "cancelled");
        const assigned = active.filter(s => s.employee_id).length;
        this.state.stats = {
            total:      active.length,
            assigned,
            unassigned: active.length - assigned,
            conflicts:  active.filter(s => s.conflict).length,
        };
    }

    _buildAlerts() {
        const a = [];
        const { conflicts, unassigned } = this.state.stats;
        if (conflicts)
            a.push({ type: "danger",  icon: "fa-exclamation-triangle",
                     text: `${conflicts} slot(s) have fairness conflicts.` });
        if (unassigned)
            a.push({ type: "warning", icon: "fa-user-times",
                     text: `${unassigned} slot(s) still unassigned.` });
        if (this.state.batch?.state === "draft")
            a.push({ type: "info",    icon: "fa-info-circle",
                     text: "Batch is in Draft — go to Setup to generate slots." });
        if (this.state.batch?.state === "generated" && unassigned === 0 && this.state.stats.total > 0)
            a.push({ type: "success", icon: "fa-check-circle",
                     text: "All slots assigned! Ready to submit for approval." });
        this.state.alerts = a;
    }

    _buildTodaySlots() {
        const today = new Date().toISOString().slice(0, 10);
        this.state.todaySlots = this.state.slots.filter(
            s => s.shift_date === today && s.state !== "cancelled"
        );
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Computed getters
    // ─────────────────────────────────────────────────────────────────────────

    get coveragePercent() {
        const { total, assigned } = this.state.stats;
        return total ? Math.round((assigned / total) * 100) : 0;
    }

    get visibleSites() {
        return this.state.filterSiteId
            ? this.state.sites.filter(s => s.id === this.state.filterSiteId)
            : this.state.sites;
    }

    get unassignedCount() {
        return this.state.slots.filter(s => !s.employee_id && s.state !== "cancelled").length;
    }

    get currentMobileDate() {
        return this.state.dates[this.state.mobileDayIdx] ?? null;
    }

    get batchWorkflowActions() {
        const s = this.state.batch?.state;
        const actions = [];
        if (s === "draft")
            actions.push({ label: "Generate Slots", method: "_generateSlots",
                           icon: "fa-cogs", cls: "rh-btn-primary" });
        if (s === "generated")
            actions.push(
                { label: "Copy Previous Month", method: "_copyPrevious",
                  icon: "fa-copy", cls: "rh-btn-ghost" },
                { label: "Submit for Approval",  method: "_submit",
                  icon: "fa-paper-plane", cls: "rh-btn-primary" }
            );
        if (s === "submitted")
            actions.push(
                { label: "Approve",  method: "_approve",  icon: "fa-check",  cls: "rh-btn-success" },
                { label: "Reject",   method: "_reject",   icon: "fa-times",  cls: "rh-btn-danger" }
            );
        if (s === "approved")
            actions.push(
                { label: "Confirm",  method: "_confirm",  icon: "fa-check-double", cls: "rh-btn-success" }
            );
        if (!["cancelled", "confirmed"].includes(s))
            actions.push({ label: "Cancel Batch", method: "_cancel",
                           icon: "fa-ban", cls: "rh-btn-danger" });
        return actions;
    }

    getPostsForSite(siteId) {
        return this.state.posts.filter(p => p.site_id === siteId);
    }

    getSlotsForCell(siteId, postId, dateStr) {
        return this.state.slots.filter(
            s => s.site_id === siteId && s.post_id === postId && s.shift_date === dateStr
        );
    }

    getSlotsForDay(dateStr) {
        return this.state.slots.filter(
            s => s.shift_date === dateStr && s.state !== "cancelled"
        );
    }

    batchStateColor(st) {
        return ({ draft:"#94a3b8", generated:"#3b82f6", submitted:"#f59e0b",
                  approved:"#8b5cf6", confirmed:"#16a34a" })[st] ?? "#64748b";
    }

    batchStateBg(st) {
        return ({ draft:"#f1f5f9", generated:"#eff6ff", submitted:"#fffbeb",
                  approved:"#f5f3ff", confirmed:"#f0fdf4" })[st] ?? "#f8fafc";
    }

    scoreColor(v) { return v >= 80 ? "#16a34a" : v >= 50 ? "#ca8a04" : "#dc2626"; }
    scoreBarColor(v) { return v >= 80 ? "#16a34a" : v >= 50 ? "#f59e0b" : "#ef4444"; }

    alertBg(type) {
        return ({ danger:"#fef2f2", warning:"#fffbeb", info:"#eff6ff", success:"#f0fdf4" })[type] ?? "#f8fafc";
    }
    alertColor(type) {
        return ({ danger:"#991b1b", warning:"#92400e", info:"#1e40af", success:"#166534" })[type] ?? "#475569";
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Navigation
    // ─────────────────────────────────────────────────────────────────────────

    setView(v) { this.state.view = v; }

    prevDay() { if (this.state.mobileDayIdx > 0) this.state.mobileDayIdx--; }
    nextDay() {
        if (this.state.mobileDayIdx < this.state.dates.length - 1) this.state.mobileDayIdx++;
    }

    async onBatchChange(ev) {
        const val = ev.target.value;
        this.state.batchId = val ? parseInt(val) : null;
        this.state.slots   = [];
        this.state.sites   = [];
        this.state.posts   = [];
        this.state.dates   = [];
        this.state.filterSiteId = null;
        if (this.state.batchId) await this.loadBoardData();
    }

    onSiteFilter(ev) {
        const val = ev.target.value;
        this.state.filterSiteId = val ? parseInt(val) : null;
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Guard assignment panel
    // ─────────────────────────────────────────────────────────────────────────

    selectSlot(slot) {
        this.state.selectedSlot      = slot;
        this.state.panelOpen         = true;
        this.state.suggestions       = [];
        this.state.suggestionsLoaded = false;
        this.state.assignError       = null;
    }

    closePanel() {
        this.state.panelOpen         = false;
        this.state.selectedSlot      = null;
        this.state.suggestions       = [];
        this.state.suggestionsLoaded = false;
        this.state.assignError       = null;
    }

    async loadSuggestions() {
        const slot = this.state.selectedSlot;
        if (!slot) return;
        this.state.loadingSuggestions = true;
        this.state.assignError = null;
        try {
            await this.orm.call("security.roster.slot", "action_suggest_guards", [[slot.id]]);
            const raw = await this.orm.searchRead(
                "security.slot.suggestion",
                [["slot_id", "=", slot.id]],
                ["id", "rank", "employee_id", "employee_grade_id", "score", "score_breakdown"],
                { order: "rank" }
            );
            this.state.suggestions = raw.map(s => ({
                id:              s.id,
                rank:            s.rank,
                employee_id:     s.employee_id[0],
                employee_name:   s.employee_id[1],
                grade:           s.employee_grade_id?.[1] ?? null,
                score:           s.score,
                score_breakdown: s.score_breakdown,
            }));
            this.state.suggestionsLoaded = true;
        } catch (e) {
            this.notification.add("Could not load suggestions: " + (e.message || e), { type: "warning" });
        } finally {
            this.state.loadingSuggestions = false;
        }
    }

    async assignGuard(sug) {
        if (!this.state.selectedSlot) return;
        this.state.assignError = null;
        try {
            const res = await this.orm.call(
                "security.slot.suggestion", "action_assign_to_slot", [[sug.id]]
            );
            if (res?.tag === "display_notification") {
                const p = res.params || {};
                this.state.assignError = { guardName: sug.employee_name, message: p.message || "Assignment not allowed." };
                this.notification.add(p.message || "Assignment not allowed.", {
                    title: p.title || "Cannot Assign", type: p.type || "danger",
                });
                return;
            }
            await this.loadSlotsOnly();
            this.closePanel();
            this.notification.add(`${sug.employee_name} assigned.`, { type: "success" });
        } catch (e) {
            const msg = e.message || "Assignment failed.";
            this.state.assignError = { guardName: sug.employee_name, message: msg };
            this.notification.add(msg, { type: "danger" });
        }
    }

    async unassignSlot() {
        const slot = this.state.selectedSlot;
        if (!slot) return;
        this.state.assignError = null;
        try {
            await this.orm.write("security.roster.slot", [slot.id], {
                employee_id: false, state: "draft",
            });
            await this.loadSlotsOnly();
            // Update selected slot reference
            const updated = this.state.slots.find(s => s.id === slot.id);
            if (updated) this.state.selectedSlot = updated;
            this.state.suggestions       = [];
            this.state.suggestionsLoaded = false;
            this.notification.add("Guard unassigned.", { type: "info" });
        } catch (e) {
            this.notification.add("Unassign failed: " + (e.message || e), { type: "danger" });
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Auto-assign
    // ─────────────────────────────────────────────────────────────────────────

    async autoAssignAll() {
        const unassigned = this.state.slots.filter(
            s => !s.employee_id && s.state !== "cancelled"
        );
        if (!unassigned.length) {
            this.notification.add("All slots are already assigned.", { type: "info" });
            return;
        }
        this.state.autoAssigning = true;
        try {
            const res = await this.orm.call(
                "security.roster.slot",
                "action_auto_assign_all",
                [unassigned.map(s => s.id)]
            );
            if (res?.tag === "display_notification") {
                const p = res.params || {};
                this.notification.add(p.message || "Auto-assignment complete.", {
                    title: p.title || "Auto-Assign", type: p.type || "success",
                });
            }
            await this.loadSlotsOnly();
        } catch (e) {
            this.notification.add("Auto-assignment failed: " + (e.message || e), { type: "danger" });
        } finally {
            this.state.autoAssigning = false;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Batch workflow
    // ─────────────────────────────────────────────────────────────────────────

    async _callBatch(method) {
        try {
            await this.orm.call("security.roster.batch", method, [[this.state.batchId]]);
            await this.loadBatches();
            this.notification.add("Batch updated.", { type: "success" });
        } catch (e) {
            this.notification.add("Action failed: " + (e.message || e), { type: "danger" });
        }
    }

    async _generateSlots() {
        this.state.generating = true;
        try {
            await this.orm.call("security.roster.batch", "action_generate_slots", [[this.state.batchId]]);
            await this.loadBatches();
            await this.loadBoardData();
            this.notification.add("Slots generated successfully.", { type: "success" });
        } catch (e) {
            this.notification.add("Generate failed: " + (e.message || e), { type: "danger" });
        } finally {
            this.state.generating = false;
        }
    }

    async _copyPrevious() {
        try {
            const res = await this.orm.call(
                "security.roster.batch", "action_copy_from_previous_month", [[this.state.batchId]]
            );
            if (res?.tag === "display_notification") {
                const p = res.params || {};
                this.notification.add(p.message || "Copied.", { title: p.title, type: p.type || "info" });
            }
            await this.loadBoardData();
        } catch (e) {
            this.notification.add("Copy failed: " + (e.message || e), { type: "danger" });
        }
    }

    _submit()  { return this._callBatch("action_submit"); }
    _approve() { return this._callBatch("action_approve"); }
    _reject()  { return this._callBatch("action_reject"); }
    _confirm() { return this._callBatch("action_confirm"); }
    _cancel()  { return this._callBatch("action_cancel"); }

    async runWorkflowAction(method) {
        return this[method]();
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Batch creation modal
    // ─────────────────────────────────────────────────────────────────────────

    openCreateModal() {
        const today   = new Date();
        const first   = new Date(today.getFullYear(), today.getMonth() + 1, 1);
        const last    = new Date(today.getFullYear(), today.getMonth() + 2, 0);
        this.state.newBatch = {
            date_from: first.toISOString().slice(0, 10),
            date_to:   last.toISOString().slice(0, 10),
            note: "",
        };
        this.state.showCreate = true;
    }

    closeCreateModal() { this.state.showCreate = false; }

    onNewField(field, ev) {
        this.state.newBatch = { ...this.state.newBatch, [field]: ev.target.value };
    }

    async createBatch() {
        const nb = this.state.newBatch;
        if (!nb.date_from || !nb.date_to) {
            this.notification.add("Please set both start and end dates.", { type: "warning" });
            return;
        }
        this.state.creating = true;
        try {
            const newId = await this.orm.create("security.roster.batch", [{
                date_from: nb.date_from,
                date_to:   nb.date_to,
                note:      nb.note || false,
            }]);
            this.state.showCreate = false;
            await this.loadBatches();
            this.state.batchId = newId;
            this.state.batch   = this.state.batches.find(b => b.id === newId) || null;
            await this.loadBoardData();
            this.state.view = "setup";
            this.notification.add("Batch created. Now generate slots to populate the roster.", { type: "success" });
        } catch (e) {
            this.notification.add("Create failed: " + (e.message || e), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Utilities
    // ─────────────────────────────────────────────────────────────────────────

    _buildDateRange(from, to) {
        const dates = [];
        const cur = new Date(from + "T00:00:00"), end = new Date(to + "T00:00:00");
        while (cur <= end) { dates.push(cur.toISOString().slice(0, 10)); cur.setDate(cur.getDate() + 1); }
        return dates;
    }

    _fmtShift(t) {
        const f = h => `${Math.floor(h).toString().padStart(2,"0")}:${Math.round((h%1)*60).toString().padStart(2,"0")}`;
        return `${f(t.start_hour)}–${f(t.end_hour)}`;
    }

    fmtDateShort(d) {
        return new Date(d + "T00:00:00").toLocaleDateString("en-ZA", { day:"2-digit", month:"short" });
    }
    fmtDateFull(d) {
        if (!d) return "";
        return new Date(d + "T00:00:00").toLocaleDateString("en-ZA",
            { weekday:"long", day:"2-digit", month:"long", year:"numeric" });
    }
    fmtDateMed(d) {
        return new Date(d + "T00:00:00").toLocaleDateString("en-ZA",
            { weekday:"short", day:"2-digit", month:"short" });
    }

    dayName(d) { return ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][new Date(d+"T00:00:00").getDay()]; }
    isWeekend(d) { const x = new Date(d+"T00:00:00").getDay(); return x===0||x===6; }
    isToday(d)   { return d === new Date().toISOString().slice(0,10); }
}

registry.category("actions").add("security_shift_planner.rostering_hub", RosteringHub);
