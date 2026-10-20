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
    { key: "unfilled", label: "Unfilled" },
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
    return { from: ymd(start), to: ymd(end), label: `${start.toLocaleDateString("en-GB", { day: "numeric", month: "short" })} – ${end.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" })}` };
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

        // Cycles: three back and three forward from today.
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
            search: "",
            page: 1,
            pageSize: 15,
            loading: false,
            data: null,
        });

        onWillStart(() => this.load());
    }

    get pages() {
        const total = this.state.data?.total_sites || 0;
        return Math.max(1, Math.ceil(total / this.state.pageSize));
    }

    cellClass(cell, day) {
        if (!cell || !cell.total) return "rc-cell rc-empty";
        if (cell.clashes) return "rc-cell rc-clash";
        if (cell.unfilled) return "rc-cell rc-gap";
        return "rc-cell rc-full";
    }

    cellText(cell) {
        if (!cell || !cell.total) return "";
        return `${cell.total - cell.unfilled}/${cell.total}`;
    }

    async load() {
        this.state.loading = true;
        try {
            const data = await this.orm.call("security.roster.slot", "get_roster_cycle_grid", [], {
                date_from: this.state.cycle.from,
                date_to: this.state.cycle.to,
                day_type: this.state.dayType,
                status: this.state.status,
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
    async onSearch(ev) { this.state.search = ev.target.value; this.state.page = 1; await this.load(); }
    async goPage(delta) {
        const next = Math.min(Math.max(1, this.state.page + delta), this.pages);
        if (next !== this.state.page) { this.state.page = next; await this.load(); }
    }
    isActive(current, key) { return current === key ? "active" : ""; }
}

registry.category("actions").add("security_shift_planner.roster_cycle", RosterCycle);
