import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SecurityWhatsAppBridge(models.AbstractModel):
    _name = "security.whatsapp.bridge"
    _description = "Conversational WhatsApp and Roster Bridge Model"

    @api.model
    def mark_guard_awol(self, guard_name):
        """
        Locates a guard by name, finds their active roster assignment today, and marks them AWOL.
        """
        _logger.info("WhatsApp Bridge | Attempting to mark guard AWOL: %s", guard_name)

        # Fuzzy search for employee matching name
        employee = self.env["hr.employee"].sudo().search([
            "|",
            ("name", "ilike", guard_name),
            ("work_email", "ilike", guard_name),
        ], limit=1)

        if not employee:
            return _("Guard matching '%s' could not be found in active employee roster.") % guard_name

        today = fields.Date.today()

        # Search for their active roster assignment for today
        slot = self.env["security.roster.slot"].sudo().search([
            ("employee_id", "=", employee.id),
            ("shift_date", "=", today),
        ], limit=1)

        if not slot:
            return _("Guard '%s' has no active roster slots scheduled for today (%s).") % (employee.name, today)

        # Check if attendance record already exists
        attendance = self.env["security.attendance"].sudo().search([
            ("employee_id", "=", employee.id),
            ("shift_date", "=", today),
        ], limit=1)

        if not attendance:
            # Create a new AWOL attendance record
            attendance = self.env["security.attendance"].sudo().create({
                "employee_id": employee.id,
                "site_id": slot.site_id.id,
                "post_id": slot.post_id.id,
                "shift_date": today,
                "state": "absent",
                "attendance_status": "awol",
            })
        else:
            # Update existing to AWOL
            attendance.sudo().write({
                "state": "absent",
                "attendance_status": "awol",
            })

        # Broadcast the AWOL event on the central intelligence bus
        payload = {
            "guard_name": employee.name,
            "site_name": slot.site_id.name,
            "post_name": slot.post_id.name,
        }

        self.env["security.event.log"].register_event(
            name="attendance.missed",
            source_model="security.attendance",
            source_id=attendance.id,
            payload=payload,
        )

        return _("Guard '%s' at Site '%s' has been flagged as AWOL today. Central intelligence alerts dispatched.") % (employee.name, slot.site_id.name)

    @api.model
    def get_roster_status_summary(self):
        """
        Retrieves real-time aggregated roster posting statistics for the conversational AI parser.
        """
        today = fields.Date.today()
        slots = self.env["security.roster.slot"].sudo().search([("shift_date", "=", today)])
        attendance = self.env["security.attendance"].sudo().search([("shift_date", "=", today)])

        total = len(slots)
        present = len(attendance.filtered(lambda a: a.actual_check_in and not a.actual_check_out))
        awol = len(attendance.filtered(lambda a: a.state == "absent" or a.attendance_status == "awol"))

        return {
            "total": total,
            "present": present,
            "awol": awol,
        }
