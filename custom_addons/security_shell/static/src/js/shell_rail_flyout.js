/** @odoo-module **/

import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

/** Popover content for a rail icon's hover preview — mounted via Odoo's own
 * popover service (see shell_rail.js), which portals it into
 * MainComponentsContainer instead of leaving it as a DOM descendant of the
 * rail's own scrolling icon list. That distinction matters: CSS overflow
 * clipping on an ancestor still clips a plain `position: absolute`/`fixed`
 * descendant, so a hand-rolled hover flyout nested inside
 * .dgs-rail-sections (which scrolls vertically once there are more than a
 * handful of top-level sections) would get silently cropped. The popover
 * service is Odoo's own answer to exactly this problem.
 *
 * Two shapes: a plain one-line tooltip (props.nodes is null/empty — just
 * props.label), or a full preview of the section's real subtree, fully
 * expanded rather than click-to-drill (props.nodes), since this is a
 * transient hover surface, not a persistent nav state to remember.
 *
 * Opened with { holdOnHover: true } (see shell_rail.js) as a bonus, but
 * this component also bridges its own hover state explicitly via
 * onHoverStart/onHoverEnd — the trigger's own close-timer (in shell_rail.js)
 * is cancelled while the pointer is over the popover itself, so moving the
 * mouse diagonally from the rail icon into the flyout never closes it
 * prematurely. */
export class ShellRailFlyout extends Component {
    static template = "security_shell.ShellRailFlyout";
    static props = {
        label: { type: String, optional: true },
        nodes: { type: Array, optional: true },
        onNavigate: { type: Function, optional: true },
        onHoverStart: { type: Function, optional: true },
        onHoverEnd: { type: Function, optional: true },
        close: { type: Function, optional: true },
    };

    setup() {
        this.rootRef = useRef("root");
        onMounted(() => {
            this.rootRef.el?.addEventListener("mouseenter", this.props.onHoverStart);
            this.rootRef.el?.addEventListener("mouseleave", this.props.onHoverEnd);
        });
        onWillUnmount(() => {
            this.rootRef.el?.removeEventListener("mouseenter", this.props.onHoverStart);
            this.rootRef.el?.removeEventListener("mouseleave", this.props.onHoverEnd);
        });
    }

    onRowClick(node) {
        if (!node.clickable) {
            return;
        }
        this.props.onNavigate?.(node);
        this.props.close?.();
    }
}
