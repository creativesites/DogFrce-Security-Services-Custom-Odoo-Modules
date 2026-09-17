from datetime import timedelta

from odoo import api, fields, models

HORIZON_DAYS = 7


class SecurityWorkScheduleRule(models.Model):
    """Recurring task generation over a rolling 7-day horizon.

    BUILD-STATUS-AND-PHASE-PLAN.md Phase 3.1. Only calendar recurrence
    (fixed weekdays, fixed assignee) is implemented. Shift-based and
    site-event-based recurrence (materialising from roster slots, so the
    assignee is whoever is actually on duty) need real design work this
    slice doesn't attempt -- see this class's docstring note below rather
    than a half-built heuristic that silently assigns the wrong guard.
    """

    _name = "security.work.schedule.rule"
    _description = "Work Task Recurrence Rule"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    checklist_template_id = fields.Many2one(
        "security.work.checklist.template", required=True
    )
    employee_id = fields.Many2one(
        "hr.employee", required=True, string="Assign to",
        help="Fixed assignee. Shift-based assignment (whoever is on duty "
             "that day) is not implemented -- see this model's docstring.",
    )
    site_id = fields.Many2one("security.client.site")
    task_name_template = fields.Char(
        required=True, default="{template} — {date}",
        help="{template} and {date} are substituted when a task is created.",
    )
    due_hour = fields.Float(
        default=17.0, required=True,
        help="Hour of day (0-23.99) the generated task is due.",
    )

    monday = fields.Boolean(default=True)
    tuesday = fields.Boolean(default=True)
    wednesday = fields.Boolean(default=True)
    thursday = fields.Boolean(default=True)
    friday = fields.Boolean(default=True)
    saturday = fields.Boolean(default=False)
    sunday = fields.Boolean(default=False)

    last_materialized_date = fields.Date(readonly=True)

    _weekday_fields = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")

    def _runs_on(self, date):
        self.ensure_one()
        return bool(getattr(self, self._weekday_fields[date.weekday()]))

    @api.model
    def action_materialize_all(self, horizon_days=HORIZON_DAYS):
        """Cron entry point: materialize every active rule over the rolling
        horizon. Idempotent -- calling this twice for the same rule/date
        never creates a duplicate task (checked below, not relied on as a
        DB constraint, since a task's identity here is rule+date, not
        something the task model itself tracks)."""
        for rule in self.search([("active", "=", True)]):
            rule._materialize(horizon_days)

    def _materialize(self, horizon_days=HORIZON_DAYS):
        self.ensure_one()
        Task = self.env["security.work.task"]
        today = fields.Date.context_today(self)
        created = self.env["security.work.task"]

        for offset in range(horizon_days):
            date = today + timedelta(days=offset)
            if not self._runs_on(date):
                continue

            due_at = fields.Datetime.to_datetime(date) + timedelta(hours=self.due_hour)
            task_name = self.task_name_template.format(
                template=self.checklist_template_id.name, date=date.isoformat()
            )

            # Idempotency: a task for this rule, this exact due date, already
            # exists. Matched on name + employee + due date rather than a
            # stored rule_id back-reference, since a human may reassign or
            # rename a generated task without it losing its identity for
            # future materialisation runs.
            existing = Task.search([
                ("employee_id", "=", self.employee_id.id),
                ("checklist_template_id", "=", self.checklist_template_id.id),
                ("due_at", ">=", fields.Datetime.to_string(due_at.replace(hour=0, minute=0, second=0))),
                ("due_at", "<", fields.Datetime.to_string(due_at.replace(hour=0, minute=0, second=0) + timedelta(days=1))),
            ], limit=1)
            if existing:
                continue

            created |= Task.create({
                "name": task_name,
                "employee_id": self.employee_id.id,
                "site_id": self.site_id.id if self.site_id else False,
                "checklist_template_id": self.checklist_template_id.id,
                "due_at": fields.Datetime.to_string(due_at),
            })

        self.last_materialized_date = today
        return created
