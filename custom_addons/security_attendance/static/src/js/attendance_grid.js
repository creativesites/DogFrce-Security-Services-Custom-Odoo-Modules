/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class AttendanceSummaryGrid extends Component {
    static template = "security_attendance.AttendanceSummaryGrid";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: null,
            filterSiteId: null,
            monthStr: null,
            siteSearchTerm: "",
            activeDayModal: null,
        });
        onWillStart(() => this._load());
    }

    async _load() {
        this.state.loading = true;
        const data = await this.orm.call(
            "security.attendance.grid",
            "get_grid_data",
            [this.state.monthStr, this.state.filterSiteId]
        );
        this.state.data = data;
        if (!this.state.monthStr) this.state.monthStr = data.month_str;
        this.state.loading = false;
    }

    prevMonth() {
        const [y, m] = this.state.monthStr.split("-").map(Number);
        const prev = m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, "0")}`;
        this.state.monthStr = prev;
        this._load();
    }

    nextMonth() {
        const [y, m] = this.state.monthStr.split("-").map(Number);
        const next = m === 12 ? `${y + 1}-01` : `${y}-${String(m + 1).padStart(2, "0")}`;
        this.state.monthStr = next;
        this._load();
    }

    goToday() {
        const now = new Date();
        const curMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
        this.state.monthStr = curMonth;
        this._load();
    }

    setSite(id) {
        this.state.filterSiteId = id ? parseInt(id) : null;
        this._load();
    }

    openDayModal(cell) {
        if (!cell || cell.scheduled === 0) return;
        this.state.activeDayModal = cell;
    }

    closeDayModal() {
        this.state.activeDayModal = null;
    }

    openPostingConsole(dateStr) {
        this.closeDayModal();
        this.action.doAction({
            type: "ir.actions.client",
            tag: "security_attendance.posting_console",
            params: { date: dateStr },
        });
    }

    openAttendanceRecords(dateStr) {
        this.closeDayModal();
        this.action.doAction({
            name: `Attendance Records - ${dateStr}`,
            type: "ir.actions.act_window",
            res_model: "security.attendance.record",
            domain: [["shift_date", "=", dateStr]],
            views: [[false, "list"], [false, "form"]],
            target: "current",
        });
    }

    get calendarGrid() {
        if (!this.state.data) return [];
        const days = this.state.data.days;
        if (!days.length) return [];
        // Pad start so day 1 is on the correct weekday (0=Mon)
        const rows = [];
        let week = Array(days[0].weekday_num).fill(null);
        for (const day of days) {
            week.push(day);
            if (week.length === 7) {
                rows.push(week);
                week = [];
            }
        }
        if (week.length) {
            while (week.length < 7) week.push(null);
            rows.push(week);
        }
        return rows;
    }

    get filteredSiteSummary() {
        if (!this.state.data || !this.state.data.site_summary) return [];
        const term = (this.state.siteSearchTerm || "").toLowerCase().trim();
        if (!term) return this.state.data.site_summary;
        return this.state.data.site_summary.filter(s =>
            (s.name || "").toLowerCase().includes(term)
        );
    }

    dayClass(cell) {
        if (!cell || cell.scheduled === 0) return "ag-day-empty";
        if (cell.not_marked === cell.scheduled) return "ag-day-unmarked";
        if (cell.pct >= 90) return "ag-day-full";
        if (cell.pct >= 60) return "ag-day-partial";
        return "ag-day-low";
    }

    pctBar(pct) {
        if (pct === null || pct === undefined) return "";
        if (pct >= 90) return "ag-progress-fill-emerald";
        if (pct >= 60) return "ag-progress-fill-amber";
        return "ag-progress-fill-rose";
    }

    exportCsv() {
        const data = this.state.data;
        if (!data) return;
        const header = ["Date", "Weekday", "Scheduled", "Present", "Absent", "AWOL", "Late", "Not Marked", "Presence %"];
        const rows = data.days.map(d => [
            d.date, d.weekday, d.scheduled, d.present, d.absent, d.awol, d.late, d.not_marked,
            d.pct !== null ? d.pct + "%" : "—",
        ]);
        const csv = [header, ...rows].map(r => r.join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `attendance_${data.month_str}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }
}

registry.category("actions").add("security_attendance.attendance_summary_grid", AttendanceSummaryGrid);
