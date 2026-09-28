/** @odoo-module **/

import { Component, onMounted, onWillUnmount, reactive, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { findAnchor } from "./anchors";

const POLL_MS = 1500;

/**
 * DeployGuard guided tasks, the ERP side.
 *
 * Costs nothing when no guidance is running: one check at page load. When a
 * session is active (the employee pressed "Guide me" in DeployGuard, which
 * reloads this page) it reports which screen the employee is on and renders a
 * highlight around the real control. It never clicks, types or submits
 * anything: the employee does the work.
 *
 * All decisions (which step, done or not, off track or not) are made by
 * security.guidance.session on the server. The DeployGuard desktop reads the
 * same session through Odoo's normal API; nothing is injected into this page
 * from outside (desktop/RECONCILIATION.md C-10).
 */
export const guidanceService = {
    dependencies: ["orm", "action"],
    start(env, { orm, action }) {
        const state = reactive({ session: null });
        let timer = null;
        let busy = false;

        function uiState() {
            const c = action.currentController;
            const a = c?.action || {};
            return {
                action_xmlid: a.xml_id || null,
                action_id: a.id || null,
                client_tag: a.tag || null,
                model: c?.props?.resModel || a.res_model || null,
                view_type: c?.view?.type || null,
                res_id: c?.props?.resId || null,
                path: window.location.pathname,
            };
        }

        async function sync() {
            if (busy) {
                return;
            }
            busy = true;
            try {
                const session = await orm.silent.call("security.guidance.session", "report_ui_state", [uiState()]);
                state.session = session || null;
                if (!session || session.state !== "active") {
                    stop();
                }
            } catch {
                // Offline or no access: guidance quietly steps aside.
                stop();
            } finally {
                busy = false;
            }
        }

        function begin() {
            if (!timer) {
                timer = setInterval(sync, POLL_MS);
                env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", sync);
            }
            sync();
        }

        function stop() {
            clearInterval(timer);
            timer = null;
            env.bus.removeEventListener("ACTION_MANAGER:UI-UPDATED", sync);
        }

        orm.silent
            .call("security.guidance.session", "get_active", [])
            .then((session) => {
                if (session) {
                    state.session = session;
                    begin();
                }
            })
            .catch(() => {});

        return { state, begin };
    },
};

export class GuidanceOverlay extends Component {
    static template = "security_guidance.Overlay";
    static props = {};

    setup() {
        this.guidance = useState(this.env.services.deployguard_guidance.state);
        this.pos = useState({ ring: null, found: false, pulse: false, whyOpen: false });
        this.lastNonce = null;
        this.calloutRef = useRef("callout");
        onMounted(() => {
            this.tick = setInterval(() => this.place(), 250);
        });
        onWillUnmount(() => clearInterval(this.tick));
    }

    get session() {
        return this.guidance.session;
    }

    get step() {
        return this.session && this.session.state === "active" ? this.session.step : null;
    }

    place() {
        const step = this.step;
        if (!step) {
            this.pos.ring = null;
            return;
        }
        const el = findAnchor(step.target);
        this.pos.found = !!el;
        if (!el) {
            this.pos.ring = null;
            return;
        }
        const r = el.getBoundingClientRect();
        this.pos.ring = { top: r.top - 6, left: r.left - 6, width: r.width + 12, height: r.height + 12 };
        if (this.session.highlight_nonce !== this.lastNonce) {
            if (this.lastNonce !== null) {
                el.scrollIntoView({ block: "center", behavior: "smooth" });
                this.pos.pulse = true;
                setTimeout(() => (this.pos.pulse = false), 1400);
            }
            this.lastNonce = this.session.highlight_nonce;
        }
    }

    get ringStyle() {
        const r = this.pos.ring;
        return r ? `top:${r.top}px;left:${r.left}px;width:${r.width}px;height:${r.height}px;` : "";
    }

    get calloutStyle() {
        const r = this.pos.ring;
        if (!r) {
            return "";
        }
        const below = r.top + r.height + 12;
        const top = below + 160 > window.innerHeight ? Math.max(12, r.top - 172) : below;
        const left = Math.min(Math.max(12, r.left), window.innerWidth - 332);
        return `top:${top}px;left:${left}px;`;
    }
}

registry.category("services").add("deployguard_guidance", guidanceService);
registry.category("main_components").add("DeployGuardGuidanceOverlay", { Component: GuidanceOverlay });
