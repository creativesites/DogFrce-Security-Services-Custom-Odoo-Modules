/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class WhatsAppChatWorkspace extends Component {
    static template = "security_whatsapp.ChatWorkspace";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            threads: [],
            activePhone: null,
            activeThread: null,
            replyText: "",
            loading: true,
        });

        onWillStart(async () => {
            await this.loadThreads();
        });
    }

    async loadThreads() {
        try {
            this.state.loading = true;
            const res = await this.orm.call("security.whatsapp.dashboard", "get_chat_workspace_threads", ["all"]);
            if (res && res.length) {
                this.state.threads = res;
                if (!this.state.activePhone) {
                    this.selectThread(res[0].phone);
                } else {
                    const match = res.find(t => t.phone === this.state.activePhone);
                    if (match) {
                        this.state.activeThread = match;
                    }
                }
            } else {
                this.state.threads = [];
                this.state.activeThread = null;
            }
        } catch (e) {
            console.error("Failed to load WhatsApp Chat Workspace threads:", e);
        } finally {
            this.state.loading = false;
        }
    }

    selectThread(phone) {
        this.state.activePhone = phone;
        const thread = this.state.threads.find(t => t.phone === phone);
        if (thread) {
            this.state.activeThread = thread;
        }
    }

    async sendReply() {
        if (!this.state.activePhone || !this.state.replyText || !this.state.replyText.trim()) {
            return;
        }
        const text = this.state.replyText.trim();
        const phone = this.state.activePhone;
        this.state.replyText = "";

        try {
            const res = await this.orm.call("security.whatsapp.dashboard", "send_manual_chat_reply", [phone, text]);
            if (res && res.success) {
                this.notification.add("Reply sent successfully over WhatsApp!", { type: "success" });
                await this.loadThreads();
            } else {
                this.notification.add(res.error || "Failed to send WhatsApp message.", { type: "danger" });
            }
        } catch (e) {
            console.error("Failed to send WhatsApp reply:", e);
            this.notification.add("Error sending reply.", { type: "danger" });
        }
    }

    onInputKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendReply();
        }
    }
}

registry.category("actions").add("security_whatsapp.ChatWorkspace", WhatsAppChatWorkspace);
