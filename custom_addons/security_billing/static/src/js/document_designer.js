/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef, markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { rpc } from "@web/core/network/rpc";

const BLOCK_LABELS = {
    header: "Company Logo & Header",
    client_info: "Client Details",
    line_items: "Line Items Table",
    totals: "Totals & Tax Summary",
    terms: "Payment Terms & Bank Details",
    footer: "Company Footer Info",
};

const PRESETS = {
    corporate_navy: {
        label: "Corporate Navy",
        primary_color: "#1B3A6B",
        secondary_color: "#0D1117",
        header_bg_color: "#1B3A6B",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "modern",
    },
    emerald_guard: {
        label: "Emerald Guard",
        primary_color: "#0D7A4E",
        secondary_color: "#064e3b",
        header_bg_color: "#0D7A4E",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "bold",
    },
    slate_minimal: {
        label: "Slate Minimal",
        primary_color: "#475569",
        secondary_color: "#0f172a",
        header_bg_color: "#334155",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "minimalist",
    },
    tactical_dark: {
        label: "Tactical Dark",
        primary_color: "#1e293b",
        secondary_color: "#000000",
        header_bg_color: "#0f172a",
        header_text_color: "#ffffff",
        font_family: "system-ui",
        base_layout: "bold",
    },
    // Aliases for backwards compatibility
    slate: {
        label: "Slate",
        primary_color: "#475569",
        secondary_color: "#0f172a",
        header_bg_color: "#334155",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "modern",
    },
    emerald: {
        label: "Emerald",
        primary_color: "#0D7A4E",
        secondary_color: "#064e3b",
        header_bg_color: "#0D7A4E",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "bold",
    },
    midnight: {
        label: "Midnight",
        primary_color: "#1B3A6B",
        secondary_color: "#0D1117",
        header_bg_color: "#1B3A6B",
        header_text_color: "#ffffff",
        font_family: "Inter",
        base_layout: "modern",
    },
    tactical: {
        label: "Tactical",
        primary_color: "#1e293b",
        secondary_color: "#000000",
        header_bg_color: "#0f172a",
        header_text_color: "#ffffff",
        font_family: "system-ui",
        base_layout: "bold",
    },
};

