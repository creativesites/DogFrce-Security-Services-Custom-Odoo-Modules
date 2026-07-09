/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

class AWOLHeatmap extends Component {
    static props = { "*": true };
    static template = "security_attendance.AWOLHeatmap";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            days: [],
            guards: [],
            cells: {},      // key: "guardId_date" → {status, absence_type, record_id, site_id}
            guardSiteIds: {}, // key: guardId → Set of siteIds seen in range
            filterSiteId: null,
            guardSearch: "",
            sites: [],
            dayRange: 30,   // 7 | 14 | 30 | 60
        });

        onWillStart(async () => {
            await this._loadAll();
            this.state.loading = false;
        });
    }

    // ─── Data loading ────────────────────────────────────────────────────────

    _toDateString(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const d = String(date.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    }

    _buildDays(numDays) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const days = [];
        for (let i = numDays - 1; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            days.push(this._toDateString(d));
        }
        return days;
    }

    async _loadAll() {
        const days = this._buildDays(this.state.dayRange);
        this.state.days = days;
        const fromDate = days[0];
        const toDate = days[days.length - 1];

        const [guards, records, sites] = await Promise.all([
            this.orm.searchRead(
                "hr.employee",
                [["security_guard", "=", true], ["active", "=", true]],
                ["id", "name"],
                { order: "name" }
            ),
            this.orm.searchRead(
                "security.attendance.record",
                [["shift_date", ">=", fromDate], ["shift_date", "<=", toDate]],
                ["employee_id", "shift_date", "status", "absence_type", "id", "site_id"],
                { order: "shift_date" }
            ),
            this.orm.searchRead(
                "security.client.site",
                [["active", "=", true]],
                ["id", "name"],
                { order: "name" }
            ),
        ]);

        this.state.guards = guards;
        this.state.sites = sites;

        const cells = {};
        const guardSiteIds = {};
        for (const rec of records) {
            const eid = Array.isArray(rec.employee_id) ? rec.employee_id[0] : rec.employee_id;
            if (!eid) continue;
            const key = `${eid}_${rec.shift_date}`;
            const siteId = Array.isArray(rec.site_id) ? rec.site_id[0] : (rec.site_id || null);
            cells[key] = {
                status: rec.status,
                absence_type: rec.absence_type,
                record_id: rec.id,
                site_id: siteId,
            };
            if (siteId) {
                if (!guardSiteIds[eid]) guardSiteIds[eid] = new Set();
                guardSiteIds[eid].add(siteId);
            }
        }
        this.state.cells = cells;
        this.state.guardSiteIds = guardSiteIds;
    }

    // ─── Cell helpers ─────────────────────────────────────────────────────────

    getCellColor(guardId, date) {
        const cell = this.state.cells[`${guardId}_${date}`];
        if (!cell) return "#e2e8f0";
        if (cell.absence_type === "awol") return "#dc2626";
        if (cell.status === "absent") return "#d97706";
        if (["present", "late", "early_leave"].includes(cell.status)) return "#16a34a";
        return "#e2e8f0";
    }

    getCellTooltip(guardId, date) {
        const cell = this.state.cells[`${guardId}_${date}`];
        if (!cell) return `${date}: No record`;
        const statusLabel = {
            scheduled: "Scheduled", present: "Present", late: "Late",
            early_leave: "Early Leave", absent: "Absent", incomplete: "Incomplete",
        }[cell.status] || cell.status;
        const absenceLabel = cell.absence_type && cell.absence_type !== "none"
            ? ` (${cell.absence_type === "awol" ? "AWOL" : cell.absence_type === "authorised" ? "Authorised" : "No Show"})`
            : "";
        return `${date}: ${statusLabel}${absenceLabel}`;
    }

    openRecord(guardId, date) {
        const cell = this.state.cells[`${guardId}_${date}`];
        if (!cell || !cell.record_id) return;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.attendance.record",
            res_id: cell.record_id,
            views: [[false, "form"]],
            target: "new",
        });
    }

    onFilterSiteChange(ev) {
        this.state.filterSiteId = parseInt(ev.target.value) || null;
    }

    onGuardSearchInput(ev) {
        this.state.guardSearch = ev.target.value.toLowerCase();
    }

    async setDayRange(numDays) {
        this.state.dayRange = numDays;
        this.state.loading = true;
        await this._loadAll();
        this.state.loading = false;
    }

    exportCsv() {
        const guards = this.visibleGuards;
        const days = this.state.days;
        const rows = [["Guard", ...days]];
        for (const g of guards) {
            const row = [g.name];
            for (const d of days) {
                const cell = this.state.cells[`${g.id}_${d}`];
                if (!cell) row.push("");
                else if (cell.absence_type === "awol") row.push("AWOL");
                else if (cell.status === "absent") row.push("Absent");
                else if (["present", "late", "early_leave"].includes(cell.status)) row.push("Present");
                else row.push("Scheduled");
            }
            rows.push(row);
        }
        const csv = rows.map(r => r.map(v => `"${v}"`).join(",")).join("\n");
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `attendance_heatmap_${days[0]}_to_${days[days.length - 1]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // ─── Computed getters ─────────────────────────────────────────────────────

    get visibleGuards() {
        let guards = this.state.guards;

        // Site filter — keep guards who appeared at the selected site in the date range
        if (this.state.filterSiteId) {
            guards = guards.filter(g => {
                const siteSet = this.state.guardSiteIds[g.id];
                return siteSet && siteSet.has(this.state.filterSiteId);
            });
        }

        // Name search
        if (this.state.guardSearch) {
            guards = guards.filter(g => g.name.toLowerCase().includes(this.state.guardSearch));
        }

        return guards;
    }

    get dateHeaders() {
        const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
        return this.state.days.map(dateStr => {
            const [, mm, dd] = dateStr.split("-");
            return { date: dateStr, label: `${MONTHS[parseInt(mm) - 1]} ${parseInt(dd)}` };
        });
    }

    countByStatus(status) {
        const todayStr = this.state.days[this.state.days.length - 1];
        let count = 0;
        for (const g of this.visibleGuards) {
            const cell = this.state.cells[`${g.id}_${todayStr}`];
            if (!cell) continue;
            if (status === "awol" && cell.absence_type === "awol") count++;
            else if (status === "absent" && cell.status === "absent" && cell.absence_type !== "awol") count++;
            else if (status === "present" && ["present","late","early_leave"].includes(cell.status)) count++;
        }
        return count;
    }

    // Summary row: per-day attendance % across visible guards
    getDaySummary(date) {
        const guards = this.visibleGuards;
        if (!guards.length) return { pct: 0, color: "#e2e8f0" };
        let present = 0;
        let scheduled = 0;
        for (const g of guards) {
            const cell = this.state.cells[`${g.id}_${date}`];
            if (!cell) continue;
            scheduled++;
            if (["present","late","early_leave"].includes(cell.status)) present++;
        }
        if (!scheduled) return { pct: null, color: "#f8f9fa" };
        const pct = Math.round((present / scheduled) * 100);
        const color = pct >= 90 ? "#16a34a" : pct >= 80 ? "#d97706" : "#dc2626";
        return { pct, color };
    }
}

registry.category("actions").add("security_attendance.awol_heatmap", AWOLHeatmap);
