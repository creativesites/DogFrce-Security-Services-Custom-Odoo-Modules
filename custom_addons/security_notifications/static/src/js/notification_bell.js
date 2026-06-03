/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class SecurityNotificationBell extends Component {
    static template = "security_notifications.NotificationBell";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            unreadCount: 0,
            notifications: [],
            open: false,
        });

        onWillStart(async () => {
            await this._loadNotifications();
        });
    }

    async _loadNotifications() {
        try {
            const records = await this.orm.searchRead(
                "security.notification",
                [["state", "=", "unread"]],
                ["title", "body", "notification_type", "severity", "create_date"],
                { limit: 10, order: "create_date desc" }
            );
            this.state.unreadCount = await this.orm.searchCount(
                "security.notification",
                [["state", "=", "unread"]]
            );
            this.state.notifications = records;
        } catch (_e) {
            this.state.unreadCount = 0;
        }
    }

    toggleDropdown() {
        this.state.open = !this.state.open;
        if (this.state.open) {
            this._loadNotifications();
        }
    }

    async markAllRead() {
        try {
            const ids = await this.orm.search("security.notification", [["state", "=", "unread"]]);
            if (ids.length) {
                await this.orm.call("security.notification", "action_mark_read", [ids]);
            }
            this.state.unreadCount = 0;
            this.state.notifications = [];
            this.state.open = false;
        } catch (_e) {}
    }

    openNotifications() {
        this.state.open = false;
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "security.notification",
            views: [[false, "list"], [false, "form"]],
            domain: [["state", "=", "unread"]],
        });
    }

    get bellColor() {
        return this.state.unreadCount > 0 ? "#dc2626" : "#64748b";
    }
}

registry.category("systray").add("security_notifications.bell", {
    Component: SecurityNotificationBell,
    sequence: 5,
});
