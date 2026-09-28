from odoo import models


class SecurityGuidanceSession(models.Model):
    """Record checks for the attendance guided flows. Each one reads the real
    posting sheet for the session's site and day. "Done" in guidance means
    the ERP says so."""

    _inherit = "security.guidance.session"

    def _attendance_stage(self):
        self.ensure_one()
        if not self.context_site_id or not self.context_date:
            return "none"
        stage, _batch = self.env["security.work.task"]._attendance_stage(self.context_site_id.id, self.context_date)
        return stage

    def _guidance_check_attendance_sheet_generated(self):
        return self._attendance_stage() != "none"

    def _guidance_check_attendance_all_marked(self):
        return self._attendance_stage() in ("marked", "reviewed", "locked")

    def _guidance_check_attendance_reviewed(self):
        return self._attendance_stage() in ("reviewed", "locked")

    def _guidance_check_attendance_locked(self):
        return self._attendance_stage() == "locked"

    def _advance(self, ui_state):
        # Keep the task in step with the records as the employee works.
        if self.task_id:
            self.task_id._sync_attendance_pipeline()
        return super()._advance(ui_state)
