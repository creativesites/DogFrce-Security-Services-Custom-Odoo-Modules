"""
Extend security.attendance.batch to send push notifications
when supervisors submit a batch (action_review).
"""
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class SecurityAttendanceBatchNotify(models.Model):
    _inherit = "security.attendance.batch"

    def action_review(self):
        result = super().action_review()
        for batch in self:
            try:
                from ..controllers.notifications import send_expo_push, get_manager_tokens
                tokens = get_manager_tokens(self.env)
                if not tokens:
                    continue
                site = batch.site_id
                date_str = str(batch.attendance_date) if batch.attendance_date else ""
                records = batch.attendance_record_ids
                total = len(records)
                present = len(records.filtered(lambda r: r.manual_presence == "present"))
                awol = len(records.filtered(lambda r: r.manual_presence == "awol"))
                rate = round(present / total * 100, 1) if total else 0.0
                awol_note = f" · {awol} AWOL" if awol else ""
                send_expo_push(
                    tokens,
                    f"Attendance Submitted — {site.name}",
                    f"{date_str} · {present}/{total} present ({rate}%){awol_note}",
                    {
                        "type": "batch_reviewed",
                        "batch_id": batch.id,
                        "site_id": site.id if site else None,
                    },
                )
            except Exception as exc:
                _logger.warning("Push notification error for batch %s: %s", batch.id, exc)
        return result
