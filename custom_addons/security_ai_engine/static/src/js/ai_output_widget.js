/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

// ── JSON parser ───────────────────────────────────────────────────────────────

/**
 * Extract the first balanced JSON object from a string.
 * Uses bracket counting so it works even when there is trailing text after the
 * closing brace (common with markdown fences or AI preamble).
 * Returns the parsed object, or null if nothing could be extracted.
 */
function _extractByBrackets(s) {
    const start = s.indexOf("{");
    if (start < 0) return null;

    let depth = 0;
    let inStr = false;
    let esc = false;

    for (let i = start; i < s.length; i++) {
        const c = s[i];
        if (esc)          { esc = false; continue; }
        if (c === "\\")   { esc = true;  continue; }
        if (c === '"')    { inStr = !inStr; continue; }
        if (inStr)        continue;
        if (c === "{")    depth++;
        if (c === "}") {
            depth--;
            if (depth === 0) {
                try { return JSON.parse(s.slice(start, i + 1)); } catch { return null; }
            }
        }
    }
    return null; // never reached depth 0 → truncated
}

/**
 * Attempt to repair a truncated JSON string by closing any open
 * braces/arrays at the last position that was syntactically safe.
 * Returns the repaired parsed object, or null if repair failed.
 */
function _repairTruncatedJson(s) {
    const opener = { "{": "}", "[": "]" };
    const stack  = [];
    let inStr = false;
    let esc   = false;
    let lastComma = -1; // last top-level comma position (safe truncation point)

    const start = s.indexOf("{");
    if (start < 0) return null;

    for (let i = start; i < s.length; i++) {
        const c = s[i];
        if (esc)        { esc = false; continue; }
        if (c === "\\") { esc = true;  continue; }
        if (c === '"')  { inStr = !inStr; continue; }
        if (inStr)      continue;
        if (c in opener) stack.push(opener[c]);
        if (c === "}" || c === "]") stack.pop();
        // Track last comma at root-object depth (depth === 1)
        if (c === "," && stack.length === 1) lastComma = i;
    }

    if (stack.length === 0) return null; // wasn't actually truncated

    const closers = stack.reverse().join("");

    // Attempt 1: close at the very end
    try { return JSON.parse(s.slice(start) + closers); } catch { /* ignore */ }

    // Attempt 2: truncate at last safe comma, then close
    if (lastComma > start) {
        try { return JSON.parse(s.slice(start, lastComma) + closers); } catch { /* ignore */ }
    }

    return null;
}

/**
 * Parse an AI response string into a component-tree object.
 *
 * Multi-strategy approach:
 *   1. Strip any ```json … ``` fences (greedy — works even when closing fence is absent)
 *   2. Try JSON.parse on the extracted/raw string
 *   3. Try bracket-balanced extraction (handles trailing prose after the JSON)
 *   4. Try JSON repair for truncated responses
 *   5. Fall back to { _raw } for raw-text display
 *
 * Returns null for empty input, { _raw } for unparseable text, or a parsed object.
 */
function parseAIOutput(raw) {
    if (!raw || !raw.trim()) return null;

    const s = raw.trim();

    // ── Strategy 1: extract from code fence ────────────────────────────────
    // Greedy (.+) so we capture content even when the closing ``` is missing.
    const fenceMatch = s.match(/```(?:json)?\s*([\s\S]+?)(?:```|$)/);
    if (fenceMatch) {
        const inner = fenceMatch[1].trim();
        if (inner.startsWith("{")) {
            // a) direct parse
            try { return JSON.parse(inner); } catch { /* fall through */ }
            // b) bracket extraction (trailing text after JSON inside fence)
            const r = _extractByBrackets(inner);
            if (r) return r;
            // c) repair truncated JSON inside the fence
            const rep = _repairTruncatedJson(inner);
            if (rep) return { ...rep, _truncated: true };
        }
    }

    // ── Strategy 2: bracket extraction from the full string ────────────────
    const objStart = s.indexOf("{");
    if (objStart >= 0) {
        // a) fast path
        try { return JSON.parse(s.slice(objStart)); } catch { /* fall through */ }
        // b) bracket-balanced
        const r = _extractByBrackets(s.slice(objStart));
        if (r) return r;
        // c) truncated repair
        const rep = _repairTruncatedJson(s.slice(objStart));
        if (rep) return { ...rep, _truncated: true };
    }

    // ── Fallback: raw text ──────────────────────────────────────────────────
    return { _raw: raw };
}

