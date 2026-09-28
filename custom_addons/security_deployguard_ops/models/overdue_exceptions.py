from odoo import api, fields, models

DONE_OR_CLOSED = ("submitted", "verified", "cancelled")


class SecurityNotification(models.Model):
    _inherit = "security.notification"

    notification_type = fields.Selection(
        selection_add=[("task_overdue", "Work overdue")],
        ondelete={"task_overdue": "set default"},
    )


class SecurityExceptionRule(models.Model):
    _inherit = "security.exception.rule"

    notification_type = fields.Selection(
        selection_add=[("task_overdue", "Work overdue")],
        ondelete={"task_overdue": "cascade"},
    )


class SecurityWorkTask(models.Model):
    """Overdue work becomes an operational exception: what happened, the
    evidence (the task itself), who owns it, and the next action. When the
    work gets done the alert is dismissed, and the exception resolves on the
    exception engine's next sync."""

    _inherit = "security.work.task"

    @api.model
    def action_sweep_overdue(self):
        overdue = super().action_sweep_overdue()
        Notification = self.env["security.notification"].sudo()
        supervisors = self.env.ref("security_work.group_work_supervisor").sudo().all_user_ids
        for task in overdue:
            if Notification.search_count([
                ("notification_type", "=", "task_overdue"), ("related_model", "=", "security.work.task"),
                ("related_id", "=", task.id), ("state", "!=", "dismissed"),
            ]):
                continue
            owner = task.employee_id.name or self.env._("Unassigned")
            due = fields.Datetime.context_timestamp(task, task.due_at).strftime("%H:%M on %d %b") if task.due_at else ""
            body = [self.env._("%(task)s was due %(due)s and isn't done. Owner: %(owner)s.", task=task.name, due=due, owner=owner)]
            if task.why_it_matters:
                body.append(self.env._("Why it matters: %s", task.why_it_matters))
            if task.readiness == "waiting":
                body.append(self.env._("It is still waiting for %s, so start there.", task.waiting_on))
            body.append(self.env._("Next: ask %s whether something is blocking them. If it can't be done, they can mark it 'couldn't complete' with a reason.", owner))
            Notification.create({
                "title": self.env._("Overdue: %s", task.name),
                "body": "\n".join(body),
                "notification_type": "task_overdue",
                "severity": "warning",
                "site_id": task.site_id.id or False,
                "partner_id": task.site_id.partner_id.id or False,
                "related_model": "security.work.task",
                "related_id": task.id,
                "recipient_ids": [(6, 0, (supervisors | task.employee_id.user_id).ids)],
            })
        return overdue

    def write(self, vals):
        res = super().write(vals)
        if vals.get("state") in DONE_OR_CLOSED:
            self.env["security.notification"].sudo().search([
                ("notification_type", "=", "task_overdue"), ("related_model", "=", "security.work.task"),
                ("related_id", "in", self.ids), ("state", "!=", "dismissed"),
            ]).write({"state": "dismissed"})
        return res
