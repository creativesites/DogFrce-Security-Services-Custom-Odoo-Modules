# -*- coding: utf-8 -*-
import re
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SecurityWhatsAppReplyWizard(models.TransientModel):
    _name = "security.whatsapp.reply.wizard"
    _description = "WhatsApp Control Room Dispatcher Reply Wizard"

    recipient_phone = fields.Char(string="Recipient Phone Number", required=True, index=True)
    sender_name = fields.Char(string="Contact / Guard Name", readonly=True)
    employee_id = fields.Many2one("hr.employee", string="Matched Employee", readonly=True)
    
    template_type = fields.Selection(
        [
            ("custom", "Custom Freeform Message"),
            ("ack_incident", "🚨 Acknowledge Incident & Dispatch Patrol"),
            ("confirm_attendance", "✅ Confirm Attendance Check-In"),
            ("request_location", "📍 Request Live Location / Post Check"),
            ("awol_warning", "⚠️ Issue AWOL Absence Warning"),
            ("shift_reminder", "⏱️ Shift Start Reminder"),
        ],
        string="Quick Dispatch Template",
        default="custom",
    )
    
    message_body = fields.Text(string="Message Content", required=True)

    @api.onchange("template_type")
    def _onchange_template_type(self):
        guard_name = self.sender_name or (self.employee_id.name if self.employee_id else "Officer")
        if self.template_type == "ack_incident":
            self.message_body = (
                f"🚨 *DogForce Control Room Dispatch*\n\n"
                f"Dear {guard_name}, your incident report has been received and logged in Central Intelligence.\n"
                f"A supervisor/patrol unit has been alerted."
            )
        elif self.template_type == "confirm_attendance":
            self.message_body = (
                f"✅ *DogForce Control Room*\n\n"
                f"Attendance confirmed for {guard_name}. Your shift posting is active and synchronized with payroll."
            )
        elif self.template_type == "request_location":
            self.message_body = (
                f"📍 *DogForce Control Room Check*\n\n"
                f"Attention {guard_name}: Please send your current post status or share your live GPS location."
            )
        elif self.template_type == "awol_warning":
            self.message_body = (
                f"⚠️ *DogForce Control Room Alert*\n\n"
                f"Officer {guard_name}: You have been flagged for unexcused absence (AWOL) on today's roster.\n"
                f"Reply immediately or contact your field supervisor."
            )
        elif self.template_type == "shift_reminder":
            self.message_body = (
                f"⏱️ *DogForce Shift Reminder*\n\n"
                f"Attention {guard_name}: Your scheduled shift is starting shortly. Please report to your assigned post and send your check-in command."
            )

    def action_send_whatsapp_message(self):
        self.ensure_one()
        clean_text = (self.message_body or "").strip()
        clean_phone = (self.recipient_phone or "").strip()

        if not clean_text:
            raise UserError(_("Message body cannot be empty."))
        if not clean_phone:
            raise UserError(_("Recipient phone number is missing."))

        Bridge = self.env["security.whatsapp.bridge"].sudo()
        
        # Dispatch outbound message via backend Node service / Baileys bridge
        res = Bridge._send_whatsapp_reply(clean_phone, clean_text)
        
        # Log outbound message in audit log
        self.env["security.whatsapp.message.log"].sudo().create({
            "sender_phone": clean_phone,
            "sender_name": self.sender_name,
            "employee_id": self.employee_id.id if self.employee_id else False,
            "direction": "outbound",
            "raw_body": f"[Control Room Manual Dispatch]: {clean_text}",
            "reply_body": clean_text,
            "parsed_intent": "manual_dispatch",
            "execution_status": "success",
            "is_authorized": True,
            "timestamp": fields.Datetime.now(),
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("WhatsApp Message Sent"),
                'message': _("Message dispatched successfully to %s") % (self.sender_name or clean_phone),
                'type': 'success',
                'sticky': False,
            }
        }