// ── Severity / variant helpers ────────────────────────────────────────────────

function variantToBg(variant) {
    const map = {
        success: "#dcfce7",
        info:    "#e0f2fe",
        warning: "#fef3c7",
        danger:  "#fee2e2",
    };
    return map[variant] || map.info;
}

function variantToBorder(variant) {
    const map = {
        success: "#16a34a",
        info:    "#0284c7",
        warning: "#d97706",
        danger:  "#dc2626",
    };
    return map[variant] || map.info;
}

function variantToText(variant) {
    const map = {
        success: "#14532d",
        info:    "#0c4a6e",
        warning: "#78350f",
        danger:  "#7f1d1d",
    };
    return map[variant] || map.info;
}

function variantToIcon(variant) {
    const map = {
        success: "fa-check-circle",
        info:    "fa-info-circle",
        warning: "fa-exclamation-triangle",
        danger:  "fa-exclamation-circle",
    };
    return map[variant] || map.info;
}

function severityToBorder(severity) {
    const map = { CRITICAL: "#dc2626", WARNING: "#d97706", INFO: "#0284c7", OK: "#16a34a" };
    return map[(severity || "").toUpperCase()] || "#94a3b8";
}

function severityToBadgeBg(severity) {
    const map = { CRITICAL: "#fee2e2", WARNING: "#fef3c7", INFO: "#e0f2fe", OK: "#dcfce7" };
    return map[(severity || "").toUpperCase()] || "#f1f5f9";
}

function severityToBadgeText(severity) {
    const map = { CRITICAL: "#dc2626", WARNING: "#d97706", INFO: "#0284c7", OK: "#16a34a" };
    return map[(severity || "").toUpperCase()] || "#64748b";
}

function trendIcon(trend) {
    if (trend === "up") return "fa-arrow-up";
    if (trend === "down") return "fa-arrow-down";
    return "fa-minus";
}

function trendColor(severity) {
    const map = {
        danger:  "#dc2626",
        warning: "#d97706",
        success: "#16a34a",
        info:    "#0284c7",
    };
    return map[severity] || "#64748b";
}


// ── Component: Alert ──────────────────────────────────────────────────────────

class AiAlert extends Component {
    static template = "security_ai_engine.AiAlert";
    static props = { c: { type: Object, optional: true } };
    get c()      { return this.props.c || {}; }
    get bg()     { return variantToBg(this.c.variant); }
    get border() { return variantToBorder(this.c.variant); }
    get text()   { return variantToText(this.c.variant); }
    get icon()   { return variantToIcon(this.c.variant); }
}

// ── Component: MetricRow ──────────────────────────────────────────────────────

class AiMetricRow extends Component {
    static template = "security_ai_engine.AiMetricRow";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }

    trendIcon(m) { return trendIcon(m.trend); }
    valueColor(m) { return trendColor(m.severity); }
}

// ── Component: Finding ────────────────────────────────────────────────────────

class AiFinding extends Component {
    static template = "security_ai_engine.AiFinding";
    static props = { c: { type: Object, optional: true } };
    get c()            { return this.props.c || {}; }
    get borderColor()  { return severityToBorder(this.c.severity); }
    get badgeBg()      { return severityToBadgeBg(this.c.severity); }
    get badgeText()    { return severityToBadgeText(this.c.severity); }
}

// ── Component: Recommendation ─────────────────────────────────────────────────

class AiRecommendation extends Component {
    static template = "security_ai_engine.AiRecommendation";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }

    get meta() {
        const c = this.c;
        const parts = [];
        if (c.guard) parts.push({ icon: "fa-user",      label: c.guard });
        if (c.post)  parts.push({ icon: "fa-map-marker", label: c.post  });
        if (c.date)  parts.push({ icon: "fa-calendar",   label: c.date  });
        return parts;
    }
}

