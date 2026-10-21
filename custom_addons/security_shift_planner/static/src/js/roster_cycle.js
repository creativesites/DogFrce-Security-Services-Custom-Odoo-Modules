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

    async assignGuard(slotId, guardId) {
        try {
            await this.orm.call("security.roster.slot", "action_manual_assign", [[slotId], guardId]);
            this.notification.add("Guard assigned successfully", { type: "success" });
            this.state.activeSlotId = null;
            await this.loadDaySlots();
            this.load(); // refresh background grid metrics
        } catch (e) {
            this.notification.add("Assignment failed: " + (e.message || e), { type: "danger" });
        }
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
}

registry.category("actions").add("security_shift_planner.roster_cycle", RosterCycle);
