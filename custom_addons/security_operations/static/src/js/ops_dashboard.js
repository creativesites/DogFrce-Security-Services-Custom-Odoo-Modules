/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const DAY_NAMES = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTH_NAMES = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
];

class OpsDashboard extends Component {
    static template = "security_operations.OpsDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        const now = new Date();
        const pad = n => String(n).padStart(2, "0");
        this._today = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
        this._todayLabel = `${DAY_NAMES[now.getDay()]} ${now.getDate()} ${MONTH_NAMES[now.getMonth()]} ${now.getFullYear()}`;

        this.state = useState({
            loading: true,
            todayLabel: this._todayLabel,
            kpi: {
                scheduled: 0,
                present: 0,
                late: 0,
                awol: 0,
                criticalGaps: 0,
                fillRate: 0,
            },
            alertSites: [],
            awolAlerts: [],
            activeBatchId: null,
            activeBatchName: null,
            filling: false,
        });

        onWillStart(() => this._load());
    }

    async _load() {
        await Promise.all([
            this._loadKpi(),
            this._loadAwolAlerts(),
            this._loadAlertSites(),
        ]);
        this.state.loading = false;
    }

    async _loadKpi() {
        // Today's attendance records
        const records = await this.orm.searchRead(
            "security.attendance.record",
            [["shift_date", "=", this._today]],
            ["status", "absence_type"],
            { limit: 2000 },
        );

        let present = 0, late = 0, awol = 0;
        for (const r of records) {
            if (r.status === "present") present++;
            else if (r.status === "late") { present++; late++; }
            else if (r.absence_type === "awol") awol++;
        }
        this.state.kpi.scheduled = records.length;
        this.state.kpi.present = present;
        this.state.kpi.late = late;
        this.state.kpi.awol = awol;

        // Active batch KPIs
        const batches = await this.orm.searchRead(
            "security.roster.batch",
            [["state", "in", ["generated", "confirmed", "submitted", "approved"]]],
            ["id", "name", "fill_rate", "unassigned_count", "critical_gap_count"],
            { limit: 1, order: "date_from desc" },
        );
        if (batches[0]) {
            this.state.kpi.fillRate = batches[0].fill_rate;
            this.state.kpi.criticalGaps = batches[0].critical_gap_count;
            this.state.activeBatchId = batches[0].id;
            this.state.activeBatchName = batches[0].name;
        }
    }

    async _loadAwolAlerts() {
        const records = await this.orm.searchRead(
            "security.attendance.record",
            [
                ["shift_date", "=", this._today],
                ["absence_type", "=", "awol"],
            ],
            ["employee_id", "site_id", "post_id", "shift_template_id", "roster_slot_id"],
            { limit: 8 },
        );
        this.state.awolAlerts = records;
    }

    async _loadAlertSites() {
        const batches = await this.orm.searchRead(
            "security.roster.batch",
            [
                ["state", "in", ["generated", "confirmed", "submitted", "approved"]],
                ["critical_gap_count", ">", 0],
            ],
            ["site_id", "fill_rate", "critical_gap_count", "unassigned_count"],
            { limit: 20 },
        );

        const siteMap = {};
        for (const b of batches) {
            if (!b.site_id) continue;
            const sid = b.site_id[0];
            if (!siteMap[sid]) {
                siteMap[sid] = {
                    id: sid, name: b.site_id[1],
                    fillRate: b.fill_rate,
                    criticalGaps: b.critical_gap_count,
                    unassigned: b.unassigned_count,
                };
            } else {
                siteMap[sid].criticalGaps += b.critical_gap_count;
                siteMap[sid].unassigned += b.unassigned_count;
                siteMap[sid].fillRate = Math.min(siteMap[sid].fillRate, b.fill_rate);
            }
        }
        this.state.alertSites = Object.values(siteMap)
            .sort((a, b) => b.criticalGaps - a.criticalGaps)
            .slice(0, 6);
    }

    async autoFillGaps() {
        if (!this.state.activeBatchId) {
            this.notification.add("No active roster batch found.", { type: "warning" });
            return;
        }
        this.state.filling = true;
        try {
            const result = await this.orm.call(
                "security.roster.batch",
                "action_auto_fill_slots",
                [[this.state.activeBatchId]],
            );
            const msg = result?.params?.message || "Auto-fill complete.";
            const type = result?.params?.type || "success";
            this.notification.add(msg, { type });
            // Reload KPIs and alert sites after fill
            await Promise.all([this._loadKpi(), this._loadAlertSites()]);
        } finally {
            this.state.filling = false;
        }
    }

    async findReplacement(alert) {
        if (!alert.roster_slot_id) {
            this.notification.add("No roster slot linked to this alert.", { type: "warning" });
            return;
        }
        const slotId = alert.roster_slot_id[0];
        // Pre-generate suggestions, then open slot form
        await this.orm.call("security.roster.slot", "action_suggest_guards", [[slotId]]);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.roster.slot",
            res_id: slotId,
            views: [[false, "form"]],
            target: "new",
        });
    }

    openRosterBoard() {
        this.actionService.doAction({
            type: "ir.actions.client",
            tag: "security_shift_planner.roster_board",
        });
    }

    openLiveOps() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Live Ops — Today",
            res_model: "security.attendance.record",
            domain: [["shift_date", "=", this._today]],
            views: [[false, "kanban"], [false, "list"]],
        });
    }

    openBatch() {
        if (!this.state.activeBatchId) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "security.roster.batch",
            res_id: this.state.activeBatchId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    statusClass(pct) {
        if (pct >= 95) return "text-success";
        if (pct >= 75) return "text-warning";
        return "text-danger";
    }

    barClass(pct) {
        if (pct >= 95) return "bg-success";
        if (pct >= 75) return "bg-warning";
        return "bg-danger";
    }
}

registry.category("actions").add("security_operations.ops_dashboard", OpsDashboard);
