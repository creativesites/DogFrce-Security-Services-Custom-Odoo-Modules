/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, onWillUnmount } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class DeployGuardMainCommandCenter extends Component {
    static template = "security_base.DeployGuardMainCommandCenter";
    static props = { "*": true };

    setup() {
        this.action = useService("action");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            activeTab: "launchpad", // 'launchpad' | 'live_ops' | 'rostering' | 'financials' | 'guide'
            searchQuery: "",
            loading: true,
            userRoles: {
                isOwner: false,
                isManager: false,
                isSupervisor: false,
                isHR: false,
                isFinance: false,
            },
            attentionStrip: {
                unassignedSlotsCount: 0,
                awolCount: 0,
                expiringDocsCount: 0,
                pendingLeaveCount: 0,
                draftInvoicesCount: 0,
                hasItems: false,
            },
        });

        this.onGlobalKeyDown = this.onGlobalKeyDown.bind(this);

        onWillStart(async () => {
            await this._loadRolesAndMetrics();
        });

        onMounted(() => {
            window.addEventListener("keydown", this.onGlobalKeyDown);
        });

        onWillUnmount(() => {
            window.removeEventListener("keydown", this.onGlobalKeyDown);
        });
    }

    _todayStr() {
        const d = new Date();
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    _daysFromTodayStr(n) {
        const d = new Date();
        d.setDate(d.getDate() + n);
        return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    }

    async _loadRolesAndMetrics() {
        this.state.loading = true;
        const today = this._todayStr();
        const in7Days = this._daysFromTodayStr(7);

        try {
            // Check roles via ORM
            const [isOwner, isManager, isSupervisor, isHR, isFinance] = await Promise.all([
                this.orm.call("res.users", "has_group", ["security_base.group_security_owner"]).catch(() => false),
                this.orm.call("res.users", "has_group", ["security_base.group_security_manager"]).catch(() => false),
                this.orm.call("res.users", "has_group", ["security_base.group_security_supervisor"]).catch(() => false),
                this.orm.call("res.users", "has_group", ["hr.group_hr_user"]).catch(() => false),
                this.orm.call("res.users", "has_group", ["account.group_account_invoice"]).catch(() => false),
            ]);

            this.state.userRoles = { isOwner, isManager, isSupervisor, isHR, isFinance };

            // Fetch live attention strip counts
            const [
                unassignedSlotsCount,
                awolCount,
                expiringDocsCount,
                pendingLeaveCount,
                draftInvoicesCount,
            ] = await Promise.all([
                this.orm.searchCount("security.roster.slot", [
                    ["state", "=", "confirmed"],
                    ["employee_id", "=", false],
                    ["shift_date", ">=", today],
                ]).catch(() => 0),
                this.orm.searchCount("security.attendance.record", [
                    ["shift_date", "=", today],
                    ["absence_type", "=", "awol"],
                ]).catch(() => 0),
                this.orm.searchCount("security.employee.certification", [
                    ["expiry_date", ">=", today],
                    ["expiry_date", "<=", in7Days],
                ]).catch(() => 0),
                this.orm.searchCount("security.leave.request", [
                    ["state", "=", "submitted"],
                ]).catch(() => 0),
                this.orm.searchCount("security.billing.invoice", [
                    ["state", "=", "draft"],
                ]).catch(() => 0),
            ]);

            const hasItems = (unassignedSlotsCount + awolCount + expiringDocsCount + pendingLeaveCount + draftInvoicesCount) > 0;

            this.state.attentionStrip = {
                unassignedSlotsCount,
                awolCount,
                expiringDocsCount,
                pendingLeaveCount,
                draftInvoicesCount,
                hasItems,
            };
        } catch (err) {
            console.warn("DeployGuard Command Center metric load notice:", err);
        } finally {
            this.state.loading = false;
        }
    }

    onGlobalKeyDown(ev) {
        if (ev.key === "Escape") {
            this.close();
        }
    }

    close() {
        if (this.props.closeModal && typeof this.props.closeModal === "function") {
            this.props.closeModal();
        } else {
            try {
                this.action.doAction("security_operations.action_ops_dashboard");
            } catch (e) {
                console.error("Failed to dismiss Command Center:", e);
            }
        }
    }

    async openAction(actionXmlId) {
        try {
            if (this.props.closeModal && typeof this.props.closeModal === "function") {
                this.props.closeModal();
            }
            await this.action.doAction(actionXmlId);
        } catch (e) {
            console.error("Failed to open action:", actionXmlId, e);
            if (this.notification) {
                this.notification.add("Could not launch action: " + actionXmlId, { type: "warning" });
            }
        }
    }

    setTab(tabId) {
        this.state.activeTab = tabId;
    }

    matchesSearch(title, desc, keywords = []) {
        const query = (this.state.searchQuery || "").toLowerCase().trim();
        if (!query) return true;
        const text = `${title} ${desc} ${keywords.join(" ")}`.toLowerCase();
        return text.includes(query);
    }
}

registry.category("actions").add("deployguard.main_command_center", DeployGuardMainCommandCenter);
