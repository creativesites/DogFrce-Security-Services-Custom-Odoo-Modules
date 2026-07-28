from odoo import api, fields, models


class SecurityPayslipTemplate(models.Model):
    _name = "security.payslip.template"
    _description = "Payslip Visual Template"
    _order = "name"

    name = fields.Char(required=True, help="Name of the template (e.g., Standard Guard Payslip)")
    base_layout = fields.Selection(
        [
            ("modern", "Modern"),
            ("corporate", "Corporate"),
            ("minimalist", "Minimalist"),
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
    show_ytd = fields.Boolean(default=True, string="Show Year-to-Date Totals")
    show_leave_balances = fields.Boolean(default=True, string="Show Leave Balances")
    show_attendance_metrics = fields.Boolean(default=True, string="Show Attendance Metrics")
    show_admin_signature = fields.Boolean(default=True, string="Show Admin Signature")
    show_guard_signature = fields.Boolean(default=True, string="Show Guard Signature")
    announcement_text = fields.Text(string="Announcement Text", help="A custom message to display at the bottom of the payslip.")
    header_bg_color = fields.Char(default="#1e293b", string="Table Header BG Color")
    header_text_color = fields.Char(default="#ffffff", string="Table Header Text Color")
    label_payslip = fields.Char(default="Payslip", string="Label: Payslip")
    
    # Stored as JSON array of block names
    block_order = fields.Char(
        default='["header", "employee_info", "attendance", "earnings_deductions_split", "totals", "footer"]',
        help="JSON array defining the display order of sections on the payslip.",
    )

