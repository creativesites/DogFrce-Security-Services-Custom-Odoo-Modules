/** @odoo-module **/

/**
 * Finds the real ERP control a guided step points at. Anchors are tried in
 * order, most stable first:
 *   {anchor}  a data-dg-anchor attribute placed on purpose in our own screens
 *   {menu}    an Odoo menu xmlid (data-menu-xmlid)
 *   {button}  an Odoo button name (button[name])
 *   {field}   an Odoo field name
 *   {css}     a CSS selector
 *   {text}    visible text, optionally within {selector}
 * Never screen coordinates: those break the moment the window is resized.
 */

function visible(el) {
    if (!el || el.closest(".o_dg_guidance")) {
        return false;
    }
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
}

function first(selector) {
    for (const el of document.querySelectorAll(selector)) {
        if (visible(el)) {
            return el;
        }
    }
    return null;
}

function byText(text, selector) {
    const wanted = text.trim().toLowerCase();
    let partial = null;
    for (const el of document.querySelectorAll(selector || "button, a, [role=button], [role=menuitem], label, .dropdown-item")) {
        if (!visible(el)) {
            continue;
        }
        const t = (el.textContent || "").replace(/\s+/g, " ").trim().toLowerCase();
        if (t === wanted) {
            return el;
        }
        if (!partial && t.includes(wanted)) {
            partial = el;
        }
    }
    return partial;
}

export function findAnchor(anchors) {
    for (const a of anchors || []) {
        let el = null;
        try {
            if (a.anchor) {
                el = first(`[data-dg-anchor="${CSS.escape(a.anchor)}"]`);
            } else if (a.menu) {
                el = first(`[data-menu-xmlid="${CSS.escape(a.menu)}"]`);
            } else if (a.button) {
                el = first(`button[name="${CSS.escape(a.button)}"]`);
            } else if (a.field) {
                el = first(`.o_field_widget[name="${CSS.escape(a.field)}"], div[name="${CSS.escape(a.field)}"]`);
            } else if (a.css) {
                el = first(a.css);
            } else if (a.text) {
                el = byText(a.text, a.selector);
            }
        } catch {
            el = null; // a bad selector in step data must never break the page
        }
        if (el) {
            return el;
        }
    }
    return null;
}
