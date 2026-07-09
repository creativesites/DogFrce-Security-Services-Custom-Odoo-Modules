/** @odoo-module **/

import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";
import { AiComponentRenderer } from "./ai_output_widget";

// ── Greeting suggestions shown when chat is empty ─────────────────────────────

const _GREETINGS_FULL = [
    "How many guards were AWOL this week?",
    "Show me pending actions",
    "Who are the top 5 guards by reliability score?",
    "What invoices are overdue?",
    "Summarise today's attendance",
];

const _GREETINGS_LITE = [
    "What can you help me with?",
    "How does roster scheduling work?",
    "Explain the payroll process",
    "How do I handle a guard AWOL?",
];

// ── Main Chat Panel ───────────────────────────────────────────────────────────

class SecurityAIChatPanel extends Component {
    static template = "security_ai_engine.AiChatPanel";
    static components = { AiComponentRenderer };
    static props = { "*": true };

    setup() {
        this.action = useService("action");
        this.notification = useService("notification");

        this.messagesRef = useRef("messages");
        this.inputRef = useRef("input");

        this.state = useState({
            isOpen: false,
            messages: [],       // {role, content, components, id}
            hasInput: false,    // true when textarea has non-empty text
            loading: false,
            sessionId: null,
            unreadCount: 0,
            historyLoaded: false,
            liteMode: localStorage.getItem("dogforce_ai_lite") !== "0",  // default ON
        });

        onMounted(async () => {
            const saved = parseInt(localStorage.getItem("dogforce_ai_session") || "0");
            if (saved) await this._loadHistory(saved);
        });
    }

    // ── Mode ───────────────────────────────────────────────────────────────────

    get activeGreetings() {
        return this.state.liteMode ? _GREETINGS_LITE : _GREETINGS_FULL;
    }

    toggleMode() {
        this.state.liteMode = !this.state.liteMode;
        localStorage.setItem("dogforce_ai_lite", this.state.liteMode ? "1" : "0");
    }

    // ── Context ────────────────────────────────────────────────────────────────

    get currentContext() {
        const path = window.location.pathname;
        const m = path.match(/\/odoo\/([^/]+)(?:\/(\d+))?/);
        const menuEl = document.querySelector(".o_menu_brand");
        return {
            current_url: path,
            url_slug: m ? m[1] : null,
            url_id: m && m[2] ? parseInt(m[2]) : null,
            active_menu: menuEl ? menuEl.textContent.trim() : null,
        };
    }

    get contextLabel() {
        const ctx = this.currentContext;
        if (ctx.active_menu) return ctx.active_menu;
        if (ctx.url_slug) return ctx.url_slug.replace(/-/g, " ");
        return "Home";
    }

    // ── Toggle ─────────────────────────────────────────────────────────────────

    togglePanel() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen) {
            this.state.unreadCount = 0;
            this._focusInput();
        }
    }

    // ── Messaging ──────────────────────────────────────────────────────────────

    async sendMessage(messageOverride) {
        // Read from DOM ref for user-typed messages; use override for quick replies
        const raw = messageOverride ?? (this.inputRef.el ? this.inputRef.el.value : "");
        const message = raw.trim();
        if (!message || this.state.loading) return;

        // Clear the textarea via DOM ref (avoids OWL controlled-input edge cases)
        if (!messageOverride && this.inputRef.el) {
            this.inputRef.el.value = "";
        }
        this.state.hasInput = false;

        this.state.messages = [
            ...this.state.messages,
            { role: "user", content: message },
        ];
        this.state.loading = true;
        this._scrollToBottom();

        try {
            const endpoint = this.state.liteMode
                ? "/web/ai-chat/message-lite"
                : "/web/ai-chat/message";
            const result = await rpc(endpoint, {
                session_id: this.state.sessionId,
                message,
                context: this.currentContext,
            });

            this.state.sessionId = result.session_id;
            localStorage.setItem("dogforce_ai_session", result.session_id);

            this.state.messages = [
                ...this.state.messages,
                {
                    role: "assistant",
                    components: result.components || [],
                    id: result.message_id,
                },
            ];

            if (!this.state.isOpen) this.state.unreadCount += 1;
        } catch (err) {
            this.notification.add("Could not reach the AI assistant.", { type: "warning" });
        } finally {
            this.state.loading = false;
            this._scrollToBottom();
        }
    }

    // ── Confirmation ───────────────────────────────────────────────────────────

    async confirmAction(actionToken) {
        if (!actionToken) return;
        try {
            const result = await rpc("/web/ai-chat/confirm", {
                action_token: actionToken,
            });
            if (result.success) {
                this.state.messages = [
                    ...this.state.messages,
                    { role: "assistant", components: result.components || [] },
                ];
                this._scrollToBottom();
            } else {
                this.notification.add(result.error || "Action failed.", { type: "danger" });
            }
        } catch (err) {
            this.notification.add("Failed to execute the action.", { type: "danger" });
        }
    }

    // ── Quick replies ──────────────────────────────────────────────────────────

    async sendQuickReply(question) {
        await this.sendMessage(question);
    }

    // ── New chat ───────────────────────────────────────────────────────────────

    async newChat() {
        this.state.messages = [];
        this.state.sessionId = null;
        this.state.historyLoaded = false;
        localStorage.removeItem("dogforce_ai_session");
        try {
            const r = await rpc("/web/ai-chat/new-session", {});
            this.state.sessionId = r.session_id;
            localStorage.setItem("dogforce_ai_session", r.session_id);
        } catch (_e) {}
        this._focusInput();
    }

    // ── History ────────────────────────────────────────────────────────────────

    async _loadHistory(sessionId) {
        try {
            const r = await rpc("/web/ai-chat/history", { session_id: sessionId });
            if (r.session_id) {
                this.state.sessionId = r.session_id;
                localStorage.setItem("dogforce_ai_session", r.session_id);
                this.state.messages = (r.messages || []).map(m => ({
                    role: m.role,
                    content: m.content,
                    components: Array.isArray(m.components)
                        ? m.components.filter(Boolean)
                        : [],
                }));
                this.state.historyLoaded = true;
            }
        } catch (_e) {}
    }

    // ── Input handling ─────────────────────────────────────────────────────────

    onInputKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    onInputChange(ev) {
        // Track whether there is any text so the send button activates
        this.state.hasInput = !!ev.target.value.trim();
    }

    // ── DOM helpers ────────────────────────────────────────────────────────────

    _scrollToBottom() {
        requestAnimationFrame(() => {
            const el = this.messagesRef.el;
            if (el) el.scrollTop = el.scrollHeight;
        });
    }

    _focusInput() {
        requestAnimationFrame(() => {
            const el = this.inputRef.el;
            if (el) {
                el.focus();
                // Ensure the send button reflects DOM state after focus
                this.state.hasInput = !!el.value.trim();
            }
        });
    }
}

registry.category("main_components").add("SecurityAIChatPanel", {
    Component: SecurityAIChatPanel,
    props: {},
});
