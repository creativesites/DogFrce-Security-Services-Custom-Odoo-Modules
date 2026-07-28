/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { RosterGrid } from "@security_shift_planner/js/roster_grid";

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
    static components = { RosterGrid };
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

            // ── all client sites & company cycle defaults
            allSites: [],
            companyCycle: { startDay: 21, endDay: 20, autoGenerate: true },

            // ── ineligibility override dialog
            overrideDialog: {
                visible: false,
                slot: null,
                guardId: null,
                guardName: "",
                reasons: [],
                reasonInput: "",
                submitting: false,
                error: "",
            },

            // ── guard directory & search
            allGuards: [],
            guardSearchTerm: "",
            guardTab: "suggested", // "suggested" or "all"

            // ── create-batch modal (New Monthly Roster Batch engine)
            createDialog: {
                visible: false,
                partnerId: null,
                siteId: null,
                month: "",
                year: "",
                cycleMode: "default",
                dateFrom: "",
                dateTo: "",
                autoGenerateSlots: true,
                copySourceId: null,
                validating: false,
                validation: null,
                creating: false,
                error: "",
            },
        });

        onWillStart(async () => {
            await this.loadCompanyCycle();
            await this.loadAllSites();
            await this.loadBatches();
            await this.loadAllGuards();
        });
    }

    async loadAllGuards() {
        try {
            const guards = await this.orm.searchRead(
                "hr.employee",
                [["security_guard", "=", true], ["active", "=", true], ["security_disqualified", "=", false]],
                ["id", "name", "security_grade_id"],
                { order: "name asc" }
            );
            this.state.allGuards = guards.map((g) => ({
                id: g.id,
                name: g.name,
                grade: g.security_grade_id ? g.security_grade_id[1] : "—",
            }));
        } catch {
            this.state.allGuards = [];
        }
    }

    // ─────────────────────────────────────────────────────────────────────────
    // Data loaders
    // ─────────────────────────────────────────────────────────────────────────

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
            // fallback defaults
        }
    }

    async loadAllSites() {
        try {
            const sites = await this.orm.searchRead(
                "security.client.site",
                [["active", "=", true]],
                ["id", "name", "partner_id"],
                { order: "name" }
            );
            this.state.allSites = sites;
        } catch {
            this.state.allSites = [];
        }
    }

    async loadBatches() {
        const batches = await this.orm.searchRead(
            "security.roster.batch",
            [["state", "not in", ["cancelled"]]],
            ["id", "name", "date_from", "date_to", "partner_id", "site_id", "state", "generated_slot_count"],
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
             "employee_id", "state", "suggestion_count", "fairness_warning",
             "critical_gap", "is_override", "override_reason", "wrong_fit_reasons"]
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
                id:                s.id,
                shift_date:        s.shift_date,
                site_id:           s.site_id?.[0]   ?? null,
                site_name:         s.site_id?.[1]   ?? "—",
                post_id:           s.post_id?.[0]   ?? null,
                post_name:         s.post_id?.[1]   ?? "—",
                employee_id:       s.employee_id?.[0] ?? null,
                employee_name:     s.employee_id?.[1] ?? null,
                state:             s.state,
                conflict:          !!s.fairness_warning,
                critical_gap:      !!s.critical_gap,
                is_override:       !!s.is_override,
                override_reason:   s.override_reason || "",
                wrong_fit_reasons: s.wrong_fit_reasons || "",
                shift_label:       tmpl ? this._fmtShift(tmpl) : "",
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
        const total    = active.length;
        const assigned = active.filter(s => s.employee_id).length;
        const unassigned = total - assigned;
        const overrides = active.filter(s => s.employee_id && s.is_override).length;
        const fulfillmentRate = total > 0 ? Math.round((assigned / total) * 100) : 0;
        const overrideRatio = total > 0 ? Math.round((overrides / total) * 100) : 0;
        const complianceScore = Math.max(0, 100 - overrideRatio);

        this.state.stats = {
            total,
            assigned,
            unassigned,
            overrides,
            fulfillmentRate,
            overrideRatio,
            complianceScore,
            conflicts:  active.filter(s => s.conflict).length,
            criticalGaps: active.filter(s => !s.employee_id && s.critical_gap).length,
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

    closeOverrideModal() {
        this.state.overrideDialog = {
            visible: false,
            slot: null,
            guardId: null,
            guardName: "",
            reasons: [],
            reasonInput: "",
            submitting: false,
            error: "",
        };
    }

    async confirmOverrideAssign() {
        const dlg = this.state.overrideDialog;
        if (!dlg.reasonInput || !dlg.reasonInput.trim()) {
            dlg.error = "Please enter an override reason for audit logging.";
            return;
        }
        dlg.submitting = true;
        dlg.error = "";
        const ok = await this.manualAssignGuard(
            dlg.slot,
            dlg.guardId,
            dlg.guardName,
            true,
            dlg.reasonInput.trim()
        );
        dlg.submitting = false;
        if (ok) {
            this.closeOverrideModal();
        }
    }

    async manualAssignGuard(slot, guardId, guardName, override = false, overrideReason = "", sourceSlotId = null) {
        this.state.assignError = null;
        try {
            const res = await this.orm.call(
                "security.roster.slot",
                "action_manual_assign",
                [[slot.id], guardId],
                { override: override, override_reason: overrideReason }
            );

            if (res.status === "hard_block") {
                this.state.assignError = { guardName, message: res.message };
                this.notification.add(res.message, { title: `Blocked: ${guardName}`, type: "danger" });
                return false;
            }

            if (res.status === "override_required") {
                this.state.overrideDialog = {
                    visible: true,
                    slot: slot,
                    guardId: guardId,
                    guardName: guardName,
                    reasons: res.reasons || [],
                    reasonInput: "",
                    submitting: false,
                    error: "",
                };
                return false;
            }

            if (res.status === "error") {
                this.state.assignError = { guardName, message: res.message };
                this.notification.add(res.message, { type: "danger" });
                return false;
            }

            if (res.status === "success") {
                if (sourceSlotId && sourceSlotId !== slot.id) {
                    await this.orm.write("security.roster.slot", [sourceSlotId], {
                        employee_id: false,
                        state: "draft",
                    });
                }
                await this.loadSlotsOnly();
                this.closePanel();
                this.state.assignError = null;

                if (res.is_override) {
                    this.notification.add(
                        `Assigned ${guardName} with manual override (WRONG FIT recorded).`,
                        { title: "Manual Override Recorded", type: "warning" }
                    );
                } else {
                    this.notification.add(
                        `${guardName} assigned successfully.`,
                        { type: "success" }
                    );
                }
                return true;
            }
        } catch (e) {
            this.notification.add("Assignment error: " + (e.message || e), { type: "danger" });
            return false;
        }
    }

    get filteredAllGuards() {
        const term = (this.state.guardSearchTerm || "").toLowerCase().trim();
        if (!term) return this.state.allGuards;
        return this.state.allGuards.filter(
            (g) => g.name.toLowerCase().includes(term) || (g.grade && g.grade.toLowerCase().includes(term))
        );
    }

    async assignGuard(sug) {
        if (!this.state.selectedSlot) return;
        await this.manualAssignGuard(this.state.selectedSlot, sug.employee_id, sug.employee_name);
    }

    async assignGuardDirect(guard) {
        if (!this.state.selectedSlot) return;
        await this.manualAssignGuard(this.state.selectedSlot, guard.id, guard.name);
    }

    async onDropSlot(slot, ev) {
        ev.preventDefault();
        if (slot.state === "cancelled") return;
        let data;
        try {
            const raw = ev.dataTransfer.getData("text/plain") || ev.dataTransfer.getData("application/json");
            data = JSON.parse(raw);
        } catch {
            return;
        }
        const guardId = data.employee_id || data.guardId;
        const guardName = data.employee_name || data.guardName || "Guard";
        if (!guardId) return;

        await this.manualAssignGuard(slot, guardId, guardName, false, "", data.sourceSlotId);
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
    // New Monthly Roster Batch Creation Modal Engine
    // ─────────────────────────────────────────────────────────────────────────

    async openCreateModal(sourceBatch = null) {
        const now = new Date();
        let targetM = now.getMonth() + 1;
        let targetY = now.getFullYear();

        if (sourceBatch) {
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

    closeCreateModal() {
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
            await this.loadBatches();
            this.state.batchId = result.batch_id;
            await this.loadBoardData();
            this.state.view = "roster";
            this.notification.add(
                `Monthly Roster Batch created: ${result.batch_name} (${result.slot_count} slot${result.slot_count !== 1 ? "s" : ""})`,
                { type: "success" }
            );
        } catch (e) {
            dlg.error = e.message || "Failed to create roster batch.";
        } finally {
            dlg.creating = false;
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
