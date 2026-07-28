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
    footer: "Company Footer Info"
};

const PRESETS = {
    slate: { primary_color: "#475569", secondary_color: "#0f172a", font_family: "Inter", base_layout: "modern" },
    emerald: { primary_color: "#10b981", secondary_color: "#064e3b", font_family: "Inter", base_layout: "bold" },
    midnight: { primary_color: "#2563eb", secondary_color: "#1e3a8a", font_family: "Roboto", base_layout: "classic" },
    tactical: { primary_color: "#1e293b", secondary_color: "#000000", font_family: "system-ui", base_layout: "bold" }
};

export class DocumentDesigner extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        this.sortableList = useRef("sortableList");

        this.state = useState({
            documentType: 'invoice', // or 'quotation'
            isLoading: false,
            previewHtml: "",
            errorMsg: "",
            templateId: false,
            templateData: {
                primary_color: "#10b981",
                secondary_color: "#0f172a",
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
                header_bg_color: "#1e293b",
                header_text_color: "#ffffff",
                label_billed_to: "Billed To",
                blocks: ['header', 'client_info', 'line_items', 'totals', 'terms', 'footer']
            }
        });

        this.previewTimer = null;

        onWillStart(async () => {
            await loadJS("https://cdn.jsdelivr.net/npm/sortablejs@latest/Sortable.min.js");
            await this.loadDefaultTemplate();
        });

        onMounted(() => {
            this.initSortable();
            this.initInteractiveInspector();
            this.refreshPreview();
        });
    }

    // ── DATA LOADING ───────────────────────────────────────────────────────

    async loadDefaultTemplate() {
        const templates = await this.orm.searchRead(
            "security.document.template",
            [["document_type", "=", this.state.documentType]],
            [
                "id", "name", "primary_color", "secondary_color", "font_family", "base_layout",
                "show_payment_terms", "show_bank_details", "show_company_logo", "show_watermark",
                "show_tax_column", "logo_height", "logo_alignment", "custom_footer_note", "block_order"
            ],
            { limit: 1 }
        );

        if (templates.length > 0) {
            const tmpl = templates[0];
            this.state.templateId = tmpl.id;
            this.state.templateData = {
                primary_color: tmpl.primary_color || "#10b981",
                secondary_color: tmpl.secondary_color || "#0f172a",
                font_family: tmpl.font_family || "Inter",
                base_layout: tmpl.base_layout || "modern",
                show_payment_terms: tmpl.show_payment_terms,
                show_bank_details: tmpl.show_bank_details,
                show_company_logo: tmpl.show_company_logo,
                show_watermark: tmpl.show_watermark,
                show_tax_column: tmpl.show_tax_column,
                logo_height: tmpl.logo_height || 60,
                logo_alignment: tmpl.logo_alignment || "left",
                custom_footer_note: tmpl.custom_footer_note || "",
                header_bg_color: tmpl.header_bg_color || "#1e293b",
                header_text_color: tmpl.header_text_color || "#ffffff",
                label_billed_to: tmpl.label_billed_to || "Billed To",
                blocks: tmpl.block_order ? JSON.parse(tmpl.block_order) : ['header', 'client_info', 'line_items', 'totals', 'terms', 'footer']
            };
        } else {
            this.state.templateId = false;
            this.state.templateData = {
                primary_color: "#10b981",
                secondary_color: "#0f172a",
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
                header_bg_color: "#1e293b",
                header_text_color: "#ffffff",
                label_billed_to: "Billed To",
                blocks: ['header', 'client_info', 'line_items', 'totals', 'terms', 'footer']
            };
        }
    }

    resetTemplate() {
        if (confirm("Are you sure you want to discard your changes and load the last saved or default template?")) {
            this.loadDefaultTemplate();
            setTimeout(() => this.initSortable(), 100);
            this.triggerPreviewUpdate();
        }
    }

    // ── DRAG AND DROP (Sortable) ───────────────────────────────────────────

    initSortable() {
        if (this.sortableList.el && window.Sortable) {
            window.Sortable.create(this.sortableList.el, {
                animation: 150,
                handle: '.drag-handle',
                ghostClass: 'bg-light border-dashed',
                onEnd: (evt) => {
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
        const previewContainer = document.querySelector(".pcc-preview-container");
        if (previewContainer) {
            previewContainer.addEventListener("click", (e) => {
                const blockWrapper = e.target.closest("[data-block-id]");
                if (blockWrapper) {
                    const blockId = blockWrapper.getAttribute("data-block-id");
                    this._highlightBlockInSidebar(blockId);
                }
            });
        }
    }

    _highlightBlockInSidebar(blockId) {
        const blockEl = document.querySelector(`.pcc-builder-block[data-block="${blockId}"]`);
        if (blockEl) {
            blockEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
            blockEl.style.transition = 'all 0.3s ease';
            blockEl.style.boxShadow = '0 0 0 4px rgba(16, 185, 129, 0.4)';
            blockEl.style.borderColor = '#10b981';
            blockEl.style.transform = 'scale(1.03)';
            setTimeout(() => {
                blockEl.style.boxShadow = '';
                blockEl.style.borderColor = '';
                blockEl.style.transform = '';
            }, 1500);
        }
    }

    // ── PRESETS ────────────────────────────────────────────────────────────

    applyPreset(presetName) {
        const preset = PRESETS[presetName];
        if (preset) {
            this.state.templateData.primary_color = preset.primary_color;
            this.state.templateData.secondary_color = preset.secondary_color;
            this.state.templateData.font_family = preset.font_family;
            this.state.templateData.base_layout = preset.base_layout;
            this.triggerPreviewUpdate();
            this.notification.add(`Applied ${presetName.toUpperCase()} preset.`, { type: "info" });
        }
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
        }, 500);
    }

    async refreshPreview() {
        this.state.isLoading = true;
        this.state.errorMsg = "";
        
        try {
            let endpoint = '/billing/designer/preview_invoice';
            if (this.state.documentType === 'quotation') {
                endpoint = '/billing/designer/preview_quotation';
            }

            const result = await rpc(endpoint, {
                template_data: this.state.templateData
            });

            if (result.error) {
                this.state.errorMsg = result.error;
                this.state.previewHtml = "";
            } else if (result.html) {
                const parser = new DOMParser();
                const doc = parser.parseFromString(result.html, "text/html");
                const pageContent = doc.querySelector('.doc-page');
                if (pageContent) {
                    const styles = Array.from(doc.querySelectorAll('style, link[rel="stylesheet"]')).map(s => s.outerHTML).join('');
                    this.state.previewHtml = markup(styles + pageContent.outerHTML);
                } else {
                    this.state.previewHtml = markup(result.html);
                }
            }
        } catch (error) {
            this.state.errorMsg = "Failed to load preview. Ensure the server is running.";
            console.error("Preview error:", error);
        } finally {
            this.state.isLoading = false;
        }
    }

    openPdfPreview() {
        const reportName = this.state.documentType === 'quotation' 
            ? 'security_billing_sale.report_security_quotation' 
            : 'security_billing.report_security_invoice';
        
        window.open(`/report/html/${reportName}/1`, '_blank');
    }

    // ── SAVING ─────────────────────────────────────────────────────────────

    async saveTemplate() {
        this.state.isLoading = true;
        try {
            const vals = {
                name: `Custom ${this.state.documentType === 'invoice' ? 'Invoice' : 'Quotation'} Template`,
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
                block_order: JSON.stringify(this.state.templateData.blocks)
            };

            if (this.state.templateId) {
                await this.orm.write("security.document.template", [this.state.templateId], vals);
                this.notification.add("Template updated successfully", { type: "success" });
            } else {
                const newId = await this.orm.create("security.document.template", [vals]);
                this.state.templateId = newId[0];
                this.notification.add("Template created successfully", { type: "success" });
            }
            this.triggerPreviewUpdate();
        } catch (error) {
            this.notification.add("Error saving template: " + error.message, { type: "danger" });
        } finally {
            this.state.isLoading = false;
        }
    }
}

DocumentDesigner.template = "security_billing.DocumentDesigner";

registry.category("actions").add("security_document_designer", DocumentDesigner);
export { BLOCK_LABELS };
