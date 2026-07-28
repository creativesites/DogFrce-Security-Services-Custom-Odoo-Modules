/** @odoo-module **/

import { Component, useState, onWillStart, onMounted, useRef, markup } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const BLOCK_DEFS = {
    header: "Company Header",
    employee_info: "Employee Details",
    attendance: "Attendance Metrics",
    leave_balances: "Leave Balances",
    ytd_totals: "Year-To-Date Totals",
    earnings: "Earnings List",
    deductions: "Deductions List",
    earnings_deductions_split: "Earnings/Deductions (Split)",
    totals: "Totals & Net Pay",
    footer: "Signature Footer",
};

const PRESETS = {
    slate: { primary_color: "#475569", secondary_color: "#0f172a", font_family: "Inter", base_layout: "modern" },
    emerald: { primary_color: "#10b981", secondary_color: "#064e3b", font_family: "Inter", base_layout: "bold" },
    midnight: { primary_color: "#2563eb", secondary_color: "#1e3a8a", font_family: "Roboto", base_layout: "corporate" },
    tactical: { primary_color: "#1e293b", secondary_color: "#000000", font_family: "system-ui", base_layout: "bold" }
};

export class PayslipDesigner extends Component {
    static template = "security_payroll_core.PayslipDesigner";

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.actionService = useService("action");
        
        this.sortableContainer = useRef("sortableContainer");

        // Initial default state
        this.state = useState({
            template_id: this.props.action.context.default_template_id || false,
            name: "New Payslip Template",
            font_family: "Inter",
            primary_color: "#10b981",
            secondary_color: "#0f172a",
            base_layout: "modern",
            show_attendance_metrics: true,
            show_leave_balances: true,
            show_ytd: true,
            show_admin_signature: true,
            show_guard_signature: true,
            announcement_text: "",
            header_bg_color: "#1e293b",
            header_text_color: "#ffffff",
            label_payslip: "Payslip",
            blocks: [
                { id: "header", label: "Company Header" },
                { id: "employee_info", label: "Employee Details" },
                { id: "attendance", label: "Attendance Metrics" },
                { id: "leave_balances", label: "Leave Balances" },
                { id: "ytd_totals", label: "Year-To-Date Totals" },
                { id: "earnings_deductions_split", label: "Earnings/Deductions (Split)" },
                { id: "totals", label: "Totals & Net Pay" },
                { id: "footer", label: "Signature Footer" },
            ],
            isPreviewLoading: false,
            previewHtml: markup("<div class='text-center p-5 text-muted'>Loading preview...</div>"),
        });

        this.debounceTimer = null;

        onWillStart(async () => {
            if (this.state.template_id) {
                await this._loadTemplate(this.state.template_id);
            }
        });

