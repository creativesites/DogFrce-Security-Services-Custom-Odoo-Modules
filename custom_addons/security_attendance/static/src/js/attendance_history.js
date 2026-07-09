/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

// ─── Utilities ───────────────────────────────────────────────────────────────

function pad2(n) {
    return String(n).padStart(2, "0");
}

function floatToTime(h) {
    if (h == null || isNaN(h)) return "--:--";
    const hours = Math.floor(h);
    const mins = Math.round((h - hours) * 60);
    return `${pad2(hours)}:${pad2(mins)}`;
}

function datetimeToTime(dtStr) {
    if (!dtStr) return "--:--";
    // Odoo UTC datetime string: "2025-06-25 06:30:00"
    const dt = new Date(dtStr.replace(" ", "T") + "Z");
    if (isNaN(dt.getTime())) return "--:--";
    return `${pad2(dt.getHours())}:${pad2(dt.getMinutes())}`;
}

function buildInitials(name) {
    if (!name) return "?";
    return name
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map((w) => w[0].toUpperCase())
        .join("");
}

function formatDateLabel(dateStr) {
    if (!dateStr) return "";
    const [y, m, d] = dateStr.split("-").map(Number);
    const dt = new Date(y, m - 1, d);
    const days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
    const months = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ];
    return `${days[dt.getDay()]}, ${d} ${months[m - 1]} ${y}`;
}

function isoDateMinus(days) {
    const d = new Date();
    d.setDate(d.getDate() - days);
    return d.toISOString().slice(0, 10);
}

// ─── Component ───────────────────────────────────────────────────────────────

