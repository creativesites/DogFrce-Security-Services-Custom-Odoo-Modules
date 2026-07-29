/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * WeeklyCheckIn — Ops-manager weekly review dashboard & operations check-in.
 *
 * Fully integrates Weekly Reviews (security.roster.week):
 *   - Mon–Sun week offset navigation (Previous, Today, Next)
 *   - Real-time slot fill rate, critical gaps, AWOL, missing check-ins
 *   - Weekly Review Manager: Notes input, Mark Reviewed, Confirm Week, Reset to Draft
 *   - Historical Weekly Reviews Log & Snapshot Table
 *   - Alert panel for active operational notifications
 */
class WeeklyCheckIn extends Component {
    static props = { "*": true };
    static template = "security_shift_planner.WeeklyCheckIn";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");

        this.state = useState({
            loading: true,
            saving: false,
            confirming: false,
            weekOffset: 0,
            weekStart: null,
            weekEnd: null,
            weekLabel: "",
            isCurrentWeek: true,
            stats: {
                totalSlots: 0,
                unassigned: 0,
                criticalGaps: 0,
                awolToday: 0,
                missingCheckins: 0,
                presentToday: 0,
            },
            alerts: [],
            weekRecord: null,
            weekState: "draft",
            reviewNotes: "",
            pastReviews: [],
        });