        onMounted(() => {
            this._initSortable();
            this._initInteractiveInspector();
            this._fetchPreview();
        });
    }

    // ── TEMPLATE LOADING & SAVING ─────────────────────────────────────────

    async _loadTemplate(templateId) {
        try {
            const [tmpl] = await this.orm.read("security.payslip.template", [templateId], [
                "name", "font_family", "primary_color", "secondary_color", "base_layout",
                "show_attendance_metrics", "show_leave_balances", "show_ytd",
                "show_admin_signature", "show_guard_signature", "announcement_text", "block_order"
            ]);
            
            if (tmpl) {
                this.state.name = tmpl.name;
                this.state.font_family = tmpl.font_family;
                this.state.primary_color = tmpl.primary_color;
                this.state.secondary_color = tmpl.secondary_color;
                this.state.base_layout = tmpl.base_layout;
                this.state.show_attendance_metrics = tmpl.show_attendance_metrics;
                this.state.show_leave_balances = tmpl.show_leave_balances;
                this.state.show_ytd = tmpl.show_ytd;
                this.state.show_admin_signature = tmpl.show_admin_signature;
                this.state.show_guard_signature = tmpl.show_guard_signature;
                this.state.announcement_text = tmpl.announcement_text || "";
                this.state.header_bg_color = tmpl.header_bg_color || "#1e293b";
                this.state.header_text_color = tmpl.header_text_color || "#ffffff";
                this.state.label_payslip = tmpl.label_payslip || "Payslip";

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
        const blockIds = this.state.blocks.map(b => b.id);
        const vals = {
            name: this.state.name,
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
            this._fetchPreview();
        } catch (e) {
            this.notification.add("Failed to save template.", { type: "danger" });
        }
    }

    // ── SORTABLE DRAG AND DROP ────────────────────────────────────────────

    resetTemplate() {
        if (confirm("Are you sure you want to discard your changes and load the last saved or default template?")) {
            if (this.state.template_id) {
                this._loadTemplate(this.state.template_id).then(() => {
                    this._triggerPreview();
                });
            } else {
                this.state.font_family = "Inter";
                this.state.primary_color = "#10b981";
                this.state.secondary_color = "#0f172a";
                this.state.base_layout = "modern";
                this.state.header_bg_color = "#1e293b";
                this.state.header_text_color = "#ffffff";
                this.state.label_payslip = "Payslip";
                this.state.show_attendance_metrics = true;
                this.state.show_leave_balances = true;
                this.state.show_ytd = true;
                this.state.show_admin_signature = true;
                this.state.show_guard_signature = true;
                this.state.announcement_text = "";
                this.state.blocks = [
                    { id: "header", label: "Company Header" },
                    { id: "employee_info", label: "Employee Details" },
                    { id: "attendance", label: "Attendance Metrics" },
                    { id: "leave_balances", label: "Leave Balances" },
                    { id: "ytd_totals", label: "Year-To-Date Totals" },
                    { id: "earnings_deductions_split", label: "Earnings/Deductions (Split)" },
                    { id: "totals", label: "Totals & Net Pay" },
                    { id: "footer", label: "Signature Footer" },
                ];
                this._triggerPreview();
            }
        }
    }

    _initSortable() {
        if (!this.sortableContainer.el || typeof Sortable === "undefined") {
            return;
        }

        new Sortable(this.sortableContainer.el, {
            animation: 150,
            handle: ".pcc-drag-handle",
            ghostClass: "bg-light",
            onEnd: (evt) => {
                const newOrder = [];
                const blockElements = this.sortableContainer.el.querySelectorAll("[data-block-id]");
                blockElements.forEach(el => {
                    const blockId = el.dataset.blockId;
                    newOrder.push({ id: blockId, label: BLOCK_DEFS[blockId] || blockId });
                });
                this.state.blocks = newOrder;
                this._triggerPreview();
            },
        });
    }

    // ── INTERACTIVE CANVAS INSPECTOR ───────────────────────────────────────

    _initInteractiveInspector() {
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
        const blockEl = document.querySelector(`.pcc-builder-block[data-block-id="${blockId}"]`);
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

    // ── PRESET HANDLING ───────────────────────────────────────────────────

    applyPreset(presetName) {
        const preset = PRESETS[presetName];
        if (preset) {
            this.state.primary_color = preset.primary_color;
            this.state.secondary_color = preset.secondary_color;
            this.state.font_family = preset.font_family;
            this.state.base_layout = preset.base_layout;
            this._triggerPreview();
            this.notification.add(`Applied ${presetName.toUpperCase()} preset.`, { type: "info" });
        }
    }

    // ── LIVE PREVIEW ───────────────────────────────────────────────────────

    _triggerPreview() {
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }
        this.debounceTimer = setTimeout(() => {
            this._fetchPreview();
        }, 500); // 500ms debounce
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
                template_data: templateData
            });
            if (result.html) {
                const parser = new DOMParser();
                const doc = parser.parseFromString(result.html, "text/html");
                const pageContent = doc.querySelector('.pcc-payslip-page');
                
                if (pageContent) {
                    const styles = Array.from(doc.querySelectorAll('style, link[rel="stylesheet"]')).map(s => s.outerHTML).join('');
                    this.state.previewHtml = markup(styles + pageContent.outerHTML);
                } else {
                    this.state.previewHtml = markup("<div class='alert alert-warning'>Could not render preview. Ensure there is at least 1 payslip in the system.</div>");
                }
            } else if (result.error) {
                this.state.previewHtml = markup(`<div class="alert alert-danger">${result.error}</div>`);
            }
        } catch (error) {
            console.error(error);
            this.state.previewHtml = markup("<div class='alert alert-danger'>Server error while fetching preview.</div>");
        } finally {
            this.state.isPreviewLoading = false;
        }
    }

    openPdfPreview() {
        window.open('/report/html/security_payroll_core.report_security_payslip/1', '_blank');
    }
}

registry.category("actions").add("security_payslip_designer", PayslipDesigner);
registry.category("actions").add("security_payroll_core.payslip_designer", PayslipDesigner);
