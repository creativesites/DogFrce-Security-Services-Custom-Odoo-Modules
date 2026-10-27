/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const DAY_TYPES = [
    { key: "all", label: "All days" },
    { key: "weekday", label: "Mon–Fri" },
    { key: "sat", label: "Saturday" },
    { key: "sun", label: "Sunday" },
    { key: "ph", label: "Public holiday" },
];
const STATUSES = [
    { key: "all", label: "All sites" },
    { key: "unfilled", label: "Unfilled / Gaps" },
    { key: "clashes", label: "Clashes" },
    { key: "assigned", label: "Fully filled" },
];

function ymd(d) {
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
}

/** Operational cycle: 21st of one month to 20th of the next. */
function cycleFor(ref) {
    const y = ref.getFullYear(), m = ref.getMonth();
    const start = ref.getDate() >= 21 ? new Date(y, m, 21) : new Date(y, m - 1, 21);
    const end = new Date(start.getFullYear(), start.getMonth() + 1, 20);
    return {
        from: ymd(start),
        to: ymd(end),
        label: `${start.toLocaleDateString("en-GB", { day: "numeric", month: "short" })} – ${end.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}`
    };
}

export class RosterCycle extends Component {
    static template = "security_shift_planner.RosterCycle";
    static props = { "*": true };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.dayTypes = DAY_TYPES;
        this.statuses = STATUSES;

        // Operational cycles: 3 back and 3 forward from today.
        const today = new Date();
        this.cycles = [];
        for (let i = -3; i <= 3; i++) {
            this.cycles.push(cycleFor(new Date(today.getFullYear(), today.getMonth() + i, 21)));
        }
        const current = cycleFor(today);

