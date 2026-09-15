/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

const BLOCK_DEFS = {
    header: "Company Header & Status",
    employee_info: "Employee & Pay Period Details",
    attendance: "Time & Attendance Summary",
    leave_balances: "Leave Balances Grid",
    ytd_totals: "Year-To-Date (YTD) Totals",
    earnings: "Earnings Breakdown",
    deductions: "Deductions List",
    earnings_deductions_split: "Earnings & Deductions (Split)",
    totals: "Gross, Deductions & Net Take-Home",
    footer: "Signature & Authorization Block",
};

const PRESETS = {
    corporate_navy: {
        key: "corporate_navy",
        label: "Corporate Navy",
        primary_color: "#1B3A6B",
        secondary_color: "#0D1117",
        header_bg_color: "#1B3A6B",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "corporate",
    },
    emerald_guard: {
        key: "emerald_guard",
        label: "Emerald Guard",
        primary_color: "#0D7A4E",
        secondary_color: "#064e3b",
        header_bg_color: "#0D7A4E",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "bold",
    },
    slate_minimal: {
        key: "slate_minimal",
        label: "Slate Minimal",
        primary_color: "#475569",
        secondary_color: "#0f172a",
        header_bg_color: "#334155",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "minimalist",
    },
    tactical_dark: {
        key: "tactical_dark",
        label: "Tactical Dark",
        primary_color: "#1e293b",
        secondary_color: "#000000",
        header_bg_color: "#0f172a",
        header_text_color: "#ffffff",
        font_family: "system-ui",
        base_layout: "modern",
    },
};

const BRAND_PALETTE = [
    "#1B3A6B", // Corporate Navy
    "#0D7A4E", // Emerald Guard
    "#475569", // Slate
    "#1E293B", // Tactical Charcoal
    "#2563EB", // Royal Blue
    "#DC2626", // Crimson Alert
    "#0D1117", // Midnight Black
    "#FFFFFF", // Pure White
];

export class PayslipDesigner extends Component {
    static template = "security_payroll_core.PayslipDesigner";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");

        this.sortableContainer = useRef("sortableContainer");
        this.sortableInstance = null;

        // Initial state
        this.state = useState({
            template_id: this.props.action?.context?.default_template_id || false,
            name: "Standard Guard Payslip",
            availableTemplates: [],
            activeDrawerTab: "style", // 'style' | 'blocks' | 'content'
            selectedPreset: "corporate_navy",
            zoomScale: 100,
            font_family: "Inter",
            primary_color: "#1B3A6B",
            secondary_color: "#0D1117",
            base_layout: "modern",
            show_attendance_metrics: true,
            show_leave_balances: true,
            show_ytd: true,
            show_admin_signature: true,
            show_guard_signature: true,
            announcement_text: "",
            header_bg_color: "#1B3A6B",
            header_text_color: "#ffffff",
            label_payslip: "Payslip",
            blocks: [
                { id: "header", label: "Company Header & Status" },
                { id: "employee_info", label: "Employee & Pay Period Details" },
                { id: "attendance", label: "Time & Attendance Summary" },
                { id: "leave_balances", label: "Leave Balances Grid" },
                { id: "ytd_totals", label: "Year-To-Date (YTD) Totals" },
                { id: "earnings_deductions_split", label: "Earnings & Deductions (Split)" },
                { id: "totals", label: "Gross, Deductions & Net Take-Home" },
                { id: "footer", label: "Signature & Authorization Block" },
            ],
            isSaving: false,
            isPreviewLoading: false,
            isInitialLoading: true,
            previewHtml: markup("<div class='text-center p-5 text-muted'><i class='fa fa-spinner fa-spin fa-2x mb-2'/><br/>Initializing canvas…</div>"),
        });

        this.debounceTimer = null;

        onWillStart(async () => {
            try {
                await loadJS("https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js");
            } catch (err) {
                console.warn("SortableJS CDN could not be loaded; using manual arrow reordering:", err);
            }
            await this._loadAvailableTemplates();
            if (this.state.template_id) {
                await this._loadTemplate(this.state.template_id);
            } else if (this.state.availableTemplates.length > 0) {
                this.state.template_id = this.state.availableTemplates[0].id;
                await this._loadTemplate(this.state.template_id);
            }
        });

