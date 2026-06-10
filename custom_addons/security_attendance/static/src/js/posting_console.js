/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * Tier-3 OWL client action: Attendance Posting Console
 *
 * Dark-themed card-grid interface where supervisors mark all guards
 * present / absent / AWOL for a site in one screen, with stats strip,
 * filter pills, and a single Save All commit.
 */
class AttendancePostingConsole extends Component {
    static props = { "*": true };
    static template = "security_attendance.PostingConsole";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        const today = new Date().toISOString().slice(0, 10);
        const ctx = this.props.action?.context || {};

        this.state = useState({
            loading: true,
            sites: [],
            selectedSiteId: ctx.default_site_id || null,
            date: ctx.default_date || today,
            batchId: ctx.default_batch_id || null,
            batchState: null,
            batchName: null,
            records: [],
            dirtyIds: new Set(),
            saving: false,
            filter: "all", // "all" | "not_marked" | "present" | "absent" | "awol"
        });

        onWillStart(async () => {
            await this.loadSites();
            if (this.state.date && this.state.selectedSiteId) {
                if (this.state.batchId) {
                    await this._loadBatchMeta(this.state.batchId);
                    await this.loadRecords();
                } else {
                    await this.loadBatch();
                }
            }
            this.state.loading = false;
        });
    }

    // ─── Data loaders ────────────────────────────────────────────────────────

    async loadSites() {
        const sites = await this.orm.searchRead(
            "security.client.site",
            [["active", "=", true]],
            ["id", "name"],
            { order: "name" }
        );
        this.state.sites = sites;
    }

    async loadBatch() {
        if (!this.state.date || !this.state.selectedSiteId) return;
        this.state.loading = true;
        try {
            const batches = await this.orm.searchRead(
                "security.attendance.batch",
                [
                    ["attendance_date", "=", this.state.date],
                    ["site_id", "=", this.state.selectedSiteId],
                    ["state", "!=", "cancelled"],
                ],
                ["id", "state", "name"],
                { limit: 1, order: "id desc" }
            );
            if (batches.length) {
                this.state.batchId = batches[0].id;
                this.state.batchState = batches[0].state;
                this.state.batchName = batches[0].name;
                await this.loadRecords();
            } else {
                this.state.batchId = null;
                this.state.batchState = null;
                this.state.batchName = null;
                this.state.records = [];
                this.state.dirtyIds = new Set();
            }
        } finally {
            this.state.loading = false;
        }
    }

    async _loadBatchMeta(batchId) {
        const batches = await this.orm.searchRead(
            "security.attendance.batch",
            [["id", "=", batchId]],
            ["id", "state", "name"],
            { limit: 1 }
        );
        if (batches.length) {
            this.state.batchState = batches[0].state;
            this.state.batchName = batches[0].name;
        }
    }

    async loadRecords() {
        if (!this.state.batchId) return;
        const records = await this.orm.searchRead(
            "security.attendance.record",
            [["attendance_batch_id", "=", this.state.batchId]],
            [
                "id",
                "employee_id",
                "post_id",
                "shift_template_id",
                "manual_presence",
                "check_in",
                "check_out",
                "worked_hours",
                "late_minutes",
                "early_departure_minutes",
                "status",
                "override_reason",
            ],
            { order: "employee_id" }
        );
        this.state.records = records.map((r) => ({ ...r }));
        this.state.dirtyIds = new Set();
    }

    async refreshRecords() {
        this.state.loading = true;
        await this.loadRecords();
        this.state.loading = false;
    }

    // ─── UI event handlers ───────────────────────────────────────────────────

    onDateChange(ev) {
        this.state.date = ev.target.value;
        this.state.batchId = null;
        this.state.batchState = null;
        this.state.batchName = null;
        this.state.records = [];
        this.state.dirtyIds = new Set();
        if (this.state.selectedSiteId) {
            this.loadBatch();
        }
    }

    onSiteChange(ev) {
        const val = ev.target.value;
        this.state.selectedSiteId = val ? parseInt(val) : null;
        this.state.batchId = null;
        this.state.batchState = null;
        this.state.batchName = null;
        this.state.records = [];
        this.state.dirtyIds = new Set();
        if (this.state.selectedSiteId) {
            this.loadBatch();
        }
    }

    setFilter(value) {
        this.state.filter = value;
    }

    setPresence(rec, value) {
        rec.manual_presence = value;
        if (value === "absent" || value === "awol") {
            rec.check_in = false;
            rec.check_out = false;
        }
        this.state.dirtyIds.add(rec.id);
    }

    onCheckInChange(rec, ev) {
        const val = ev.target.value; // "HH:MM" from time input
        rec.check_in = val ? this._timeToDatetime(val) : false;
        this.state.dirtyIds.add(rec.id);
    }

    onCheckOutChange(rec, ev) {
        const val = ev.target.value;
        rec.check_out = val ? this._timeToDatetime(val) : false;
        this.state.dirtyIds.add(rec.id);
    }

    markAllPresent() {
        for (const rec of this.state.records) {
            if (rec.manual_presence !== "present") {
                rec.manual_presence = "present";
                this.state.dirtyIds.add(rec.id);
            }
        }
    }

    // ─── Computed getters ────────────────────────────────────────────────────

    get visibleRecords() {
        const f = this.state.filter;
        if (f === "all") return this.state.records;
        return this.state.records.filter((r) => r.manual_presence === f);
    }

    get stats() {
        const records = this.state.records;
        return {
            total: records.length,
            present: records.filter((r) => r.manual_presence === "present").length,
            absent: records.filter((r) => r.manual_presence === "absent").length,
            awol: records.filter((r) => r.manual_presence === "awol").length,
            notMarked: records.filter((r) => r.manual_presence === "not_marked").length,
            lateCount: records.filter((r) => (r.late_minutes || 0) > 0).length,
        };
    }

    get allMarked() {
        return (
            this.state.records.length > 0 &&
            this.state.records.every((r) => r.manual_presence !== "not_marked")
        );
    }

    get canSubmit() {
        return (
            this.state.batchState === "draft" &&
            this.allMarked &&
            this.state.dirtyIds.size === 0
        );
    }

    // ─── Actions ─────────────────────────────────────────────────────────────

    async saveAll() {
        if (this.state.dirtyIds.size === 0) {
            this.notification.add("No changes to save.", { type: "info" });
            return;
        }
        const dirty = this.state.records.filter((r) => this.state.dirtyIds.has(r.id));
        this.state.saving = true;
        try {
            await this.orm.call(
                "security.attendance.batch",
                "action_bulk_mark_attendance",
                [
                    [this.state.batchId],
                    dirty.map((r) => ({
                        record_id: r.id,
                        manual_presence: r.manual_presence,
                        check_in: r.check_in ? this._toIsoString(r.check_in) : false,
                        check_out: r.check_out ? this._toIsoString(r.check_out) : false,
                    })),
                ]
            );
            this.state.dirtyIds = new Set();
            this.notification.add(
                `${dirty.length} attendance record(s) saved successfully.`,
                { type: "success", title: "Saved" }
            );
            // Reload to get recomputed worked_hours / late_minutes / status
            await this.loadRecords();
            await this._loadBatchMeta(this.state.batchId);
        } catch (e) {
            this.notification.add("Save failed: " + (e.message || String(e)), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async createBatch() {
        if (!this.state.date || !this.state.selectedSiteId) return;
        this.state.loading = true;
        try {
            const batchId = await this.orm.create("security.attendance.batch", [
                {
                    attendance_date: this.state.date,
                    site_id: this.state.selectedSiteId,
                },
            ]);
            this.state.batchId = Array.isArray(batchId) ? batchId[0] : batchId;
            await this._loadBatchMeta(this.state.batchId);
            await this.generateFromRoster();
        } catch (e) {
            this.notification.add("Could not create batch: " + (e.message || String(e)), {
                type: "danger",
            });
            this.state.loading = false;
        }
    }

    async generateFromRoster() {
        if (!this.state.batchId) return;
        this.state.loading = true;
        try {
            const result = await this.orm.call(
                "security.attendance.batch",
                "action_generate_from_roster",
                [[this.state.batchId]]
            );
            // Python returns a display_notification dict with params
            if (result && result.params) {
                this.notification.add(result.params.message, {
                    title: result.params.title,
                    type: result.params.type || "info",
                });
            }
            await this.loadRecords();
            await this._loadBatchMeta(this.state.batchId);
        } catch (e) {
            this.notification.add(e.message || "Failed to generate from roster.", {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async submitBatch() {
        if (!this.state.batchId) return;
        this.state.loading = true;
        try {
            await this.orm.call(
                "security.attendance.batch",
                "action_review",
                [[this.state.batchId]]
            );
            await this._loadBatchMeta(this.state.batchId);
            this.notification.add("Posting sheet submitted for review.", {
                title: "Submitted",
                type: "success",
            });
        } catch (e) {
            this.notification.add("Submit failed: " + (e.message || String(e)), { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    // ─── Card helpers ────────────────────────────────────────────────────────

    getCardClass(rec) {
        const isDirty = this.state.dirtyIds.has(rec.id);
        const presenceClass = {
            present: "pc-card-present",
            absent: "pc-card-absent",
            awol: "pc-card-awol",
            not_marked: "pc-card-unmarked",
        }[rec.manual_presence] || "pc-card-unmarked";
        return presenceClass + (isDirty ? " pc-card-dirty" : "");
    }

    getStatusClass(rec) {
        const map = {
            present: "pc-badge-present",
            late: "pc-badge-late",
            early_leave: "pc-badge-early",
            absent: "pc-badge-absent",
            incomplete: "pc-badge-incomplete",
            scheduled: "pc-badge-scheduled",
        };
        return map[rec.status] || "pc-badge-scheduled";
    }

    getStatusLabel(rec) {
        const map = {
            present: "Present",
            late: "Late",
            early_leave: "Early Leave",
            absent: "Absent",
            incomplete: "Incomplete",
            scheduled: "Scheduled",
        };
        return map[rec.status] || rec.status || "—";
    }

    getAvatarColor(rec) {
        // Deterministic colour from employee id
        const colors = [
            "#0ea5e9", "#8b5cf6", "#ec4899", "#f97316",
            "#14b8a6", "#84cc16", "#f59e0b", "#6366f1",
        ];
        return colors[(rec.id || 0) % colors.length];
    }

    getPresenceLabelClass(rec) {
        const map = {
            not_marked: "pc-presence-label-unmarked",
            present: "pc-presence-label-present",
            absent: "pc-presence-label-absent",
            awol: "pc-presence-label-awol",
        };
        return map[rec.manual_presence] || "pc-presence-label-unmarked";
    }

    // ─── Helpers ─────────────────────────────────────────────────────────────

    /** Convert Odoo datetime string "YYYY-MM-DD HH:MM:SS" → "HH:MM" for time input. */
    toTimeInput(odooDatetime) {
        if (!odooDatetime) return "";
        return String(odooDatetime).replace(" ", "T").slice(11, 16);
    }

    /** Build an Odoo-compatible datetime string from a time input value "HH:MM". */
    _timeToDatetime(timeStr) {
        if (!timeStr || !this.state.date) return false;
        return `${this.state.date} ${timeStr}:00`;
    }

    /** Ensure value is an ISO-style string Odoo can parse. */
    _toIsoString(val) {
        if (!val) return false;
        if (typeof val === "string") return val.replace("T", " ").slice(0, 19);
        if (val instanceof Date) return val.toISOString().replace("T", " ").slice(0, 19);
        return String(val);
    }

    getBatchStateLabel(state) {
        const map = {
            draft: "Draft",
            captured: "Captured",
            reviewed: "Reviewed",
            locked: "Locked",
            cancelled: "Cancelled",
        };
        return map[state] || state || "—";
    }

    getBatchStateBadgeStyle(state) {
        const map = {
            draft: "background:#334155;color:#94a3b8;",
            captured: "background:#1e40af;color:#bfdbfe;",
            reviewed: "background:#065f46;color:#6ee7b7;",
            locked: "background:#4c1d95;color:#ddd6fe;",
            cancelled: "background:#7f1d1d;color:#fca5a5;",
        };
        return map[state] || "background:#334155;color:#94a3b8;";
    }
}

registry.category("actions").add(
    "security_attendance.posting_console",
    AttendancePostingConsole
);
