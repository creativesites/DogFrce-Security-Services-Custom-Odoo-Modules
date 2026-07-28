from odoo import api, fields, models


class SecurityDocumentTemplate(models.Model):
    _name = "security.document.template"
    _description = "Document Visual Template"
    _order = "name"

    name = fields.Char(required=True, help="Name of the template (e.g., Corporate B2B Invoice)")
    document_type = fields.Selection(
        [
            ("invoice", "Invoice"),
            ("quotation", "Quotation"),
        ],
        required=True,
        default="invoice",
    )
    base_layout = fields.Selection(
        [
            ("modern", "Modern"),
            ("classic", "Classic"),
            ("minimalist", "Minimalist"),
            ("bold", "Bold"),
        ],
        default="modern",
        required=True,
    )
    primary_color = fields.Char(default="#10b981", help="Primary brand color (hex)")
    secondary_color = fields.Char(default="#0f172a", help="Secondary accent color (hex)")
    font_family = fields.Selection(
        [
            ("Inter", "Inter"),
            ("Roboto", "Roboto"),
            ("system-ui", "System UI"),
        ],
        default="Inter",
        required=True,
    )
    show_payment_terms = fields.Boolean(default=True, string="Show Payment Terms")
    show_bank_details = fields.Boolean(default=True, string="Show Bank Details")
    show_company_logo = fields.Boolean(default=True, string="Show Company Logo")
    show_watermark = fields.Boolean(default=False, string="Show Watermark")
    show_tax_column = fields.Boolean(default=True, string="Show Tax Column")
    logo_height = fields.Integer(default=60, string="Logo Height (px)")
    logo_alignment = fields.Selection(
        [
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
        ],
        default="left",
        string="Logo Alignment",
    )
    custom_footer_note = fields.Text(string="Custom Footer/Thank-you Note")
    header_bg_color = fields.Char(default="#1e293b", string="Table Header BG Color")
    header_text_color = fields.Char(default="#ffffff", string="Table Header Text Color")
    label_billed_to = fields.Char(default="Billed To", string="Label: Billed To")
    
    # Stored as JSON array of block names
    block_order = fields.Char(
        help="JSON array defining the display order of sections on the document.",
    )


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('block_order'):
                if vals.get('document_type') == 'quotation':
                    vals['block_order'] = '["header", "client_info", "line_items", "totals", "terms", "footer"]'
                else:
                    vals['block_order'] = '["header", "client_info", "line_items", "totals", "terms", "footer"]'
        return super().create(vals_list)
