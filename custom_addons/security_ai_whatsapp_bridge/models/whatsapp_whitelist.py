# -*- coding: utf-8 -*-
from odoo import fields, models, api


class SecurityWhatsAppWhitelist(models.Model):
    _name = "security.whatsapp.whitelist"
    _description = "WhatsApp Authorized Sender Whitelist"
    _order = "role, name, id"

    name = fields.Char(string="Contact / Label", required=True)
    phone_number = fields.Char(string="Phone Number", required=True, index=True)
    employee_id = fields.Many2one("hr.employee", string="Matched Employee", index=True)
    partner_id = fields.Many2one("res.partner", string="Matched Contact", index=True)
    role = fields.Selection(
        [
            ("supervisor", "Supervisor / Field Officer"),
            ("manager", "Operations Manager"),
            ("executive", "Executive / Owner"),
            ("guard", "Security Guard"),
        ],
        string="Assigned Role",
        default="supervisor",
        required=True,
    )
    active = fields.Boolean(string="Active", default=True)
    can_submit_attendance = fields.Boolean(string="Can Submit Attendance", default=True)
    can_flag_awol = fields.Boolean(string="Can Flag AWOL", default=True)
    can_query_kpis = fields.Boolean(string="Can Query Executive KPIs", default=True)
    can_report_incidents = fields.Boolean(string="Can Report Incidents", default=True)

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id:
            if not self.name or self.name == "New Contact":
                self.name = self.employee_id.name
            if not self.phone_number:
                self.phone_number = self.employee_id.mobile_phone or self.employee_id.work_phone or ""

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        if self.partner_id:
            if not self.name or self.name == "New Contact":
                self.name = self.partner_id.name
            if not self.phone_number:
                p_mobile = getattr(self.partner_id, "mobile", False) or ""
                self.phone_number = p_mobile or self.partner_id.phone or ""