        onWillStart(async () => {
            this._setWeekBounds(0);
            await this.loadData();
        });
    }

    // ── Helpers ──────────────────────────────────────────────────────

    _setWeekBounds(offset = 0) {
        const today = new Date();
        const dayOfWeek = today.getDay(); // 0 = Sun … 6 = Sat
        const diffToMon = (dayOfWeek === 0 ? -6 : 1 - dayOfWeek) + offset * 7;
        const monday = new Date(today);
        monday.setDate(today.getDate() + diffToMon);
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);

        this.state.weekOffset = offset;
        this.state.isCurrentWeek = offset === 0;
        this.state.weekStart = this._fmtDate(monday);
        this.state.weekEnd = this._fmtDate(sunday);
        this.state.weekLabel =
            monday.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }) +
            " – " +
            sunday.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    }

    _fmtDate(d) {
        return (
            d.getFullYear() +
            "-" + String(d.getMonth() + 1).padStart(2, "0") +
            "-" + String(d.getDate()).padStart(2, "0")
        );
    }

    changeWeek(delta) {
        const newOffset = delta === 0 ? 0 : this.state.weekOffset + delta;
        this._setWeekBounds(newOffset);
        this.loadData();
    }

    selectWeekRecord(weekStartStr) {
        if (!weekStartStr) return;
        const targetMon = new Date(weekStartStr + "T00:00:00");
        const today = new Date();
        const dayOfWeek = today.getDay();
        const diffToMon = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        const currentMon = new Date(today);
        currentMon.setDate(today.getDate() + diffToMon);
        currentMon.setHours(0, 0, 0, 0);

        const diffTime = targetMon.getTime() - currentMon.getTime();
        const diffWeeks = Math.round(diffTime / (1000 * 3600 * 24 * 7));

        this._setWeekBounds(diffWeeks);
        this.loadData();
    }

    // ── Data ─────────────────────────────────────────────────────────

    async loadData() {
        this.state.loading = true;
        try {
            const today = this._fmtDate(new Date());
            const { weekStart, weekEnd } = this.state;

            const [slots, todayRecords, alerts, weekRecords, pastReviews] = await Promise.all([
                this.orm.searchRead(
                    "security.roster.slot",
                    [
                        ["shift_date", ">=", weekStart],
                        ["shift_date", "<=", weekEnd],
                        ["state", "not in", ["cancelled"]],
                    ],
                    ["id", "employee_id", "critical_gap"],
                    { limit: 2000 }
                ),
                this.orm.searchRead(
                    "security.attendance.record",
                    [
                        ["shift_date", ">=", weekStart],
                        ["shift_date", "<=", weekEnd],
                    ],
                    ["id", "manual_presence", "check_in", "scheduled_start", "shift_date"],
                    { limit: 2000 }
                ),
                this.orm.searchRead(
                    "security.notification",
                    [
                        ["notification_type", "in", ["awol_alert", "roster_gap", "override_audit"]],
                        ["state", "=", "unread"],
                    ],
                    ["id", "title", "body", "notification_type", "severity", "create_date"],
                    { order: "create_date desc", limit: 20 }
                ),
                this.orm.searchRead(
                    "security.roster.week",
                    [["week_start", "=", weekStart]],
                    ["id", "state", "gap_count_snap", "reviewer_id", "reviewed_at", "review_notes", "display_name"],
                    { limit: 1 }
                ),
                this.orm.searchRead(
                    "security.roster.week",
                    [],
                    ["id", "week_start", "week_end", "state", "gap_count_snap", "reviewer_id", "reviewed_at", "review_notes", "display_name"],
                    { order: "week_start desc", limit: 15 }
                ),
            ]);

            // Slot stats
            const totalSlots = slots.length;
            const unassigned = slots.filter((s) => !s.employee_id).length;
            const criticalGaps = slots.filter((s) => s.critical_gap && !s.employee_id).length;

            // Attendance stats
            const now = Date.now();
            const FIFTEEN_MIN_MS = 15 * 60 * 1000;
            let awolToday = 0, missingCheckins = 0, presentToday = 0;
            for (const r of todayRecords) {
                if (r.shift_date === today) {
                    if (r.manual_presence === "awol") { awolToday++; continue; }
                    if (r.manual_presence === "present") presentToday++;
                    if (!r.check_in && r.manual_presence !== "absent") {
                        if (r.scheduled_start) {
                            const schedMs = new Date(r.scheduled_start.replace(" ", "T") + "Z").getTime();
                            if (schedMs <= now - FIFTEEN_MIN_MS) missingCheckins++;
                        }
                    }
                }
            }

            this.state.stats = { totalSlots, unassigned, criticalGaps, awolToday, missingCheckins, presentToday };
            this.state.alerts = alerts;
            this.state.pastReviews = pastReviews;

            if (weekRecords.length) {
                const rec = weekRecords[0];
                this.state.weekRecord = rec;
                this.state.weekState = rec.state || "draft";
                this.state.reviewNotes = rec.review_notes || "";
            } else {
                this.state.weekRecord = null;
                this.state.weekState = "draft";
                this.state.reviewNotes = "";
            }
        } catch (err) {
            console.error("WeeklyCheckIn.loadData error:", err);
            this.notification.add("Failed to load operational weekly review data.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    // ── Weekly Review Actions ────────────────────────────────────────

    async _ensureWeekRecord() {
        if (this.state.weekRecord && this.state.weekRecord.id) {
            return this.state.weekRecord.id;
        }
        const ids = await this.orm.create("security.roster.week", [{
            week_start: this.state.weekStart,
            gap_count_snap: this.state.stats.criticalGaps,
            review_notes: this.state.reviewNotes,
        }]);
        const weekId = Array.isArray(ids) ? ids[0] : ids;
        this.state.weekRecord = { id: weekId, state: "draft", review_notes: this.state.reviewNotes };
        return weekId;
    }

    async saveNotes() {
        this.state.saving = true;
        try {
            const weekId = await this._ensureWeekRecord();
            await this.orm.write("security.roster.week", [weekId], {
                review_notes: this.state.reviewNotes,
            });
            this.notification.add("Weekly review notes saved.", { type: "info" });
            await this.loadData();
        } catch (err) {
            this.notification.add("Could not save notes: " + (err.message || String(err)), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async markAsReviewed() {
        this.state.saving = true;
        try {
            const weekId = await this._ensureWeekRecord();
            await this.orm.call("security.roster.week", "action_review", [[weekId], this.state.reviewNotes]);
            this.state.weekState = "reviewed";
            this.notification.add("Week marked as Reviewed.", { type: "success" });
            await this.loadData();
        } catch (err) {
            this.notification.add("Could not mark as reviewed: " + (err.message || String(err)), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async confirmWeek() {
        this.state.confirming = true;
        try {
            const weekId = await this._ensureWeekRecord();
            await this.orm.call("security.roster.week", "action_confirm_week", [[weekId], this.state.reviewNotes]);
            this.state.weekState = "confirmed";
            this.notification.add("Weekly Operations Review Confirmed!", { type: "success" });
            await this.loadData();
        } catch (err) {
            this.notification.add("Could not confirm week: " + (err.message || String(err)), { type: "danger" });
        } finally {
            this.state.confirming = false;
        }
    }

    async resetToDraft() {
        if (!this.state.weekRecord) return;
        this.state.saving = true;
        try {
            await this.orm.call("security.roster.week", "action_reset_to_draft", [[this.state.weekRecord.id]]);
            this.state.weekState = "draft";
            this.notification.add("Week review reset to Draft.", { type: "warning" });
            await this.loadData();
        } catch (err) {
            this.notification.add("Could not reset week: " + (err.message || String(err)), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    async dismissAlert(alertId) {
        await this.orm.call("security.notification", "action_dismiss", [[alertId]]);
        this.state.alerts = this.state.alerts.filter((a) => a.id !== alertId);
    }

    openRosterBoard() {
        this.action.doAction("security_shift_planner.action_roster_board");
    }

    openRosteringHub() {
        this.action.doAction("security_shift_planner.action_rostering_hub");
    }

    // ── Computed getters ─────────────────────────────────────────────

    get hasAlerts() {
        return this.state.alerts.length > 0;
    }

    get hasCriticalAlerts() {
        return this.state.alerts.some((a) => a.severity === "critical");
    }

    get fillRatePct() {
        const { totalSlots, unassigned } = this.state.stats;
        if (!totalSlots) return 0;
        return Math.round(((totalSlots - unassigned) / totalSlots) * 100);
    }
}

registry.category("actions").add("security_shift_planner.weekly_checkin", WeeklyCheckIn);
