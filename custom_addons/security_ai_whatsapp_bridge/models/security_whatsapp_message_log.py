# -*- coding: utf-8 -*-
from odoo import fields, models


class SecurityWhatsAppMessageLog(models.Model):
    _name = "security.whatsapp.message.log"
    _description = "WhatsApp AI Message History & Audit Log"
    _order = "timestamp desc, id desc"

    sender_phone = fields.Char(string="Sender Phone Number", index=True, required=True)
    sender_name = fields.Char(string="Sender Display Name")
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
