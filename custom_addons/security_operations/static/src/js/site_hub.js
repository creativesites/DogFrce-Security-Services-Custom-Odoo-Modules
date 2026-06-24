/** @odoo-module **/

import { Component, useState, onWillStart, onWillUpdateProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];
const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

class SiteHub extends Component {
    static template = "security_operations.SiteHub";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            site: null,
            activeTab: "overview",
            calendarData: null,
            calendarYear: new Date().getFullYear(),
            calendarMonth: new Date().getMonth() + 1,
            activePopoverDay: null,
            guards: [],
            requirements: [],
        });

        onWillStart(() => this._load());
    }

    get siteId() {
        return this.props.action?.context?.active_id;
    }

    get monthLabel() {
        return `${MONTH_NAMES[this.state.calendarMonth - 1]} ${this.state.calendarYear}`;
    }

    get calendarMonthStr() {
        const m = String(this.state.calendarMonth).padStart(2, "0");
        return `${this.state.calendarYear}-${m}`;
    }

    get calendarGrid() {
        const { calendarData } = this.state;
        if (!calendarData) return [];

        const { days_in_month, first_weekday, days } = calendarData;
        const cells = [];

        // Fill leading empty cells (first_weekday: 0=Mon … 6=Sun)
        for (let i = 0; i < first_weekday; i++) {
            cells.push(null);
        }

        for (let d = 1; d <= days_in_month; d++) {
            const m = String(this.state.calendarMonth).padStart(2, "0");
            const dd = String(d).padStart(2, "0");
            const key = `${this.state.calendarYear}-${m}-${dd}`;
            const dayData = days[key] || null;
            cells.push({ day: d, key, data: dayData });
        }

        // Group into weeks
        const weeks = [];
        for (let i = 0; i < cells.length; i += 7) {
            weeks.push(cells.slice(i, i + 7).concat(
                Array(Math.max(0, 7 - cells.slice(i, i + 7).length)).fill(null)
            ));
        }
        return weeks;
    }

    dayClass(cell) {
        if (!cell || !cell.data) return "sh-day sh-day-empty";
        const { total, assigned } = cell.data;
        if (total === 0) return "sh-day sh-day-no-slots";
        if (assigned === total) return "sh-day sh-day-full";
        if (assigned === 0) return "sh-day sh-day-none";
        return "sh-day sh-day-partial";
    }

    async _load() {
        if (!this.siteId) {
            this.state.loading = false;
            return;
        }

        const [site] = await this.orm.read(
            "security.client.site",
            [this.siteId],
            ["name", "partner_id", "location", "supervisor_id",
             "site_coverage_today", "site_coverage_month",
             "shift_requirement_ids", "post_ids"],
        );
        this.state.site = site;

        await Promise.all([
            this._loadCalendar(),
            this._loadGuards(),
            this._loadRequirements(),
        ]);

        this.state.loading = false;
    }

    async _loadCalendar() {
        if (!this.siteId) return;
        const data = await this.orm.call(
            "security.client.site",
            "get_calendar_data",
            [this.siteId, this.calendarMonthStr],
        );
        this.state.calendarData = data;
    }

    async _loadGuards() {
        if (!this.siteId) return;
        const slots = await this.orm.searchRead(
            "security.roster.slot",
            [
                ["site_id", "=", this.siteId],
                ["state", "!=", "cancelled"],
                ["employee_id", "!=", false],
            ],
            ["employee_id", "shift_date", "post_id", "shift_template_id", "state"],
            { limit: 50, order: "shift_date desc" },
        );
        // Deduplicate by employee
        const seen = new Set();
        this.state.guards = slots.filter(s => {
            const eid = s.employee_id[0];
            if (seen.has(eid)) return false;
            seen.add(eid);
            return true;
        });
    }

    async _loadRequirements() {
        if (!this.siteId) return;
        const reqs = await this.orm.searchRead(
            "security.shift.requirement",
            [["site_id", "=", this.siteId], ["active", "=", true]],
            ["post_id", "shift_template_id", "guard_count", "bill_rate", "pay_rate",
             "rate_multiplier", "fairness_weight", "preferred_employee_id"],
        );
        this.state.requirements = reqs;
    }

    setTab(tab) {
        this.state.activeTab = tab;
    }

    async prevMonth() {
        let { calendarYear, calendarMonth } = this.state;
        calendarMonth--;
        if (calendarMonth < 1) { calendarMonth = 12; calendarYear--; }
        this.state.calendarYear = calendarYear;
        this.state.calendarMonth = calendarMonth;
        this.state.activePopoverDay = null;
        await this._loadCalendar();
    }

    async nextMonth() {
        let { calendarYear, calendarMonth } = this.state;
        calendarMonth++;
        if (calendarMonth > 12) { calendarMonth = 1; calendarYear++; }
        this.state.calendarYear = calendarYear;
        this.state.calendarMonth = calendarMonth;
        this.state.activePopoverDay = null;
        await this._loadCalendar();
    }

    togglePopover(cell) {
        if (!cell || !cell.data) return;
        this.state.activePopoverDay =
            this.state.activePopoverDay === cell.key ? null : cell.key;
    }

    closePopover() {
        this.state.activePopoverDay = null;
    }

    openSiteForm() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.client.site",
            res_id: this.siteId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openSlotForm(slotId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.roster.slot",
            res_id: slotId,
            views: [[false, "form"]],
            target: "new",
        });
    }
}

registry.category("actions").add("security_operations.site_hub", SiteHub);