class AttendanceHistory extends Component {
    static props = { "*": true };
    static template = "security_attendance.AttendanceHistory";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            records: [],
            sites: [],
            empGrades: {},      // empId → grade label
            expandedId: null,
            // filters
            search: "",
            filterSite: "all",
            filterStatus: "all",
            filterDate: "30",   // "7" | "30" | "90" | "custom"
            dateFrom: isoDateMinus(30),
            dateTo: new Date().toISOString().slice(0, 10),
        });

        onWillStart(() => this._load());
    }

    // ─── Data loading ─────────────────────────────────────────────────────────

    async _load() {
        this.state.loading = true;
        const [records, sites] = await Promise.all([
            this.orm.searchRead(
                "security.attendance.record",
                [["shift_date", ">=", this.state.dateFrom],
                 ["shift_date", "<=", this.state.dateTo]],
                [
                    "id", "employee_id", "site_id", "post_id", "shift_template_id",
                    "shift_date", "check_in", "check_out",
                    "scheduled_start", "scheduled_end",
                    "status", "absence_type", "manual_presence",
                    "late_minutes", "early_departure_minutes",
                    "missing_check_out", "no_work_no_pay",
                    "overtime_hours", "overtime_approved",
                    "scheduled_hours", "worked_hours", "valid_hours",
                    "payable_hours", "unpaid_hours",
                    "normal_hours", "night_hours", "sunday_hours",
                    "public_holiday_hours", "saturday_hours",
                    "is_night_shift", "premium_category",
                    "note", "override_reason", "attendance_batch_id",
                ],
                { limit: 2000, order: "shift_date desc, id desc" }
            ),
            this.orm.searchRead(
                "security.client.site",
                [["active", "=", true]],
                ["id", "name"],
                { limit: 200 }
            ),
        ]);

        // Batch-fetch employee grades to avoid N+1
        const empIds = [...new Set(records.map((r) => r.employee_id?.[0]).filter(Boolean))];
        if (empIds.length) {
            try {
                const emps = await this.orm.searchRead(
                    "hr.employee",
                    [["id", "in", empIds]],
                    ["id", "job_title", "security_grade_id"],
                    { limit: empIds.length }
                );
                const grades = {};
                for (const e of emps) {
                    grades[e.id] = e.security_grade_id?.[1] || e.job_title || "";
                }
                this.state.empGrades = grades;
            } catch (_) {
                // grade field may not exist — ignore
            }
        }

        this.state.records = records;
        this.state.sites = sites;
        this.state.loading = false;
    }

    async reload() {
        await this._load();
    }

    // ─── Effective status (AWOL promotion) ───────────────────────────────────

    effStatus(r) {
        if (r.absence_type === "awol" || r.manual_presence === "awol") return "awol";
        return r.status || "scheduled";
    }

    // ─── KPI strip ────────────────────────────────────────────────────────────

    get kpi() {
        let present = 0, late = 0, absent = 0, awol = 0, incomplete = 0;
        for (const r of this.filteredRecords) {
            const s = this.effStatus(r);
            if (s === "awol")                        awol++;
            else if (s === "late")                   late++;
            else if (s === "present" || s === "early_leave") present++;
            else if (s === "absent")                 absent++;
            else if (s === "incomplete")             incomplete++;
        }
        return {
            total: this.filteredRecords.length,
            present,
            late,
            absent,
            awol,
            incomplete,
        };
    }

    // ─── Filtering ────────────────────────────────────────────────────────────

    get filteredRecords() {
        const { search, filterSite, filterStatus, records } = this.state;
        const q = search.toLowerCase().trim();
        return records.filter((r) => {
            if (filterSite !== "all" && String(r.site_id?.[0]) !== filterSite) return false;
            if (filterStatus !== "all" && this.effStatus(r) !== filterStatus) return false;
            if (q) {
                const name = (r.employee_id?.[1] || "").toLowerCase();
                const site = (r.site_id?.[1] || "").toLowerCase();
                const post = (r.post_id?.[1] || "").toLowerCase();
                const date = (r.shift_date || "").toLowerCase();
                if (!name.includes(q) && !site.includes(q) && !post.includes(q) && !date.includes(q)) {
                    return false;
                }
            }
            return true;
        });
    }

    get groupedByDate() {
        const groups = {};
        for (const r of this.filteredRecords) {
            const d = r.shift_date || "Unknown";
            if (!groups[d]) groups[d] = [];
            groups[d].push(r);
        }
        // Sort dates descending
        return Object.entries(groups).sort(([a], [b]) => b.localeCompare(a));
    }

    // ─── Date range ───────────────────────────────────────────────────────────

    onFilterDateChange(ev) {
        const val = ev.target.value;
        this.state.filterDate = val;
        if (val !== "custom") {
            const days = parseInt(val, 10) || 30;
            this.state.dateFrom = isoDateMinus(days);
            this.state.dateTo = new Date().toISOString().slice(0, 10);
            this._load();
        }
    }

    onDateFromChange(ev) {
        this.state.dateFrom = ev.target.value;
    }

    onDateToChange(ev) {
        this.state.dateTo = ev.target.value;
    }

    applyCustomRange() {
        this._load();
    }

    // ─── Event handlers ───────────────────────────────────────────────────────

    onSearchInput(ev) {
        this.state.search = ev.target.value;
    }

    onSiteChange(ev) {
        this.state.filterSite = ev.target.value;
    }

    onStatusChange(ev) {
        this.state.filterStatus = ev.target.value;
    }

    toggleExpand(id) {
        this.state.expandedId = this.state.expandedId === id ? null : id;
    }

    openRecord(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.attendance.record",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ─── Display helpers ─────────────────────────────────────────────────────

    statusLabel(r) {
        const map = {
            scheduled: "Scheduled",
            present: "Present",
            late: "Late",
            early_leave: "Early Leave",
            absent: "Absent",
            incomplete: "Incomplete",
            awol: "AWOL",
        };
        return map[this.effStatus(r)] || "Unknown";
    }

    statusClass(r) {
        return `ah-badge ah-badge-${this.effStatus(r)}`;
    }

    scheduledTimes(r) {
        const tmpl = r.shift_template_id;
        if (r.scheduled_start) {
            return `${datetimeToTime(r.scheduled_start)} – ${datetimeToTime(r.scheduled_end)}`;
        }
        return "--:-- – --:--";
    }

    actualTimes(r) {
        if (!r.check_in && !r.check_out) return null;
        const cin = datetimeToTime(r.check_in);
        const cout = r.check_out ? datetimeToTime(r.check_out) : "?";
        return `${cin} – ${cout}`;
    }

    fmtHrs(h) {
        if (!h || h < 0.01) return "0 h";
        const hh = Math.floor(h);
        const mm = Math.round((h - hh) * 60);
        return mm ? `${hh}h ${pad2(mm)}m` : `${hh}h`;
    }

    initials(r) {
        return buildInitials(r.employee_id?.[1]);
    }

    gradeFor(r) {
        return this.state.empGrades[r.employee_id?.[0]] || "";
    }

    dateLabel(dateStr) {
        return formatDateLabel(dateStr);
    }

    flagList(r) {
        const flags = [];
        if (r.is_night_shift)          flags.push({ icon: "fa-moon-o",   label: "Night" });
        if (r.is_public_holiday)       flags.push({ icon: "fa-star",     label: "PH" });
        if (r.sunday_hours > 0)        flags.push({ icon: "fa-calendar", label: "Sun" });
        if (r.saturday_hours > 0)      flags.push({ icon: "fa-calendar-o",label:"Sat" });
        if (r.overtime_hours > 0)      flags.push({ icon: "fa-clock-o",  label: "OT" });
        if (r.missing_check_out)       flags.push({ icon: "fa-exclamation-triangle", label: "MCO" });
        return flags;
    }

    hasHourBuckets(r) {
        return (
            (r.normal_hours || 0) + (r.night_hours || 0) + (r.sunday_hours || 0) +
            (r.public_holiday_hours || 0) + (r.saturday_hours || 0) > 0
        );
    }
}

registry.category("actions").add("security_attendance.attendance_history", AttendanceHistory);