// ── Component: Table ──────────────────────────────────────────────────────────

class AiTable extends Component {
    static template = "security_ai_engine.AiTable";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }
}

// ── Component: Section ────────────────────────────────────────────────────────

class AiSection extends Component {
    static template = "security_ai_engine.AiSection";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }
}

// ── Component: BulletList ─────────────────────────────────────────────────────

class AiBulletList extends Component {
    static template = "security_ai_engine.AiBulletList";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }
}

// ── Component: DataTable (clickable rows → navigate) ─────────────────────────

class AiDataTable extends Component {
    static template = "security_ai_engine.AiDataTable";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }

    setup() {
        this.actionService = useService("action");
    }

    openRow(row) {
        if (!row.model) return;
        if (row.id) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: row.model,
                res_id: row.id,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
        } else if (row.domain) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: row.model,
                view_mode: "list,form",
                domain: row.domain,
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
        }
    }
}

// ── Component: RecordCard ─────────────────────────────────────────────────────

class AiRecordCard extends Component {
    static template = "security_ai_engine.AiRecordCard";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }

    setup() {
        this.actionService = useService("action");
    }

    openRecord() {
        const c = this.props.c;
        if (!c.model || !c.id) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: c.model,
            res_id: c.id,
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }
}

// ── Component: Navigate chip ──────────────────────────────────────────────────

class AiNavigate extends Component {
    static template = "security_ai_engine.AiNavigate";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }

    setup() {
        this.actionService = useService("action");
    }

    go() {
        const c = this.props.c;
        if (!c.model) return;
        if (c.id) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: c.model,
                res_id: c.id,
                view_mode: "form",
                views: [[false, "form"]],
                target: "current",
            });
        } else {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: c.model,
                view_mode: "list,form",
                domain: c.domain || [],
                views: [[false, "list"], [false, "form"]],
                target: "current",
            });
        }
    }
}

// AiNavigate and AiNavigateList share the same logic
const AiNavigateList = AiNavigate;

// ── Component: StatComparison ─────────────────────────────────────────────────

class AiStatComparison extends Component {
    static template = "security_ai_engine.AiStatComparison";
    static props = { c: { type: Object, optional: true } };
    get c() { return this.props.c || {}; }

    itemColor(item) { return trendColor(item.severity || "info"); }
    itemTrend(item) { return trendIcon(item.trend); }
}

// ── Component: ActionConfirm (chat-only — requires onConfirmAction callback) ──

class AiActionConfirm extends Component {
    static template = "security_ai_engine.AiActionConfirm";
    static props = {
        c: { type: Object, optional: true },
        onConfirmAction: { type: Function, optional: true },
    };
    get c() { return this.props.c || {}; }

    confirm() {
        if (this.props.onConfirmAction && this.props.c.action_token) {
            this.props.onConfirmAction(this.props.c.action_token);
        }
    }
}

// ── Component: QuickReplies (chat-only — requires onQuickReply callback) ─────

class AiQuickReplies extends Component {
    static template = "security_ai_engine.AiQuickReplies";
    static props = {
        c: { type: Object, optional: true },
        onQuickReply: { type: Function, optional: true },
    };
    get c() { return this.props.c || {}; }

    reply(s) {
        if (this.props.onQuickReply) this.props.onQuickReply(s);
    }
}

// ── Confidence indicator ──────────────────────────────────────────────────────

class AiConfidence extends Component {
    static template = "security_ai_engine.AiConfidence";
    static props = { score: Number };
    get score() { return this.props.score; }

    get dots() {
        return Array.from({ length: 5 }, (_, i) => i < (this.props.score || 0));
    }
}

// ── Summary bar ───────────────────────────────────────────────────────────────

class AiSummaryBar extends Component {
    static template = "security_ai_engine.AiSummaryBar";
    static components = { AiConfidence };
    static props = { parsed: Object };
    get parsed() { return this.props.parsed; }

