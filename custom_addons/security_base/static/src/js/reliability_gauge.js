/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * ReliabilityGauge — OWL field widget for security_reliability_score (Integer).
 *
 * Renders an SVG circular gauge: green ≥ 80, amber 60–79, red < 60.
 * Falls back gracefully when displayed in read-only list rows (no SVG overhead
 * needed there — the standard integer renderer is used instead via the widget
 * registration's supportedTypes).
 */
class ReliabilityGauge extends Component {
    static template = "security_base.ReliabilityGauge";
    static props = { ...standardFieldProps };
    static supportedTypes = ["integer"];

    /** Circle circumference for r=40 */
    static CIRCUMFERENCE = 2 * Math.PI * 40;

    get score() {
        const val = this.props.value;
        return typeof val === "number" ? Math.max(0, Math.min(100, val)) : 0;
    }

    get color() {
        const s = this.score;
        if (s >= 80) return "#28a745";
        if (s >= 60) return "#ffc107";
        return "#dc3545";
    }

    get dashoffset() {
        return ReliabilityGauge.CIRCUMFERENCE * (1 - this.score / 100);
    }

    get circumference() {
        return ReliabilityGauge.CIRCUMFERENCE;
    }

    get label() {
        const s = this.score;
        if (s >= 80) return "Reliable";
        if (s >= 60) return "Moderate";
        return "At Risk";
    }
}

registry.category("fields").add("reliability_gauge", {
    component: ReliabilityGauge,
    supportedTypes: ["integer"],
});