        onMounted(async () => {
            this._initSortable();
            this._initInteractiveInspector();
            await this._fetchPreview();
            this.state.isInitialLoading = false;
        });
    }

    get brandPalette() {
        return BRAND_PALETTE;
    }

    get presets() {
        return Object.values(PRESETS);
    }

    // ── NAVIGATION & FLOW ──────────────────────────────────────────────────

    onBackToPayroll() {
        this.actionService.doAction("security_payroll_core.action_payroll_command_center");
    }

    // ── ZOOM CONTROLS ──────────────────────────────────────────────────────

    zoomIn() {
        if (this.state.zoomScale < 150) {
            this.state.zoomScale = Math.min(150, this.state.zoomScale + 10);
        }
    }

    zoomOut() {
        if (this.state.zoomScale > 50) {
            this.state.zoomScale = Math.max(50, this.state.zoomScale - 10);
        }
    }

    zoomReset() {
        this.state.zoomScale = 100;
    }

    zoomFit() {
        this.state.zoomScale = 80;
    }

    // ── DRAWER TABS ────────────────────────────────────────────────────────

    setDrawerTab(tab) {
        this.state.activeDrawerTab = tab;
        if (tab === "blocks") {
            setTimeout(() => this._initSortable(), 80);
        }
    }

    // ── TEMPLATE MANAGEMENT ───────────────────────────────────────────────

    async _loadAvailableTemplates() {
        try {
            const tmpls = await this.orm.searchRead(
                "security.payslip.template",
                [],
                ["id", "name", "base_layout", "primary_color"],
                { order: "name asc" }
            );
            this.state.availableTemplates = tmpls || [];
        } catch (e) {
            console.warn("Could not load templates list", e);
            this.state.availableTemplates = [];
        }
    }

    async onTemplateSelect(ev) {
        const val = ev.target.value;
        if (val === "new") {
            this.createNewTemplate();
        } else {
            const id = parseInt(val, 10);
            if (id) {
                this.state.template_id = id;
                await this._loadTemplate(id);
                this._fetchPreview();
            }
        }
    }

    createNewTemplate() {
        this.state.template_id = false;
        this.state.name = "New Payslip Template";
        this.state.font_family = "Inter";
        this.state.primary_color = "#1B3A6B";
        this.state.secondary_color = "#0D1117";
        this.state.base_layout = "modern";
        this.state.header_bg_color = "#1B3A6B";
        this.state.header_text_color = "#ffffff";
        this.state.label_payslip = "Payslip";
        this.state.show_attendance_metrics = true;
        this.state.show_leave_balances = true;
        this.state.show_ytd = true;
        this.state.show_admin_signature = true;
        this.state.show_guard_signature = true;
        this.state.announcement_text = "";
        this.state.selectedPreset = "corporate_navy";
        this.state.blocks = [
            { id: "header", label: "Company Header & Status" },
            { id: "employee_info", label: "Employee & Pay Period Details" },
            { id: "attendance", label: "Time & Attendance Summary" },
            { id: "leave_balances", label: "Leave Balances Grid" },
            { id: "ytd_totals", label: "Year-To-Date (YTD) Totals" },
            { id: "earnings_deductions_split", label: "Earnings & Deductions (Split)" },
            { id: "totals", label: "Gross, Deductions & Net Take-Home" },
            { id: "footer", label: "Signature & Authorization Block" },
        ];
        this._fetchPreview();
        this.notification.add("Started a new custom template design.", { type: "info" });
    }

    async _loadTemplate(templateId) {
        try {
            const [tmpl] = await this.orm.read("security.payslip.template", [templateId], [
                "name", "font_family", "primary_color", "secondary_color", "base_layout",
                "show_attendance_metrics", "show_leave_balances", "show_ytd",
                "show_admin_signature", "show_guard_signature", "announcement_text", "block_order",
                "header_bg_color", "header_text_color", "label_payslip"
            ]);

            if (tmpl) {
                this.state.name = tmpl.name;
                this.state.font_family = tmpl.font_family || "Inter";
                this.state.primary_color = tmpl.primary_color || "#1B3A6B";
                this.state.secondary_color = tmpl.secondary_color || "#0D1117";
                this.state.base_layout = tmpl.base_layout || "modern";
                this.state.show_attendance_metrics = tmpl.show_attendance_metrics;
                this.state.show_leave_balances = tmpl.show_leave_balances;
                this.state.show_ytd = tmpl.show_ytd;
                this.state.show_admin_signature = tmpl.show_admin_signature;
                this.state.show_guard_signature = tmpl.show_guard_signature;
                this.state.announcement_text = tmpl.announcement_text || "";
                this.state.header_bg_color = tmpl.header_bg_color || "#1B3A6B";
                this.state.header_text_color = tmpl.header_text_color || "#ffffff";
                this.state.label_payslip = tmpl.label_payslip || "Payslip";
                this.state.selectedPreset = null;

                if (tmpl.block_order) {
                    try {
                        const blockIds = JSON.parse(tmpl.block_order);
                        this.state.blocks = blockIds.map(id => ({ id, label: BLOCK_DEFS[id] || id }));
                    } catch (e) {
                        console.error("Invalid block_order JSON", e);
                    }
                }
            }
        } catch (e) {
            this.notification.add("Failed to load template data.", { type: "danger" });
        }
    }

    async saveTemplate() {
        this.state.isSaving = true;
        const blockIds = this.state.blocks.map(b => b.id);
        const vals = {
            name: this.state.name || "Custom Payslip Template",
            font_family: this.state.font_family,
            primary_color: this.state.primary_color,
            secondary_color: this.state.secondary_color,
            base_layout: this.state.base_layout,
            show_attendance_metrics: this.state.show_attendance_metrics,
            show_leave_balances: this.state.show_leave_balances,
            show_ytd: this.state.show_ytd,
            show_admin_signature: this.state.show_admin_signature,
            show_guard_signature: this.state.show_guard_signature,
            announcement_text: this.state.announcement_text,
            header_bg_color: this.state.header_bg_color,
            header_text_color: this.state.header_text_color,
            label_payslip: this.state.label_payslip,
            block_order: JSON.stringify(blockIds),
        };

        try {
            if (this.state.template_id) {
                await this.orm.write("security.payslip.template", [this.state.template_id], vals);
                this.notification.add("Payslip Template updated successfully!", { type: "success" });
            } else {
                const res = await this.orm.create("security.payslip.template", [vals]);
                this.state.template_id = res[0];
                this.notification.add("New Payslip Template created!", { type: "success" });
            }
            await this._loadAvailableTemplates();
            this._fetchPreview();
        } catch (e) {
            this.notification.add("Failed to save template: " + e.message, { type: "danger" });
        } finally {
            this.state.isSaving = false;
        }
    }

    resetTemplate() {
        if (confirm("Are you sure you want to discard unsaved changes and reload this template?")) {
            if (this.state.template_id) {
                this._loadTemplate(this.state.template_id).then(() => {
                    this._triggerPreview();
                });
            } else {
                this.createNewTemplate();
            }
        }
    }

    // ── SORTABLE DRAG AND DROP & REORDERING ────────────────────────────────

    _initSortable() {
        const el = this.sortableContainer.el || document.querySelector(".pcc-builder-blocks");
        if (!el || !window.Sortable) {
            return;
        }

        if (this.sortableInstance) {
            try {
                this.sortableInstance.destroy();
            } catch (e) {}
        }

        this.sortableInstance = window.Sortable.create(el, {
            animation: 150,
            handle: ".pcc-drag-handle",
            ghostClass: "bg-light border-dashed",
            onEnd: () => {
                const blockElements = el.querySelectorAll("[data-block-id]");
                const newBlocks = [];
                blockElements.forEach(item => {
                    const blockId = item.dataset.blockId;
                    if (blockId) {
                        newBlocks.push({ id: blockId, label: BLOCK_DEFS[blockId] || blockId });
                    }
                });
                this.state.blocks = newBlocks;
                this._triggerPreview();
            },
        });
    }

    moveBlockUp(index) {
        if (index <= 0) return;
        const blocks = [...this.state.blocks];
        const temp = blocks[index - 1];
        blocks[index - 1] = blocks[index];
        blocks[index] = temp;
        this.state.blocks = blocks;
        this._triggerPreview();
    }

    moveBlockDown(index) {
        if (index >= this.state.blocks.length - 1) return;
        const blocks = [...this.state.blocks];
        const temp = blocks[index + 1];
        blocks[index + 1] = blocks[index];
        blocks[index] = temp;
        this.state.blocks = blocks;
        this._triggerPreview();
    }

    isBlockVisible(blockId) {
        if (blockId === "attendance") return this.state.show_attendance_metrics;
        if (blockId === "leave_balances") return this.state.show_leave_balances;
        if (blockId === "ytd_totals") return this.state.show_ytd;
        if (blockId === "footer") return this.state.show_admin_signature || this.state.show_guard_signature;
        return true;
    }

    toggleBlockVisibility(blockId) {
        if (blockId === "attendance") {
            this.state.show_attendance_metrics = !this.state.show_attendance_metrics;
        } else if (blockId === "leave_balances") {
            this.state.show_leave_balances = !this.state.show_leave_balances;
        } else if (blockId === "ytd_totals") {
            this.state.show_ytd = !this.state.show_ytd;
        } else if (blockId === "footer") {
            const next = !(this.state.show_admin_signature && this.state.show_guard_signature);
            this.state.show_admin_signature = next;
            this.state.show_guard_signature = next;
        }
        this._triggerPreview();
    }

    // ── INTERACTIVE CANVAS INSPECTOR ───────────────────────────────────────

    _initInteractiveInspector() {
        const previewContainer = document.querySelector(".pcc-preview-container");
        if (previewContainer) {
            previewContainer.addEventListener("click", (e) => {
                const blockWrapper = e.target.closest("[data-block-id]");
                if (blockWrapper) {
                    const blockId = blockWrapper.getAttribute("data-block-id");
                    this.state.activeDrawerTab = "blocks";
                    this._highlightBlockInSidebar(blockId);
                }
            });
        }
    }

    _highlightBlockInSidebar(blockId) {
        setTimeout(() => {
            const blockEl = document.querySelector(`.pcc-builder-block[data-block-id="${blockId}"]`);
            if (blockEl) {
                blockEl.scrollIntoView({ behavior: "smooth", block: "center" });
                blockEl.style.transition = "all 0.3s ease";
                blockEl.style.boxShadow = "0 0 0 4px rgba(27, 58, 107, 0.4)";
                blockEl.style.borderColor = "#1B3A6B";
                blockEl.style.transform = "scale(1.02)";
                setTimeout(() => {
                    blockEl.style.boxShadow = "";
                    blockEl.style.borderColor = "";
                    blockEl.style.transform = "";
                }, 1500);
            }
        }, 100);
    }

    // ── INSTANT LOCAL DOM STYLING ──────────────────────────────────────────

    _updateInstantStyles() {
        const page = document.querySelector(".pcc-payslip-page") || document.querySelector(".pcc-paper-sheet");
        if (!page) return;
        page.style.fontFamily = `'${this.state.font_family}', 'Inter', sans-serif`;
        page.querySelectorAll(".pcc-primary").forEach(el => el.style.setProperty("color", this.state.primary_color, "important"));
        page.querySelectorAll(".pcc-bg-primary").forEach(el => el.style.setProperty("background-color", this.state.primary_color, "important"));
        page.querySelectorAll(".pcc-secondary").forEach(el => el.style.setProperty("color", this.state.secondary_color, "important"));
        page.querySelectorAll(".pcc-bg-secondary").forEach(el => el.style.setProperty("background-color", this.state.secondary_color, "important"));
        page.querySelectorAll(".pcc-thead th, thead th").forEach(el => {
            el.style.setProperty("background-color", this.state.header_bg_color, "important");
            el.style.setProperty("color", this.state.header_text_color, "important");
        });
    }

    // ── PRESETS & COLOR UPDATES ────────────────────────────────────────────

    applyPreset(presetKey) {
        const preset = PRESETS[presetKey];
        if (preset) {
            this.state.primary_color = preset.primary_color;
            this.state.secondary_color = preset.secondary_color;
            this.state.header_bg_color = preset.header_bg_color;
            this.state.header_text_color = preset.header_text_color;
            this.state.font_family = preset.font_family;
            this.state.base_layout = preset.base_layout;
            this.state.selectedPreset = presetKey;
            this._updateInstantStyles();
            this._triggerPreview();
            this.notification.add(`Applied ${preset.label} preset.`, { type: "info" });
        }
    }

    onColorChange(colorKey, value) {
        this.state[colorKey] = value;
        this.state.selectedPreset = null;
        this._updateInstantStyles();
        this._triggerPreview();
    }

    setBrandPalette(primary, secondary, headerBg, headerText) {
        this.state.primary_color = primary;
        this.state.secondary_color = secondary;
        this.state.header_bg_color = headerBg;
        this.state.header_text_color = headerText;
        this.state.selectedPreset = null;
        this._updateInstantStyles();
        this._triggerPreview();
    }

    onLayoutChange() {
        this.state.selectedPreset = null;
        this._triggerPreview();
    }

    onFontChange() {
        this.state.selectedPreset = null;
        this._updateInstantStyles();
        this._triggerPreview();
    }

    // ── LIVE PREVIEW ───────────────────────────────────────────────────────

    _triggerPreview() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        this.debounceTimer = setTimeout(() => {
            this._fetchPreview();
        }, 300);
    }

    async _fetchPreview() {
        this.state.isPreviewLoading = true;

        const templateData = {
            font_family: this.state.font_family,
            primary_color: this.state.primary_color,
            secondary_color: this.state.secondary_color,
            base_layout: this.state.base_layout,
            show_attendance_metrics: this.state.show_attendance_metrics,
            show_leave_balances: this.state.show_leave_balances,
            show_ytd: this.state.show_ytd,
            show_admin_signature: this.state.show_admin_signature,
            show_guard_signature: this.state.show_guard_signature,
            announcement_text: this.state.announcement_text,
            header_bg_color: this.state.header_bg_color,
            header_text_color: this.state.header_text_color,
            label_payslip: this.state.label_payslip,
            blocks: this.state.blocks.map(b => b.id),
        };

        try {
            const result = await rpc("/payroll/designer/preview", {
                template_data: templateData,
            });
            if (result.html) {
                const parser = new DOMParser();
                const doc = parser.parseFromString(result.html, "text/html");
                const pageContent = doc.querySelector(".pcc-payslip-page");

                if (pageContent) {
                    const styles = Array.from(doc.querySelectorAll("style, link[rel='stylesheet']")).map(s => s.outerHTML).join("");
                    this.state.previewHtml = markup(styles + pageContent.outerHTML);
                } else {
                    this.state.previewHtml = markup("<div class='alert alert-warning'>Could not parse preview.</div>");
                }
            } else if (result.error) {
                this.state.previewHtml = markup(`<div class="alert alert-danger">${result.error}</div>`);
            }
        } catch (error) {
            console.error("Preview fetch error:", error);
            this.state.previewHtml = markup("<div class='alert alert-danger'>Server error while fetching preview.</div>");
        } finally {
            this.state.isPreviewLoading = false;
        }
    }

    openPdfPreview() {
        const templateId = this.state.template_id || "";
        window.open(`/payroll/designer/print?template_id=${templateId}`, "_blank");
    }
}

registry.category("actions").add("security_payslip_designer", PayslipDesigner);
registry.category("actions").add("security_payroll_core.payslip_designer", PayslipDesigner);
