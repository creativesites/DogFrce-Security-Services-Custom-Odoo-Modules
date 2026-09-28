from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models

HORIZON_DAYS = 7

TRIGGERS = [
    ("rostered_site_day", "Every rostered site, every day"),
    ("daily", "Every day"),
]


class SecurityWorkResponsibility(models.Model):
    """A recurring duty someone owns, turned into tasks by the **roster**.

    This is the "Roster → Responsibility → Task" link from the V2 brief
    (docs/deployguard/dogforce-roles-and-pipeline.md). For example: "Register
    attendance, owned by the Operations Supervisor, every day, for every site
    that has guards rostered". Materialising reads `security.roster.slot`, so
    a site with no guards rostered that day generates no task, and a site
    added to the roster generates one without anyone configuring it.

    `depends_on_id` chains duties into a pipeline (Register → Confirm →
    Verify). A downstream task is shown as "waiting for <step>" until the
    same site-day's upstream task is done, so each person sees whether they
    can act yet and the manager sees exactly where a site is stuck.

    Unlike security.work.schedule.rule (fixed weekdays, fixed assignee), this
    creates nothing for days the roster doesn't cover.
    """

    _name = "security.work.responsibility"
    _description = "Work Responsibility"
    _order = "sequence, name"

    name = fields.Char(required=True, help="What the duty is, in the words the employee uses. E.g. 'Register attendance'.")
    sequence = fields.Integer(default=10, help="Pipeline order: Register (10) → Confirm (20) → Verify (30).")
    active = fields.Boolean(default=True)
    employee_id = fields.Many2one("hr.employee", required=True, string="Owned by")
    checklist_template_id = fields.Many2one("security.work.checklist.template", required=True, string="Task checklist")
    trigger = fields.Selection(TRIGGERS, required=True, default="rostered_site_day")
    site_ids = fields.Many2many(
        "security.client.site", string="Only these sites",
        help="Leave empty for every rostered site.",
    )
    due_hour = fields.Float(default=10.0, required=True, help="Local time the task is due, e.g. 10.5 = 10:30.")
    depends_on_id = fields.Many2one(
        "security.work.responsibility", string="Comes after",
        help="The step that must be done first for the same site and day (e.g. Confirm comes after Register).",
    )
    why_it_matters = fields.Text(
        help="One or two sentences shown to the employee: why this duty exists and who relies on it.",
    )
    odoo_path = fields.Char(
        string="Where it's done in the ERP",
        help="Same-origin path the desktop opens for 'I know how', e.g. /odoo/action-security_attendance.action_security_attendance_batch",
    )
    guidance_flow_code = fields.Char(help="security_guidance flow that can walk the employee through this duty.")
    task_name_template = fields.Char(
        required=True, default="{responsibility} · {site}",
        help="{responsibility}, {site} and {date} are substituted.",
    )
    last_materialized_date = fields.Date(readonly=True)

    # ------------------------------------------------------------------
    # Materialisation
    # ------------------------------------------------------------------

    @api.model
    def action_materialize_all(self, horizon_days=HORIZON_DAYS):
        """Cron entry point. Idempotent: each (responsibility, site, day) has
        one task, keyed by `source_key`."""
        created = self.env["security.work.task"]
        for resp in self.search([]):
            created |= resp._materialize(horizon_days)
        return created

    def _local_due_at(self, day):
        """`due_hour` is local wall-clock time for the owner; stored UTC."""
        self.ensure_one()
        tz_name = self.employee_id.tz or self.employee_id.user_id.tz or self.env.company.partner_id.tz or "UTC"
        local = pytz.timezone(tz_name).localize(
            datetime.combine(day, time(0, 0)) + timedelta(hours=self.due_hour)
        )
        return local.astimezone(pytz.utc).replace(tzinfo=None)

    def _rostered_site_days(self, date_from, date_to):
        """{(site_id, date)} that have at least one guard rostered."""
        self.ensure_one()
        domain = [
            ("shift_date", ">=", date_from),
            ("shift_date", "<=", date_to),
            ("state", "in", ("assigned", "confirmed")),
            ("employee_id", "!=", False),
        ]
        if self.site_ids:
            domain.append(("site_id", "in", self.site_ids.ids))
        slots = self.env["security.roster.slot"].sudo().search_read(domain, ["site_id", "shift_date"])
        return {(s["site_id"][0], s["shift_date"]) for s in slots if s["site_id"]}

    def _source_key(self, site_id, day):
        return f"resp:{self.id}:{site_id or 0}:{fields.Date.to_string(day)}"

    def _materialize(self, horizon_days=HORIZON_DAYS):
        self.ensure_one()
        Task = self.env["security.work.task"].sudo()
        today = fields.Date.context_today(self)
        last_day = today + timedelta(days=horizon_days - 1)

        if self.trigger == "rostered_site_day":
            wanted = self._rostered_site_days(today, last_day)
        else:
            wanted = {(False, today + timedelta(days=o)) for o in range(horizon_days)}

        keys = {self._source_key(site, day): (site, day) for site, day in wanted}
        existing = Task.with_context(active_test=False).search([("source_key", "in", list(keys))])
        existing_keys = set(existing.mapped("source_key"))

        created = Task.browse()
        sites = {s.id: s for s in self.env["security.client.site"].sudo().browse([s for s, _ in wanted if s])}
        for key, (site_id, day) in keys.items():
            if key in existing_keys:
                continue
            site = sites.get(site_id)
            created |= Task.create({
                "name": self.task_name_template.format(
                    responsibility=self.name,
                    site=site.name if site else "",
                    date=fields.Date.to_string(day),
                ).strip(" ·"),
                "employee_id": self.employee_id.id,
                "site_id": site_id or False,
                "checklist_template_id": self.checklist_template_id.id,
                "due_at": fields.Datetime.to_string(self._local_due_at(day)),
                "responsibility_id": self.id,
                "roster_date": day,
                "source_key": key,
            })

        # The roster changed: a site-day nobody is rostered on any more no
        # longer needs this duty. Only untouched future tasks are withdrawn;
        # anything someone already started is left for a human to decide.
        if self.trigger == "rostered_site_day":
            stale = Task.search([
                ("responsibility_id", "=", self.id),
                ("roster_date", ">=", today),
                ("roster_date", "<=", last_day),
                ("state", "=", "open"),
                ("source_key", "not in", list(keys)),
            ])
            for task in stale:
                task.message_post(body=self.env._("Withdrawn: no guards are rostered at this site on this day any more."))
            stale.write({"state": "cancelled", "cancel_reason": "Roster changed"})

        self.last_materialized_date = today
        return created
