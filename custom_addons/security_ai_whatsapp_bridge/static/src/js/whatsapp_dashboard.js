/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class WhatsAppDashboard extends Component {
    static template = "security_whatsapp.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            data: {
                bridge_status: "disconnected",
                today_messages_count: 0,
                inbound_count: 0,
                outbound_count: 0,
                attendance_logged: 0,
                awol_flagged: 0,
                incidents_reported: 0,
                ai_resolution_rate: 100,
                recent_activity: [],
                hourly_counts: [],
            },
            loading: true,
        });

        onWillStart(async () => {
            await this.fetchDashboardData();
        });
    }

    async fetchDashboardData() {
        try {
            this.state.loading = true;
            const res = await this.orm.call("security.whatsapp.dashboard", "get_dashboard_data", []);
            if (res) {
                this.state.data = res;
            }
        } catch (e) {
            console.error("Failed to load WhatsApp Dashboard metrics:", e);
        } finally {
            this.state.loading = false;
        }
    }

    async refreshDashboard() {
        await this.fetchDashboardData();
    }

    openSettings() {
        this.action.doAction("security_ai_whatsapp_bridge.action_security_whatsapp_config_server");
    }

    openAuditLogs() {
        this.action.doAction("security_ai_whatsapp_bridge.action_security_whatsapp_message_log");
    }

    openWorkspace() {
        this.action.doAction("security_ai_whatsapp_bridge.action_whatsapp_chat_workspace_client");
    }
}

registry.category("actions").add("security_whatsapp.Dashboard", WhatsAppDashboard);