export class DocumentDesigner extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.sortableList = useRef("sortableList");

        this.state = useState({
            documentType: "invoice", // 'invoice' or 'quotation'
            availableTemplates: [],
            templateId: false,
            templateName: "Modern Invoice",
            activeDrawerTab: "style", // 'style' | 'blocks' | 'content'
            selectedPreset: "corporate_navy",
            zoomScale: 100,
            isLoading: false,
            isSaving: false,
            previewHtml: "",
            errorMsg: "",
            templateData: {
                primary_color: "#1B3A6B",
                secondary_color: "#0D1117",
                font_family: "Inter",
                base_layout: "modern",
                show_payment_terms: true,
                show_bank_details: true,
                show_company_logo: true,
                show_watermark: false,
                show_tax_column: true,
                logo_height: 60,
                logo_alignment: "left",
                custom_footer_note: "",
                header_bg_color: "#1B3A6B",
                header_text_color: "#ffffff",
                label_billed_to: "Billed To",
                blocks: ["header", "client_info", "line_items", "totals", "terms", "footer"],
            },
        });

        this.previewTimer = null;
        this.sortableInstance = null;

        onWillStart(async () => {
            try {
                await loadJS("https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js");
            } catch (e) {
                console.warn("SortableJS CDN could not be loaded, using manual reorder controls:", e);
            }
            await this.loadDefaultTemplate();
        });

        onMounted(() => {
            this.initSortable();
            this.initInteractiveInspector();
            this.refreshPreview();
        });
    }

    // ── NAVIGATION & FLOW ──────────────────────────────────────────────────

    onBackToBilling() {
        this.actionService.doAction("security_billing.action_billing_command_center");
    }

    // ── DATA LOADING & TEMPLATES ───────────────────────────────────────────

    async loadAvailableTemplates() {
        try {
            const templates = await this.orm.searchRead(
                "security.document.template",
                [["document_type", "=", this.state.documentType]],
                [
                    "id", "name", "document_type", "primary_color", "secondary_color", "font_family",
                    "base_layout", "show_payment_terms", "show_bank_details", "show_company_logo",
                    "show_watermark", "show_tax_column", "logo_height", "logo_alignment",
                    "custom_footer_note", "header_bg_color", "header_text_color", "label_billed_to",
                    "block_order"
                ],
                { order: "name asc" }
            );
            this.state.availableTemplates = templates || [];
            return this.state.availableTemplates;
        } catch (e) {
            console.error("Failed to load available document templates", e);
            this.state.availableTemplates = [];
            return [];
        }
    }

    async loadDefaultTemplate() {
        const templates = await this.loadAvailableTemplates();
        if (templates.length > 0) {
            await this.loadTemplateById(templates[0].id);
        } else {
            this.createNewTemplate();
        }
    }

    async loadTemplateById(templateId) {
        const tmpl = this.state.availableTemplates.find(t => t.id === templateId);
        if (tmpl) {
            this.state.templateId = tmpl.id;
            this.state.templateName = tmpl.name || `Custom ${this.state.documentType === 'invoice' ? 'Invoice' : 'Quotation'}`;
            let blocks = ["header", "client_info", "line_items", "totals", "terms", "footer"];
            if (tmpl.block_order) {
                try {
                    blocks = JSON.parse(tmpl.block_order);
                } catch (e) {
                    console.error("Invalid block_order JSON", e);
                }
            }

            this.state.templateData = {
                primary_color: tmpl.primary_color || "#1B3A6B",
                secondary_color: tmpl.secondary_color || "#0D1117",
                font_family: tmpl.font_family || "Inter",
                base_layout: tmpl.base_layout || "modern",
                show_payment_terms: tmpl.show_payment_terms !== undefined ? tmpl.show_payment_terms : true,
                show_bank_details: tmpl.show_bank_details !== undefined ? tmpl.show_bank_details : true,
                show_company_logo: tmpl.show_company_logo !== undefined ? tmpl.show_company_logo : true,
                show_watermark: !!tmpl.show_watermark,
                show_tax_column: tmpl.show_tax_column !== undefined ? tmpl.show_tax_column : true,
                logo_height: tmpl.logo_height || 60,
                logo_alignment: tmpl.logo_alignment || "left",
                custom_footer_note: tmpl.custom_footer_note || "",
                header_bg_color: tmpl.header_bg_color || "#1B3A6B",
                header_text_color: tmpl.header_text_color || "#ffffff",
                label_billed_to: tmpl.label_billed_to || "Billed To",
                blocks: blocks,
            };
        }
    }

    async onTemplateSelect(ev) {
        const val = ev.target.value;
        if (val === "new") {
            this.createNewTemplate();
            return;
        }
        const templateId = parseInt(val, 10);
        await this.loadTemplateById(templateId);
        setTimeout(() => this.initSortable(), 100);
        this.triggerPreviewUpdate();
    }

    createNewTemplate() {
        this.state.templateId = false;
        const docName = this.state.documentType === "invoice" ? "Invoice" : "Quotation";
        this.state.templateName = `New ${docName} Template`;
        this.state.templateData = {
            primary_color: "#1B3A6B",
            secondary_color: "#0D1117",
            font_family: "Inter",
            base_layout: "modern",
            show_payment_terms: true,
            show_bank_details: true,
            show_company_logo: true,
            show_watermark: false,
            show_tax_column: true,
            logo_height: 60,
            logo_alignment: "left",
            custom_footer_note: "",
            header_bg_color: "#1B3A6B",
            header_text_color: "#ffffff",
            label_billed_to: "Billed To",
            blocks: ["header", "client_info", "line_items", "totals", "terms", "footer"],
        };
        setTimeout(() => this.initSortable(), 100);
        this.triggerPreviewUpdate();
        this.notification.add(`Started a new ${docName.toLowerCase()} template design.`, { type: "info" });
    }

    resetTemplate() {
        if (confirm("Are you sure you want to discard unsaved changes and reload this template?")) {
            if (this.state.templateId) {
                this.loadTemplateById(this.state.templateId);
            } else {
                this.loadDefaultTemplate();
            }
            setTimeout(() => this.initSortable(), 100);
            this.triggerPreviewUpdate();
        }
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
            setTimeout(() => this.initSortable(), 80);
        }
    }

    // ── BLOCK REORDERING ───────────────────────────────────────────────────

    getBlockLabel(blockKey) {
        return BLOCK_LABELS[blockKey] || blockKey.replace(/_/g, " ");
    }

    moveBlockUp(index) {
        if (index <= 0) return;
        const blocks = [...this.state.templateData.blocks];
        const temp = blocks[index - 1];
        blocks[index - 1] = blocks[index];
        blocks[index] = temp;
        this.state.templateData.blocks = blocks;
        this.triggerPreviewUpdate();
    }

    moveBlockDown(index) {
        if (index >= this.state.templateData.blocks.length - 1) return;
        const blocks = [...this.state.templateData.blocks];
        const temp = blocks[index + 1];
        blocks[index + 1] = blocks[index];
        blocks[index] = temp;
        this.state.templateData.blocks = blocks;
        this.triggerPreviewUpdate();
    }

    initSortable() {
        if (this.sortableList.el && window.Sortable) {
            if (this.sortableInstance) {
                try {
                    this.sortableInstance.destroy();
                } catch (e) {
                    // Ignore destroy error
                }
            }
            this.sortableInstance = window.Sortable.create(this.sortableList.el, {
                animation: 150,
                handle: ".drag-handle",
                ghostClass: "bg-light border-dashed",
                onEnd: () => {
                    const newBlocks = [];
                    Array.from(this.sortableList.el.children).forEach(child => {
                        if (child.dataset.block) {
                            newBlocks.push(child.dataset.block);
                        }
                    });
                    this.state.templateData.blocks = newBlocks;
                    this.triggerPreviewUpdate();
                },
            });
        }
    }

    // ── INTERACTIVE CANVAS INSPECTOR ───────────────────────────────────────

    initInteractiveInspector() {
        const previewContainer = document.querySelector(".pcc-preview-container") || document.querySelector(".doc-preview-container");
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
            const blockEl = document.querySelector(`.doc-builder-block[data-block="${blockId}"]`) || document.querySelector(`.pcc-builder-block[data-block="${blockId}"]`);
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

    // ── PRESETS ────────────────────────────────────────────────────────────

    applyPreset(presetKey) {
        const preset = PRESETS[presetKey];
        if (preset) {
            this.state.templateData.primary_color = preset.primary_color;
            this.state.templateData.secondary_color = preset.secondary_color;
            this.state.templateData.font_family = preset.font_family;
            this.state.templateData.base_layout = preset.base_layout;
            if (preset.header_bg_color) {
                this.state.templateData.header_bg_color = preset.header_bg_color;
            }
            if (preset.header_text_color) {
                this.state.templateData.header_text_color = preset.header_text_color;
            }
            this.state.selectedPreset = presetKey;
            this._updateInstantStyles();
            this.triggerPreviewUpdate();
            this.notification.add(`Applied ${preset.label || presetKey} preset.`, { type: "info" });
        }
    }

    onColorInput(key, val) {
        this.state.templateData[key] = val;
        this.state.selectedPreset = null;
        this._updateInstantStyles();
    }

    setBrandPalette(primary, secondary, headerBg, headerText) {
        this.state.templateData.primary_color = primary;
        this.state.templateData.secondary_color = secondary;
        this.state.templateData.header_bg_color = headerBg;
        this.state.templateData.header_text_color = headerText;
        this.state.selectedPreset = null;
        this._updateInstantStyles();
        this.triggerPreviewUpdate();
    }

    onLayoutChange() {
        this.state.selectedPreset = null;
        this.triggerPreviewUpdate();
    }

    onFontChange() {
        this.state.selectedPreset = null;
        this._updateInstantStyles();
        this.triggerPreviewUpdate();
    }

    _updateInstantStyles() {
        const preview = document.querySelector(".doc-paper-sheet") || document.querySelector(".doc-preview-container");
        if (!preview) return;

        const data = this.state.templateData;
        const page = preview.querySelector(".doc-page");
        if (page) {
            page.style.fontFamily = `"${data.font_family}", Inter, -apple-system, sans-serif`;
        }
        preview.querySelectorAll(".doc-primary").forEach(el => {
            el.style.setProperty("color", data.primary_color, "important");
        });
        preview.querySelectorAll(".doc-bg-primary").forEach(el => {
            el.style.setProperty("background-color", data.primary_color, "important");
        });
        preview.querySelectorAll(".doc-secondary").forEach(el => {
            el.style.setProperty("color", data.secondary_color, "important");
        });
        preview.querySelectorAll(".doc-bg-secondary").forEach(el => {
            el.style.setProperty("background-color", data.secondary_color, "important");
        });
        preview.querySelectorAll("th").forEach(el => {
            el.style.setProperty("background-color", data.header_bg_color, "important");
            el.style.setProperty("color", data.header_text_color, "important");
        });
    }

    // ── NAVIGATION / TABS ──────────────────────────────────────────────────

    async setDocumentType(type) {
        if (this.state.documentType !== type) {
            this.state.documentType = type;
            await this.loadDefaultTemplate();
            setTimeout(() => this.initSortable(), 100);
            this.refreshPreview();
        }
    }

    // ── LIVE PREVIEW ───────────────────────────────────────────────────────

    triggerPreviewUpdate() {
        clearTimeout(this.previewTimer);
        this.previewTimer = setTimeout(() => {
            this.refreshPreview();
        }, 400);
    }

    async refreshPreview() {
        this.state.isLoading = true;
        this.state.errorMsg = "";

        try {
            let endpoint = "/billing/designer/preview_invoice";
            if (this.state.documentType === "quotation") {
                endpoint = "/billing/designer/preview_quotation";
            }

            const result = await rpc(endpoint, {
                template_data: this.state.templateData,
            });

            if (result.error) {
                this.state.errorMsg = result.error;
                this.state.previewHtml = "";
            } else if (result.html) {
                const parser = new DOMParser();
                const doc = parser.parseFromString(result.html, "text/html");
                const pageContent = doc.querySelector(".doc-page");
                if (pageContent) {
                    const styles = Array.from(doc.querySelectorAll("style, link[rel='stylesheet']")).map(s => s.outerHTML).join("");
                    this.state.previewHtml = markup(styles + pageContent.outerHTML);
                } else {
                    this.state.previewHtml = markup(result.html);
                }
            }
        } catch (error) {
            this.state.errorMsg = "Failed to load live preview. Ensure the local server is running.";
            console.error("Preview error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    openPdfPreview() {
        const templateId = this.state.templateId || "";
        const docType = this.state.documentType || "invoice";
        window.open(`/billing/designer/print?type=${docType}&template_id=${templateId}`, "_blank");
    }

    // ── SAVING ─────────────────────────────────────────────────────────────

    async saveTemplate() {
        this.state.isSaving = true;
        try {
            const vals = {
                name: this.state.templateName || `Custom ${this.state.documentType === "invoice" ? "Invoice" : "Quotation"} Template`,
                document_type: this.state.documentType,
                primary_color: this.state.templateData.primary_color,
                secondary_color: this.state.templateData.secondary_color,
                font_family: this.state.templateData.font_family,
                base_layout: this.state.templateData.base_layout,
                show_payment_terms: this.state.templateData.show_payment_terms,
                show_bank_details: this.state.templateData.show_bank_details,
                show_company_logo: this.state.templateData.show_company_logo,
                show_watermark: this.state.templateData.show_watermark,
                show_tax_column: this.state.templateData.show_tax_column,
                logo_height: this.state.templateData.logo_height,
                logo_alignment: this.state.templateData.logo_alignment,
                custom_footer_note: this.state.templateData.custom_footer_note,
                header_bg_color: this.state.templateData.header_bg_color,
                header_text_color: this.state.templateData.header_text_color,
                label_billed_to: this.state.templateData.label_billed_to,
                block_order: JSON.stringify(this.state.templateData.blocks),
            };

            if (this.state.templateId) {
                await this.orm.write("security.document.template", [this.state.templateId], vals);
                this.notification.add("Template updated successfully", { type: "success" });
            } else {
                const newId = await this.orm.create("security.document.template", [vals]);
                this.state.templateId = newId[0];
                this.notification.add("Template created successfully", { type: "success" });
            }
            await this.loadAvailableTemplates();
            this.triggerPreviewUpdate();
        } catch (error) {
            this.notification.add("Error saving template: " + error.message, { type: "danger" });
        } finally {
            this.state.isSaving = false;
        }
    }
}

DocumentDesigner.template = "security_billing.DocumentDesigner";

registry.category("actions").add("security_document_designer", DocumentDesigner);
export { BLOCK_LABELS, PRESETS };
