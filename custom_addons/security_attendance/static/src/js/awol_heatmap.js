/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Tier-3 OWL client action: AWOL / Absence Heatmap
 *
 * Renders a 30-day colour-coded attendance grid for all active security guards.
 * Green = present/late/early_leave, Amber = absent (authorised/no-show),
 * Red = AWOL, Grey = no scheduled shift recorded.
 */
class AWOLHeatmap extends Component {
    static props = { "*": true };
    static template = "security_attendance.AWOLHeatmap";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            days: [],       // array of date strings "YYYY-MM-DD" for last 30 days
            guards: [],     // [{id, name}]
            cells: {},      // key: "guardId_date" → {status, absence_type, record_id}
            filterSiteId: null,
            sites: [],
        });

        onWillStart(async () => {
            await this._loadAll();
            this.state.loading = false;
        });
    }

    // -------------------------------------------------------------------------
    // Data loading
    // -------------------------------------------------------------------------

    _toDateString(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, "0");
        const d = String(date.getDate()).padStart(2, "0");
        return `${y}-${m}-${d}`;
    }

    async _loadAll() {
        // 1. Generate last 30 days (29 days ago → today)
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const days = [];
        for (let i = 29; i >= 0; i--) {
            const d = new Date(today);
            d.setDate(today.getDate() - i);
            days.push(this._toDateString(d));
        }
        this.state.days = days;

        const thirtyDaysAgo = days[0];
        const todayStr = days[days.length - 1];

        // 2. Load active security guards
        const guards = await this.orm.searchRead(
            "hr.employee",
            [["security_guard", "=", true], ["active", "=", true]],
            ["id", "name"],
            { order: "name" }
        );
        this.state.guards = guards;

        // 3. Load attendance records for the date range
        const records = await this.orm.searchRead(
            "security.attendance.record",
            [
                ["shift_date", ">=", thirtyDaysAgo],
                ["shift_date", "<=", todayStr],
            ],
            ["employee_id", "shift_date", "status", "absence_type", "id"],
            { order: "shift_date" }
        );

        // 4. Load active sites
        const sites = await this.orm.searchRead(
            "security.client.site",
            [["active", "=", true]],
            ["id", "name"],
            { order: "name" }
        );
        this.state.sites = sites;

        // 5. Build cells map
        const cells = {};
        for (const rec of records) {
            const employeeId = Array.isArray(rec.employee_id) ? rec.employee_id[0] : rec.employee_id;
            if (!employeeId) continue;
            const dateStr = rec.shift_date;
            const key = `${employeeId}_${dateStr}`;
            cells[key] = {
                status: rec.status,
                absence_type: rec.absence_type,
                record_id: rec.id,
            };
        }
        this.state.cells = cells;
    }

    // -------------------------------------------------------------------------
    // Cell helpers
    // -------------------------------------------------------------------------

    getCellColor(guardId, date) {
        const cell = this.state.cells[`${guardId}_${date}`];
        if (!cell) {
            return "#e2e8f0"; // light grey — no scheduled shift
        }
        if (cell.absence_type === "awol") {
            return "#dc2626"; // red — AWOL
        }
        if (cell.status === "absent") {
            return "#d97706"; // amber — absent (authorised / no-show)
        }
        if (
            cell.status === "present" ||
            cell.status === "late" ||
            cell.status === "early_leave"
        ) {
            return "#16a34a"; // green — present / on time / late / early leave
        }
        return "#e2e8f0"; // fallback grey
    }

    getCellTooltip(guardId, date) {
        const cell = this.state.cells[`${guardId}_${date}`];
        if (!cell) {
            return `${date}: No record`;
        }
        const statusLabel = {
            scheduled: "Scheduled",
            present: "Present",
            late: "Late",
            early_leave: "Early Leave",
            absent: "Absent",
            incomplete: "Incomplete",
        }[cell.status] || cell.status;
        const absenceLabel = cell.absence_type && cell.absence_type !== "none"
            ? ` (${cell.absence_type === "awol" ? "AWOL" : cell.absence_type === "authorised" ? "Authorised" : cell.absence_type === "no_show" ? "No Show" : cell.absence_type})`
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

    setFilterSite(siteId) {
        this.state.filterSiteId = siteId || null;
    }

    // -------------------------------------------------------------------------
    // Computed / getters
    // -------------------------------------------------------------------------

    get visibleGuards() {
        if (!this.state.filterSiteId) {
            return this.state.guards;
        }
        // Filter by site: guards whose any cell in the range belongs to the site.
        // Since guards don't carry site info directly from hr.employee here,
        // we fall back to showing all guards when a site filter is active unless
        // the guard list was enriched with site data. For now this is a no-op
        // placeholder that can be wired once site_ids is added to the guard query.
        return this.state.guards;
    }

    get dateHeaders() {
        const MONTH_LABELS = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ];
        return this.state.days.map((dateStr) => {
            const [, monthStr, dayStr] = dateStr.split("-");
            const month = MONTH_LABELS[parseInt(monthStr, 10) - 1];
            return { date: dateStr, label: `${month} ${dayStr}` };
        });
    }

    countByStatus(status) {
        const todayStr = this.state.days[this.state.days.length - 1];
        let count = 0;
        for (const guard of this.visibleGuards) {
            const cell = this.state.cells[`${guard.id}_${todayStr}`];
            if (!cell) continue;
            if (status === "awol" && cell.absence_type === "awol") {
                count++;
            } else if (status === "absent" && cell.status === "absent" && cell.absence_type !== "awol") {
                count++;
            } else if (
                status === "present" &&
                (cell.status === "present" || cell.status === "late" || cell.status === "early_leave")
            ) {
                count++;
            }
        }
        return count;
    }
}

registry.category("actions").add("security_attendance.awol_heatmap", AWOLHeatmap);
