/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

/**
 * WeeklyCheckIn — Ops-manager weekly review dashboard.
 *
 * Shows a summary of the current Mon–Sun week:
 *   - Slot fill rate, critical gaps, AWOL today, missing check-ins
 *   - Alert panel for unread awol_alert / roster_gap notifications
 *   - "Confirm Week" button → creates/confirms a security.roster.week record
 */
class WeeklyCheckIn extends Component {
    static props = { "*": true };
    static template = "security_shift_planner.WeeklyCheckIn";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            confirming: false,
            weekStart: null,
            weekEnd: null,
            weekLabel: "",
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
        });

        onWillStart(async () => {
            this._setWeekBounds();
            await this.loadData();
        });
    }

    // ── Helpers ──────────────────────────────────────────────────────

    _setWeekBounds() {
        const today = new Date();
        const dayOfWeek = today.getDay(); // 0 = Sun … 6 = Sat
        const diffToMon = dayOfWeek === 0 ? -6 : 1 - dayOfWeek;
        const monday = new Date(today);
        monday.setDate(today.getDate() + diffToMon);
        const sunday = new Date(monday);
        sunday.setDate(monday.getDate() + 6);

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

    // ── Data ─────────────────────────────────────────────────────────

    async loadData() {
        this.state.loading = true;
        try {
            const today = this._fmtDate(new Date());
            const { weekStart, weekEnd } = this.state;

            const [slots, todayRecords, alerts, weekRecords] = await Promise.all([
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
                    [["shift_date", "=", today]],
                    ["id", "manual_presence", "check_in", "scheduled_start"],
                    { limit: 1000 }
                ),
                this.orm.searchRead(
                    "security.notification",
                    [
                        ["notification_type", "in", ["awol_alert", "roster_gap"]],
                        ["state", "=", "unread"],
                    ],
                    ["id", "title", "body", "notification_type", "severity", "create_date"],
                    { order: "create_date desc", limit: 20 }
                ),
                this.orm.searchRead(
                    "security.roster.week",
                    [["week_start", "=", weekStart]],
                    ["id", "state", "gap_count_snap", "reviewer_id"],
                    { limit: 1 }
                ),
            ]);

            // Slot stats
            const totalSlots = slots.length;
            const unassigned = slots.filter((s) => !s.employee_id).length;
            const criticalGaps = slots.filter((s) => s.critical_gap && !s.employee_id).length;

            // Today's attendance stats
            const now = Date.now();
            const FIFTEEN_MIN_MS = 15 * 60 * 1000;
            let awolToday = 0, missingCheckins = 0, presentToday = 0;
            for (const r of todayRecords) {
                if (r.manual_presence === "awol") { awolToday++; continue; }
                if (r.manual_presence === "present") presentToday++;
                if (!r.check_in && r.manual_presence !== "absent") {
                    if (r.scheduled_start) {
                        const schedMs = new Date(r.scheduled_start.replace(" ", "T") + "Z").getTime();
                        if (schedMs <= now - FIFTEEN_MIN_MS) missingCheckins++;
                    }
                }
            }

            this.state.stats = { totalSlots, unassigned, criticalGaps, awolToday, missingCheckins, presentToday };
            this.state.alerts = alerts;
            if (weekRecords.length) {
                this.state.weekRecord = weekRecords[0];
                this.state.weekState = weekRecords[0].state;
            } else {
                this.state.weekRecord = null;
                this.state.weekState = "draft";
            }
        } catch (err) {
            console.error("WeeklyCheckIn.loadData error:", err);
            this.notification.add("Failed to load operational data.", { type: "danger" });
        } finally {
            this.state.loading = false;
        }
    }

    // ── Actions ──────────────────────────────────────────────────────

    async confirmWeek() {
        this.state.confirming = true;
        try {
            let weekId;
            if (this.state.weekRecord) {
                weekId = this.state.weekRecord.id;
            } else {
                const ids = await this.orm.create("security.roster.week", [{
                    week_start: this.state.weekStart,
                    gap_count_snap: this.state.stats.criticalGaps,
                }]);
                weekId = ids[0] !== undefined ? ids[0] : ids;
                this.state.weekRecord = { id: weekId };
            }
            await this.orm.call("security.roster.week", "action_confirm_week", [[weekId]]);
            this.state.weekState = "confirmed";
            this.notification.add("Week confirmed successfully.", { type: "success" });
        } catch (err) {
            this.notification.add(
                "Could not confirm week: " + (err.message || String(err)),
                { type: "danger" }
            );
        } finally {
            this.state.confirming = false;
        }
    }

    async dismissAlert(alertId) {
        await this.orm.call("security.notification", "action_dismiss", [[alertId]]);
        this.state.alerts = this.state.alerts.filter((a) => a.id !== alertId);
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
