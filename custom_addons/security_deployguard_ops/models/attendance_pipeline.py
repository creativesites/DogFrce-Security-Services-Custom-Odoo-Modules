from odoo import api, fields, models

# How far a site-day's attendance has got. Each pipeline step completes at
# one of these; reaching a later one also verifies the earlier steps, because
# the next person has accepted their work.
STAGES = [
    ("marked", "Registered: every rostered guard marked"),
    ("reviewed", "Confirmed by Admin"),
    ("locked", "Verified by HR (sent to payroll)"),
]
STAGE_RANK = {"none": 0, "generated": 1, "marked": 2, "reviewed": 3, "locked": 4}


class SecurityWorkResponsibility(models.Model):
    _inherit = "security.work.responsibility"

    completes_at_stage = fields.Selection(
        STAGES, string="Done when attendance is",
        help="Leave empty for duties that aren't about attendance. DeployGuard completes the task from the "
             "posting sheet's real state; nobody has to claim it.",
    )


class SecurityWorkTask(models.Model):
    _inherit = "security.work.task"

    _bus_events = ["attendance.batch.reviewed", "attendance.batch.locked", "attendance.batch.marked"]

    @api.model
    def _attendance_stage(self, site_id, day):
        """Where a site-day's posting sheet is, read from the records."""
        batch = self.env["security.attendance.batch"].sudo().search([
            ("site_id", "=", site_id), ("attendance_date", "=", day), ("state", "!=", "cancelled"),
        ], order="id desc", limit=1)
        if not batch:
            return "none", batch
        if batch.state in ("reviewed", "locked"):
            return batch.state, batch
        records = batch.attendance_record_ids
        if records and not records.filtered(lambda r: r.manual_presence == "not_marked"):
            return "marked", batch
        return ("generated" if records else "none"), batch

    def _sync_attendance_pipeline(self):
        """Move attendance tasks forward to match the posting sheet. Only ever
        forward, and never over a human decision (could-not-complete,
        rejected, cancelled)."""
        tasks = self.sudo().filtered(
            lambda t: t.responsibility_id.completes_at_stage and t.site_id and t.roster_date
            and t.state in ("open", "in_progress", "submitted")
        )
        for task in tasks:
            stage, batch = self._attendance_stage(task.site_id.id, task.roster_date)
            own = STAGE_RANK[task.responsibility_id.completes_at_stage]
            reached = STAGE_RANK[stage]
            if reached < own:
                continue
            evidence = self.env._(
                "Posting sheet %(batch)s for %(site)s on %(date)s is now: %(stage)s (%(n)s guards).",
                batch=batch.name or batch.id, site=task.site_id.name, date=task.roster_date,
                stage=dict(STAGES).get(stage, stage), n=len(batch.attendance_record_ids),
            )
            if reached > own or stage == "locked":
                task.message_post(body=self.env._("Verified by the next step. ") + evidence)
                task.write({
                    "state": "verified",
                    "submitted_at": task.submitted_at or fields.Datetime.now(),
                    "verified_at": fields.Datetime.now(),
                    "verified_by_id": batch.reviewed_by_id.id if stage == "reviewed" else self.env.ref("base.user_root").id,
                })
            elif task.state != "submitted":
                task.message_post(body=self.env._("Done: DeployGuard checked the records. ") + evidence)
                task.write({"state": "submitted", "submitted_at": fields.Datetime.now()})

    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        # The legacy attendance.post auto-verify (security_work) was written
        # for reviewed/locked only. Don't let the new "marked" event trigger it.
        if event_name != "attendance.batch.marked":
            super()._handle_bus_event(event_name, source_model, source_id, payload)
        site_id, day = payload.get("site_id"), payload.get("attendance_date")
        if site_id and day:
            self.sudo().search([
                ("site_id", "=", site_id), ("roster_date", "=", day),
                ("responsibility_id.completes_at_stage", "!=", False),
            ])._sync_attendance_pipeline()

    @api.model
    def action_sync_attendance_pipeline(self):
        """Cron safety net for any change the bus didn't carry (e.g. a batch
        edited directly)."""
        today = fields.Date.context_today(self)
        self.sudo().search([
            ("responsibility_id.completes_at_stage", "!=", False),
            ("roster_date", ">=", fields.Date.subtract(today, days=3)),
            ("state", "in", ("open", "in_progress", "submitted")),
        ])._sync_attendance_pipeline()

    @api.model
    def get_my_today(self):
        employee = self.env.user.employee_ids[:1]
        if employee:
            self.sudo().search([
                ("employee_id", "=", employee.id),
                ("responsibility_id.completes_at_stage", "!=", False),
                ("state", "in", ("open", "in_progress", "submitted")),
            ])._sync_attendance_pipeline()
        return super().get_my_today()

    @api.model
    def get_team_today(self):
        self.action_sync_attendance_pipeline()
        return super().get_team_today()
