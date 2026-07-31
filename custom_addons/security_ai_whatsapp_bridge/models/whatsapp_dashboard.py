# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, time, timedelta


class SecurityWhatsAppDashboard(models.TransientModel):
    _name = "security.whatsapp.dashboard"
    _description = "WhatsApp Command & Control Room Dashboard Data Service"

    @api.model
    def get_dashboard_data(self):
        """Fetch real-time operational KPI metrics, charts, and activity streams for OWL Dashboard."""
        today_start = datetime.combine(datetime.today(), time.min)
        today_end = datetime.combine(datetime.today(), time.max)

        Log = self.env["security.whatsapp.message.log"]
        Config = self.env["security.whatsapp.config"]
        Whitelist = self.env["security.whatsapp.whitelist"]

        config = Config.search([], limit=1)
        bridge_status = config.connection_status if config else "disconnected"
        allowed_numbers_count = Whitelist.search_count([("active", "=", True)])

        today_domain = [("timestamp", ">=", today_start), ("timestamp", "<=", today_end)]
        today_logs = Log.search(today_domain, order="timestamp desc")

        today_messages_count = len(today_logs)
        inbound_count = sum(1 for log in today_logs if log.direction == "inbound")
        outbound_count = sum(1 for log in today_logs if log.direction == "outbound")

        attendance_logged = sum(
            1 for log in today_logs if log.parsed_intent in ("site_attendance", "lateness") and log.execution_status == "success"
        )
        awol_flagged = sum(1 for log in today_logs if log.parsed_intent == "awol" and log.execution_status == "success")
        incidents_reported = sum(
            1 for log in today_logs if log.parsed_intent == "incident_report" and log.execution_status == "success"
        )

        ai_processed = sum(
            1 for log in today_logs if log.parsed_intent not in ("unauthorized", "unrelated_chitchat") and log.execution_status in ("success", "ai_processed")
        )
        ai_resolution_rate = round((ai_processed / today_messages_count * 100), 1) if today_messages_count > 0 else 100.0

        # Recent 10 activity records
        recent_activity = []
        for log in today_logs[:10]:
            recent_activity.append({
                "id": log.id,
                "timestamp": log.timestamp.strftime("%H:%M:%S") if log.timestamp else "",
                "sender_phone": log.sender_phone or "",
                "sender_name": log.sender_name or log.employee_id.name or log.partner_id.name or "Unknown Sender",
                "employee_name": log.employee_id.name if log.employee_id else "",
                "direction": log.direction,
                "raw_body": log.raw_body or "",
                "reply_body": log.reply_body or "",
                "parsed_intent": log.parsed_intent or "general",
                "execution_status": log.execution_status or "success",
            })

        # Hourly distribution array (0 to 23 hours)
        hourly_counts = [0] * 24
        for log in today_logs:
            if log.timestamp:
                hourly_counts[log.timestamp.hour] += 1

        return {
            "bridge_status": bridge_status,
            "allowed_numbers_count": allowed_numbers_count,
            "today_messages_count": today_messages_count,
            "inbound_count": inbound_count,
            "outbound_count": outbound_count,
            "attendance_logged": attendance_logged,
            "awol_flagged": awol_flagged,
            "incidents_reported": incidents_reported,
            "ai_resolution_rate": ai_resolution_rate,
            "recent_activity": recent_activity,
            "hourly_counts": hourly_counts,
        }

    @api.model
    def get_chat_workspace_threads(self, filter_type="all"):
        """Fetch conversation threads grouped by sender phone number for the Live Control Room workspace."""
        Log = self.env["security.whatsapp.message.log"]
        
        domain = []
        if filter_type == "exceptions":
            domain = [("parsed_intent", "in", ["awol", "incident_report", "unauthorized"])]
        elif filter_type == "supervisors":
            domain = [("employee_id", "!=", False)]

        all_logs = Log.search(domain, order="timestamp desc", limit=200)

        threads_dict = {}
        for log in all_logs:
            phone = log.sender_phone
            if not phone:
                continue
            if phone not in threads_dict:
                sender_display = log.sender_name or (log.employee_id.name if log.employee_id else (log.partner_id.name if log.partner_id else phone))
                threads_dict[phone] = {
                    "phone": phone,
                    "sender_name": sender_display,
                    "employee_name": log.employee_id.name if log.employee_id else "",
                    "partner_name": log.partner_id.name if log.partner_id else "",
                    "last_message": log.raw_body or "",
                    "last_timestamp": log.timestamp.strftime("%d %b %H:%M") if log.timestamp else "",
                    "last_intent": log.parsed_intent or "general",
                    "unread_count": 0,
                    "messages": [],
                }
            
            threads_dict[phone]["messages"].append({
                "id": log.id,
                "timestamp": log.timestamp.strftime("%H:%M") if log.timestamp else "",
                "direction": log.direction,
                "raw_body": log.raw_body or "",
                "reply_body": log.reply_body or "",
                "parsed_intent": log.parsed_intent or "",
                "execution_status": log.execution_status or "",
            })

        # Return list sorted by latest message
        threads_list = list(threads_dict.values())
        for thread in threads_list:
            thread["messages"].reverse() # Chronological order inside thread
        return threads_list

    @api.model
    def send_manual_chat_reply(self, recipient_phone, message_text):
        """Send a manual response from the Live Control Room workspace via the WhatsApp Bridge."""
        if not recipient_phone or not message_text or not message_text.strip():
            return {"success": False, "error": "Missing recipient phone or message text."}
        
        Bridge = self.env["security.whatsapp.bridge"]
        try:
            res = Bridge._send_whatsapp_reply(recipient_phone, message_text.strip())
        except Exception as error:
            return {"success": False, "error": str(error)}

        if isinstance(res, dict) and res.get("success") is False:
            return {"success": False, "error": res.get("error", "WhatsApp service rejected the reply.")}
        
        # Log outbound message
        self.env["security.whatsapp.message.log"].create({
            "sender_phone": recipient_phone,
            "direction": "outbound",
            "raw_body": f"[Manual Control Room Reply]: {message_text.strip()}",
            "reply_body": message_text.strip(),
            "parsed_intent": "manual_reply",
            "execution_status": "success",
        })
        return {"success": True}