        this.state = useState({
            cycle: current,
            siteId: "all",
            sites: [],
            dayType: "all",
            status: "all",
            shiftTemplate: "all",
            shiftTemplates: [],
            search: "",
            page: 1,
            pageSize: 15,
            loading: false,
            data: null,

            // Interactive Day Drawer State
            selectedDay: null,
            loadingDay: false,
            dayData: null,
            activeSlotId: null,
            poolTab: "regular",
            poolSearch: "",
            overrideModal: null,

            // Today's Roll Call & Live Gap Dispatch State
            showTodayRollCall: false,
            previousCycleBeforeRollCall: null,
            todayRollCallData: null,
            loadingRollCall: false,

            // One-Click Guard Shift Swap Modal State
            allAssignedSlots: [],
            swapModal: {
                visible: false,
                slotA: null,
                slotB: null,
                slotAId: null,
                slotBId: null,
                reason: "",
                preValidation: null,
                validating: false,
                submitting: false,
                error: "",
                searchQuery: "",
            },

            // Relief Candidate Pool Dispatch Modal State
            candidatePoolModal: {
                visible: false,
                slot: null,
                poolTab: "relief", // "relief", "regular", "all"
                searchQuery: "",
                loading: false,
                submitting: false,
                regularGuards: [],
                reliefGuards: [],
                allGuards: [],
                error: "",
                overrideModal: null,
            },
        });

        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.load();
        });
    }

    get pages() {
        const total = this.state.data?.total_sites || 0;
        return Math.max(1, Math.ceil(total / this.state.pageSize));
    }

    cellClass(cell, day) {
        if (!cell || !cell.total) return "rc-cell rc-empty";
        let base = "rc-cell rc-interactive";
        if (cell.clashes) return `${base} rc-clash`;
        if (cell.unfilled) return `${base} rc-gap`;
        return `${base} rc-full`;
    }

    cellText(cell) {
        if (!cell || !cell.total) return "";
        return `${cell.total - cell.unfilled}/${cell.total}`;
    }

    async loadFilterOptions() {
        try {
            const res = await this.orm.call("security.roster.slot", "get_filter_options", []);
            this.state.shiftTemplates = res.shift_templates || [];
            this.state.sites = res.sites || [];
        } catch (e) {
            console.warn("Could not load filter options", e);
        }
    }

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("security.roster.slot", "get_roster_cycle_grid", [], {
                date_from: this.state.cycle.from,
                date_to: this.state.cycle.to,
                site_ids: this.state.siteId !== "all" ? [parseInt(this.state.siteId)] : null,
                day_type: this.state.dayType,
                status: this.state.status,
                shift_template_id: this.state.shiftTemplate !== "all" ? parseInt(this.state.shiftTemplate) : null,
                search: this.state.search,
                page: this.state.page,
                page_size: this.state.pageSize,
            });
            this.state.data = data;
        } catch (e) {
            this.notification.add("Could not load the roster: " + (e.message || e), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    async setCycle(c) { this.state.cycle = c; this.state.page = 1; await this.load(); }
    async focusSite(siteId) {
        this.state.siteId = String(siteId);
        this.state.page = 1;
        await this.load();
    }

    async setSite(ev) { this.state.siteId = ev.target.value; this.state.page = 1; await this.load(); }
    async setDayType(k) { this.state.dayType = k; this.state.page = 1; await this.load(); }
    async setStatus(k) { this.state.status = k; this.state.page = 1; await this.load(); }
    async setShiftTemplate(ev) { this.state.shiftTemplate = ev.target.value; this.state.page = 1; await this.load(); }
    async onSearch(ev) { this.state.search = ev.target.value; this.state.page = 1; await this.load(); }
    async goPage(delta) {
        const next = Math.min(Math.max(1, this.state.page + delta), this.pages);
        if (next !== this.state.page) { this.state.page = next; await this.load(); }
    }
    isActive(current, key) { return current === key ? "active" : ""; }

    // --- Interactive Cell Click & Slot Assignment Drawer ---

    async openDayDrawer(row, day) {
        const cell = row.cells[day.date];
        if (!cell || !cell.total) {
            return; // no shifts for this site on this day
        }
        this.state.selectedDay = {
            site_id: row.site_id,
            site_name: row.site_name,
            client_name: row.client,
            shift_date: day.date,
            dow: day.dow,
            kind: day.kind,
        };
        this.state.activeSlotId = null;
        this.state.poolSearch = "";
        await this.loadDaySlots();
    }

    async loadDaySlots() {
        if (!this.state.selectedDay) return;
        this.state.loadingDay = true;
        try {
            const res = await this.orm.call("security.roster.slot", "get_slots_for_day", [], {
                site_id: this.state.selectedDay.site_id,
                shift_date: this.state.selectedDay.shift_date,
            });
            this.state.dayData = res;
        } catch (e) {
            this.notification.add("Could not load shift details: " + (e.message || e), { type: "danger" });
        } finally {
            this.state.loadingDay = false;
        }
    }

    closeDrawer() {
        this.state.selectedDay = null;
        this.state.dayData = null;
        this.state.activeSlotId = null;
        this.state.poolSearch = "";
    }

    toggleAssignDrawer(slotId) {
        if (this.state.activeSlotId === slotId) {
            this.state.activeSlotId = null;
        } else {
            this.state.activeSlotId = slotId;
            this.state.poolTab = "regular";
            this.state.poolSearch = "";
        }
    }

    setPoolTab(tab) {
        this.state.poolTab = tab;
    }

    onPoolSearch(ev) {
        this.state.poolSearch = ev.target.value;
    }

    getPoolGuards(slot) {
        const guards = this.state.poolTab === "regular" ? slot.regular_guards : slot.relief_guards;
        if (!this.state.poolSearch) return guards;
        const q = this.state.poolSearch.toLowerCase();
        return guards.filter(g =>
            g.name.toLowerCase().includes(q) || (g.code && g.code.toLowerCase().includes(q))
        );
    }

    async assignGuard(slotId, guardId, guardName = "", override = false, overrideReason = "") {
        try {
            const res = await this.orm.call(
                "security.roster.slot",
                "action_manual_assign",
                [[slotId], guardId, override, overrideReason]
            );
            if (res && res.status === "override_required") {
                this.state.overrideModal = {
                    visible: true,
                    slotId: slotId,
                    guardId: guardId,
                    guardName: guardName || res.guard_name || "Guard",
                    reasons: res.reasons || [],
                    reasonInput: "",
                };
                return;
            }
            if (res && res.status === "error") {
                this.notification.add(res.message || "Assignment rejected.", { type: "danger" });
                return;
            }
            this.notification.add("Guard assigned successfully", { type: "success" });
            this.state.activeSlotId = null;
            this.state.overrideModal = null;
            await this.loadDaySlots();
            this.load(); // refresh background grid metrics
        } catch (e) {
            this.notification.add("Assignment failed: " + (e.message || e), { type: "danger" });
        }
    }

    async submitOverride() {
        if (!this.state.overrideModal) return;
        const { slotId, guardId, guardName, reasonInput } = this.state.overrideModal;
        if (!reasonInput || !reasonInput.trim()) {
            this.notification.add("Please provide an override reason.", { type: "warning" });
            return;
        }
        await this.assignGuard(slotId, guardId, guardName, true, reasonInput.trim());
    }

    closeOverrideModal() {
        this.state.overrideModal = null;
    }

    async clearSlot(slotId) {
        try {
            await this.orm.call("security.roster.slot", "write", [[slotId], { employee_id: false, state: "draft" }]);
            this.notification.add("Shift cleared", { type: "info" });
            await this.loadDaySlots();
            this.load(); // refresh background grid metrics
        } catch (e) {
            this.notification.add("Could not clear shift: " + (e.message || e), { type: "danger" });
        }
    }

    openSite(siteId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.site",
            res_id: siteId,
            views: [[false, "form"]],
        });
    }

    openScheduleImportWizard() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.roster.schedule.import.wizard",
            views: [[false, "form"]],
            target: "new",
            context: {
                default_date_from: this.state.cycle.from,
                default_date_to: this.state.cycle.to,
                default_site_id: this.state.siteId !== "all" ? parseInt(this.state.siteId) : false,
            },
        }, {
            onClose: () => {
                this.load();
                if (this.state.activeCell) {
                    this.loadDaySlots();
                }
            }
        });
    }

    // --- Today's Roll Call & Live Gap Dispatch ---

    async toggleTodayRollCall() {
        this.state.showTodayRollCall = !this.state.showTodayRollCall;
        const todayStr = ymd(new Date());

        if (this.state.showTodayRollCall) {
            this.state.previousCycleBeforeRollCall = this.state.cycle;
            this.state.cycle = {
                from: todayStr,
                to: todayStr,
                label: `Today (${todayStr})`,
            };
            this.state.page = 1;
            await Promise.all([
                this.load(),
                this.loadTodayRollCall(),
            ]);
        } else {
            if (this.state.previousCycleBeforeRollCall) {
                this.state.cycle = this.state.previousCycleBeforeRollCall;
            } else {
                this.state.cycle = cycleFor(new Date());
            }
            this.state.page = 1;
            await this.load();
        }
    }

    async loadTodayRollCall() {
        const todayStr = ymd(new Date());
        this.state.loadingRollCall = true;
        try {
            const data = await this.orm.call(
                "security.roster.slot",
                "get_today_roll_call",
                [],
                { today_date: todayStr }
            );
            this.state.todayRollCallData = data;
        } catch (e) {
            console.error("Could not load today's roll call:", e);
        } finally {
            this.state.loadingRollCall = false;
        }
    }

    // --- One-Click Guard Shift Swap Modal ---

    async loadAllAssignedSlots() {
        try {
            const slots = await this.orm.searchRead(
                "security.roster.slot",
                [
                    ["shift_date", ">=", this.state.cycle.from],
                    ["shift_date", "<=", this.state.cycle.to],
                    ["state", "!=", "cancelled"],
                    ["employee_id", "!=", false],
                ],
                ["id", "shift_date", "site_id", "post_id", "shift_template_id", "employee_id"],
                { limit: 1000, order: "shift_date, site_id" }
            );
            this.state.allAssignedSlots = slots.map((s) => ({
                id: s.id,
                shift_date: s.shift_date,
                site_name: s.site_id ? s.site_id[1] : "—",
                post_name: s.post_id ? s.post_id[1] : "—",
                employee_id: s.employee_id ? s.employee_id[0] : null,
                employee_name: s.employee_id ? s.employee_id[1] : "—",
                shift_label: s.shift_template_id ? s.shift_template_id[1] : "Shift",
            }));
        } catch {
            this.state.allAssignedSlots = [];
        }
    }

    get assignedSlotsForSwap() {
        return this.state.allAssignedSlots || [];
    }

    get eligibleSlotBCandidates() {
        const slotA = this.state.swapModal.slotA;
        const q = (this.state.swapModal.searchQuery || "").toLowerCase();
        return this.assignedSlotsForSwap
            .filter((s) => !slotA || s.id !== slotA.id)
            .filter((s) => {
                if (!q) return true;
                return (
                    (s.employee_name && s.employee_name.toLowerCase().includes(q)) ||
                    (s.post_name && s.post_name.toLowerCase().includes(q)) ||
                    (s.site_name && s.site_name.toLowerCase().includes(q)) ||
                    (s.shift_date && s.shift_date.includes(q))
                );
            });
    }

    async openSwapModal(slot = null) {
        let slotA = slot;
        if (slotA) {
            slotA = {
                id: slot.id,
                shift_date: slot.shift_date || this.state.selectedDay?.shift_date || "",
                site_name: slot.site_name || this.state.selectedDay?.site_name || "—",
                post_name: slot.post_name || "—",
                employee_name: slot.employee ? slot.employee.name : (slot.employee_name || "Assigned Guard"),
                shift_label: slot.shift_template_name || slot.shift_label || "Shift",
            };
        }
        await this.loadAllAssignedSlots();
        if (!slotA && this.state.allAssignedSlots.length > 0) {
            slotA = this.state.allAssignedSlots[0];
        }

        this.state.swapModal = {
            visible: true,
            slotA: slotA,
            slotAId: slotA ? slotA.id : null,
            slotB: null,
            slotBId: null,
            reason: "",
            preValidation: null,
            validating: false,
            submitting: false,
            error: "",
            searchQuery: "",
        };
    }

    closeSwapModal() {
        this.state.swapModal = {
            visible: false,
            slotA: null,
            slotB: null,
            slotAId: null,
            slotBId: null,
            reason: "",
            preValidation: null,
            validating: false,
            submitting: false,
            error: "",
            searchQuery: "",
        };
    }

    async onSelectSwapSlotA(ev) {
        const slotId = parseInt(ev.target.value);
        const slot = this.state.allAssignedSlots.find((s) => s.id === slotId) || null;
        this.state.swapModal.slotA = slot;
        this.state.swapModal.slotAId = slotId;
        this.state.swapModal.preValidation = null;
        if (this.state.swapModal.slotBId) {
            await this.runSwapPreValidation();
        }
    }

    async onSelectSwapSlotB(ev) {
        const slotId = parseInt(ev.target.value);
        const slot = this.state.allAssignedSlots.find((s) => s.id === slotId) || null;
        this.state.swapModal.slotB = slot;
        this.state.swapModal.slotBId = slotId;
        await this.runSwapPreValidation();
    }

    async runSwapPreValidation() {
        const { slotAId, slotBId } = this.state.swapModal;
        if (!slotAId || !slotBId || slotAId === slotBId) {
            this.state.swapModal.preValidation = null;
            return;
        }
        this.state.swapModal.validating = true;
        this.state.swapModal.error = "";
        try {
            const res = await this.orm.call(
                "security.roster.slot",
                "action_validate_swap",
                [[slotAId], slotBId]
            );
            this.state.swapModal.preValidation = res;
            if (res && res.status === "error") {
                this.state.swapModal.error = res.message;
            }
        } catch (err) {
            this.state.swapModal.error = err.message || "Pre-validation failed.";
        } finally {
            this.state.swapModal.validating = false;
        }
    }

    setSwapReason(reasonText) {
        this.state.swapModal.reason = reasonText;
    }

    async confirmExecuteSwap() {
        const modal = this.state.swapModal;
        if (!modal.slotAId || !modal.slotBId) {
            this.state.swapModal.error = "Please select both shifts to swap.";
            return;
        }
        if (!modal.reason || !modal.reason.trim()) {
            this.state.swapModal.error = "A manager audit reason is mandatory for shift swaps.";
            return;
        }
        this.state.swapModal.submitting = true;
        this.state.swapModal.error = "";

        try {
            const res = await this.orm.call(
                "security.roster.slot",
                "action_swap_guards",
                [[modal.slotAId], modal.slotBId, modal.reason.trim(), true]
            );

            if (res && res.status === "error") {
                this.state.swapModal.error = res.message;
                this.state.swapModal.submitting = false;
                return;
            }

            this.notification.add(
                res.message || "Guard shift swap successfully executed!",
                { type: "success" }
            );
            this.closeSwapModal();
            if (this.state.showTodayRollCall) {
                await this.loadTodayRollCall();
            }
            if (this.state.selectedDay) {
                await this.loadDaySlots();
            }
            await this.load();
        } catch (e) {
            this.state.swapModal.error = e.message || "Swap execution failed.";
            this.state.swapModal.submitting = false;
        }
    }

    // --- Candidate Pool Relief Dispatch Modal ---

    get candidatesForDispatch() {
        const modal = this.state.candidatePoolModal;
        if (!modal) return [];
        let list = [];
        if (modal.poolTab === "relief") {
            list = modal.reliefGuards;
        } else if (modal.poolTab === "regular") {
            list = modal.regularGuards;
        } else {
            list = modal.allGuards;
        }
        const q = (modal.searchQuery || "").toLowerCase();
        if (!q) return list;
        return list.filter((g) =>
            (g.name && g.name.toLowerCase().includes(q)) ||
            (g.code && g.code.toLowerCase().includes(q)) ||
            (g.grade && g.grade.toLowerCase().includes(q))
        );
    }

    async openDispatchReliefModal(slot) {
        this.state.candidatePoolModal = {
            visible: true,
            slot: slot,
            poolTab: "relief",
            searchQuery: "",
            loading: true,
            submitting: false,
            regularGuards: [],
            reliefGuards: [],
            allGuards: [],
            error: "",
            overrideModal: null,
        };

        try {
            const poolInfo = await this.orm.call(
                "security.roster.slot",
                "get_slot_pool_info",
                [[slot.id]]
            );
            if (this.state.candidatePoolModal.visible) {
                this.state.candidatePoolModal.regularGuards = poolInfo.regular_guards || [];
                this.state.candidatePoolModal.reliefGuards = poolInfo.relief_guards || [];
            }
        } catch (err) {
            console.error("Could not load slot pool info", err);
        } finally {
            if (this.state.candidatePoolModal.visible) {
                this.state.candidatePoolModal.loading = false;
            }
        }
    }

    closeCandidatePoolModal() {
        this.state.candidatePoolModal = {
            visible: false,
            slot: null,
            poolTab: "relief",
            searchQuery: "",
            loading: false,
            submitting: false,
            regularGuards: [],
            reliefGuards: [],
            allGuards: [],
            error: "",
            overrideModal: null,
        };
    }

    async dispatchCandidateGuard(guardId, guardName, isOverride = false, overrideReason = "") {
        const modal = this.state.candidatePoolModal;
        if (!modal || !modal.slot) return;
        modal.submitting = true;
        modal.error = "";

        try {
            const res = await this.orm.call(
                "security.roster.slot",
                "action_manual_assign",
                [[modal.slot.id], guardId, isOverride, overrideReason]
            );

            if (res && res.status === "override_required") {
                modal.overrideModal = {
                    visible: true,
                    slotId: modal.slot.id,
                    guardId: guardId,
                    guardName: guardName || res.guard_name || "Guard",
                    reasons: res.reasons || [],
                    reasonInput: "",
                };
                modal.submitting = false;
                return;
            }

            if (res && res.status === "error") {
                modal.error = res.message;
                this.notification.add(res.message, { type: "danger" });
                modal.submitting = false;
                return;
            }

            this.notification.add(
                `Relief guard ${guardName} successfully dispatched to ${modal.slot.post_name}!`,
                { type: "success" }
            );
            this.closeCandidatePoolModal();
            if (this.state.showTodayRollCall) {
                await this.loadTodayRollCall();
            }
            if (this.state.selectedDay) {
                await this.loadDaySlots();
            }
            await this.load();
        } catch (e) {
            modal.error = e.message || "Dispatch failed.";
            modal.submitting = false;
        }
    }

    async submitDispatchOverride() {
        const modal = this.state.candidatePoolModal;
        if (!modal || !modal.overrideModal) return;
        const { guardId, guardName, reasonInput } = modal.overrideModal;
        if (!reasonInput || !reasonInput.trim()) {
            this.notification.add("An override reason is required.", { type: "warning" });
            return;
        }
        await this.dispatchCandidateGuard(guardId, guardName, true, reasonInput.trim());
    }

    closeDispatchOverride() {
        if (this.state.candidatePoolModal) {
            this.state.candidatePoolModal.overrideModal = null;
        }
    }
}

registry.category("actions").add("security_shift_planner.roster_cycle", RosterCycle);