    get statusVariant() {
        return this.props.parsed.status === "clean" ? "success" : "findings" ? "warning" : "info";
    }
    get statusLabel() {
        return this.props.parsed.status === "clean" ? "Clean" : "Findings";
    }
    get statusBg() { return variantToBg(this.statusVariant); }
    get statusBorder() { return variantToBorder(this.statusVariant); }
    get statusText() { return variantToText(this.statusVariant); }
}

// ── Shared component map (all types excluding chat-interactive ones) ──────────

const _FIELD_COMPONENTS = {
    AiSummaryBar,
    AiAlert, AiMetricRow, AiFinding, AiRecommendation,
    AiTable, AiSection, AiBulletList,
    AiDataTable, AiRecordCard, AiNavigate, AiStatComparison,
};

const _ALL_COMPONENTS = {
    ..._FIELD_COMPONENTS,
    AiActionConfirm, AiQuickReplies,
};

function _componentTag(type) {
    return {
        alert:          "AiAlert",
        metric_row:     "AiMetricRow",
        finding:        "AiFinding",
        recommendation: "AiRecommendation",
        table:          "AiTable",
        section:        "AiSection",
        bullet_list:    "AiBulletList",
        data_table:     "AiDataTable",
        record_card:    "AiRecordCard",
        navigate:       "AiNavigate",
        navigate_list:  "AiNavigate",
        stat_comparison:"AiStatComparison",
        action_confirm: "AiActionConfirm",
        quick_replies:  "AiQuickReplies",
    }[type] || null;
}

// ── AiComponentRenderer — standalone renderer (used by chat panel) ────────────

export class AiComponentRenderer extends Component {
    static template = "security_ai_engine.AiComponentRenderer";
    static components = _ALL_COMPONENTS;
    static props = {
        components:      { type: Array,    optional: true },
        parsed:          { type: Object,   optional: true },
        showSummary:     { type: Boolean,  optional: true },
        onQuickReply:    { type: Function, optional: true },
        onConfirmAction: { type: Function, optional: true },
    };

    setup() {
        this.state = useState({ expanded: true });
    }

    get _parsed() {
        return this.props.parsed || { components: this.props.components || [] };
    }

    get comps() {
        return (this._parsed.components || []).filter(Boolean);
    }

    componentTag(type) { return _componentTag(type); }

    toggleExpand() { this.state.expanded = !this.state.expanded; }
}

// ── AiOutputWidget — Odoo field widget (bound to a record field) ──────────────

export class AiOutputWidget extends Component {
    static template = "security_ai_engine.AiOutputWidget";
    static components = {
        AiSummaryBar,
        ..._FIELD_COMPONENTS,
    };
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ expanded: true });
    }

    get rawValue() {
        return this.props.record.data[this.props.name] || "";
    }

    get parsed() {
        return parseAIOutput(this.rawValue);
    }

    get isEmpty() {
        return !this.rawValue.trim();
    }

    get isRaw() {
        const p = this.parsed;
        return p && "_raw" in p;
    }

    // JSON was parsed but the components array is absent or empty —
    // most commonly because the AI response was cut off by the token limit.
    get isTruncated() {
        const p = this.parsed;
        if (!p || "_raw" in p) return false;
        const noComponents = !Array.isArray(p.components) || p.components.length === 0;
        return noComponents;
    }

    // JSON was parsed AND repaired from a truncated response.
    get wasRepaired() {
        return !!this.parsed?._truncated;
    }

    get isStructured() {
        const p = this.parsed;
        return p && !("_raw" in p) && Array.isArray(p.components) && p.components.length > 0;
    }

    get components() {
        return (this.parsed?.components || []).filter(Boolean);
    }

    get partialSummary() {
        return this.parsed?.summary || null;
    }

    componentTag(type) {
        return _componentTag(type);
    }

    toggleExpand() {
        this.state.expanded = !this.state.expanded;
    }
}

registry.category("fields").add("ai_output", { component: AiOutputWidget });
