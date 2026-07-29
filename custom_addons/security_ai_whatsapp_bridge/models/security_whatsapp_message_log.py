# -*- coding: utf-8 -*-
import re
from odoo import fields, models, api, _


class SecurityWhatsAppMessageLog(models.Model):
    _name = "security.whatsapp.message.log"
    _description = "WhatsApp AI Message History & Audit Log"
    _order = "timestamp desc, id desc"

    sender_phone = fields.Char(string="Sender Phone Number", index=True, required=True)
    sender_name = fields.Char(string="Sender Display Name")
    conversation_id = fields.Char(
        string="Conversation ID / Thread Phone",
        compute="_compute_conversation_id",
        store=True,
        index=True,
        help="Cleaned digits representation for grouping chat threads"
    )
    employee_id = fields.Many2one("hr.employee", string="Matched Employee", index=True)
    partner_id = fields.Many2one("res.partner", string="Matched Contact", index=True)
    site_id = fields.Many2one("security.client.site", string="Related Client Site", index=True)
    
    direction = fields.Selection(
        [
            ("inbound", "Inbound"),
            ("outbound", "Outbound"),
        ],
        string="Direction",
        required=True,
        default="inbound",
        index=True,
    )
    message_type = fields.Selection(
        [
            ("text", "Text"),
            ("image", "Image"),
            ("document", "Document"),
            ("audio", "Voice Note / Audio"),
            ("location", "GPS Location"),
            ("system", "System Notification"),
        ],
        string="Message Type",
        default="text",
        required=True,
    )
    media_url = fields.Char(string="Media / Attachment URL")
    raw_body = fields.Text(string="Raw Message Body", required=True)
    parsed_intent = fields.Char(
        string="Recognized Intent",
        help="Recognized operational intent, e.g. site_attendance, lateness, awol, owner_stats, manager_stats, help, unrelated_chitchat, unauthorized",
        index=True,
    )
    execution_status = fields.Selection(
        [
            ("success", "Success"),
            ("ignored", "Ignored / Unrelated"),
            ("unauthorized", "Unauthorized Number"),
            ("error", "Error"),
        ],
        string="Execution Status",
        default="success",
        index=True,
    )
    reply_body = fields.Text(string="Reply Sent")
    is_authorized = fields.Boolean(string="Is Sender Authorized", default=True)
    timestamp = fields.Datetime(string="Timestamp", default=fields.Datetime.now, index=True, required=True)

    @api.depends("sender_phone")
    def _compute_conversation_id(self):
        for rec in self:
            digits = re.sub(r"[^\d]", "", rec.sender_phone or "")
            rec.conversation_id = digits or rec.sender_phone or "unknown"

    def action_open_reply_wizard(self):
        self.ensure_one()
        return {
            "name": _("Compose WhatsApp Reply — %s") % (self.sender_name or self.sender_phone),
            "type": "ir.actions.act_window",
            "res_model": "security.whatsapp.reply.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_recipient_phone": self.sender_phone,
                "default_sender_name": self.sender_name or (self.employee_id.name if self.employee_id else self.sender_phone),
                "default_employee_id": self.employee_id.id if self.employee_id else False,
            }
        }
