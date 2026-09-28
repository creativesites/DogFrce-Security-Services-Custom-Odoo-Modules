from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models
from odoo.exceptions import AccessError

DONE_STATES = ("submitted", "verified")
OPEN_STATES = ("open", "in_progress")

VIEWER_GROUPS = {
    "is_supervisor": "security_work.group_work_supervisor",
    "is_manager": "security_base.group_security_manager",
    "is_owner": "security_base.group_security_owner",
}


class SecurityWorkTask(models.Model):
    """Roster-driven fields and the "Today" APIs the desktop renders.

    The desktop never decides what is due, overdue, blocked or done. It asks
    `get_my_today()` / `get_team_today()` and renders the answer
    (desktop/RECONCILIATION.md §E, "thin client")."""

    _inherit = "security.work.task"

    responsibility_id = fields.Many2one("security.work.responsibility", ondelete="set null", index=True, readonly=True)
    source_key = fields.Char(readonly=True, copy=False, index=True, help="Idempotency key for generated tasks.")
    roster_date = fields.Date(readonly=True, index=True, help="The rostered day this task is for.")
    why_it_matters = fields.Text(related="responsibility_id.why_it_matters")
    guidance_flow_code = fields.Char(related="responsibility_id.guidance_flow_code")
    odoo_path = fields.Char(related="responsibility_id.odoo_path")
    readiness = fields.Selection(
        [("ready", "Ready"), ("waiting", "Waiting for an earlier step")],
        compute="_compute_readiness",
    )
    waiting_on = fields.Char(compute="_compute_readiness", help="Which earlier step, and who owns it.")

    _source_key_unique = models.Constraint(
        "unique(source_key)",
        "A generated task already exists for this duty, site and day.",
    )

    # ------------------------------------------------------------------
    # Pipeline readiness
    # ------------------------------------------------------------------

    def _upstream_task(self):
        """The same site-day's task for the step this one comes after."""
        self.ensure_one()
        upstream = self.responsibility_id.depends_on_id
        if not upstream or not self.roster_date:
            return self.browse()
        return self.sudo().search([
            ("source_key", "=", upstream._source_key(self.site_id.id, self.roster_date)),
        ], limit=1)

    @api.depends("responsibility_id", "roster_date", "site_id")
    def _compute_readiness(self):
        for task in self:
            task.readiness = "ready"
            task.waiting_on = False
            upstream_resp = task.responsibility_id.depends_on_id
            if not upstream_resp or task.state not in OPEN_STATES:
                continue
            upstream = task._upstream_task()
            if not upstream or upstream.state not in DONE_STATES:
                task.readiness = "waiting"
                who = upstream.employee_id.name if upstream else upstream_resp.employee_id.name
                task.waiting_on = self.env._("%(step)s (%(who)s)", step=upstream_resp.name, who=who or "")

    # ------------------------------------------------------------------
    # Desktop APIs
    # ------------------------------------------------------------------

    @api.model
    def get_viewer_context(self):
        """Which role-gated screens the signed-in employee may see. Roles come
        from Odoo groups only, never from names or logins."""
        return {key: self.env.user.has_group(xmlid) for key, xmlid in VIEWER_GROUPS.items()}

    @api.model
    def _today_bounds(self):
        """UTC datetimes spanning the viewer's local today."""
        tz = pytz.timezone(self.env.user.tz or self.env.company.partner_id.tz or "UTC")
        today = fields.Date.context_today(self)
        start = tz.localize(datetime.combine(today, time.min)).astimezone(pytz.utc).replace(tzinfo=None)
        return today, start, start + timedelta(days=1)

    def _today_card(self):
        """One task as the desktop's Today card. Extension point: modules add
        keys (training, guidance) by overriding and calling super()."""
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "due_at": fields.Datetime.to_string(self.due_at) if self.due_at else False,
            "is_overdue": self.is_overdue,
            "site": self.site_id.name or False,
            "responsibility": self.responsibility_id.name or False,
            "why_it_matters": self.why_it_matters or False,
            "readiness": self.readiness,
            "waiting_on": self.waiting_on or False,
            "odoo_path": self.odoo_path or False,
            "guidance_flow_code": self.guidance_flow_code or False,
            "checklist": bool(self.checklist_template_id),
        }

    @api.model
    def get_my_today(self):
        """What the signed-in employee needs to do: today's tasks, anything
        overdue from before, and anything they have started. Ordered: overdue
        first, then by due time."""
        employee = self.env.user.employee_ids[:1]
        if not employee:
            return {"employee": False, "tasks": []}
        _today, start, end = self._today_bounds()
        tasks = self.search([
            ("employee_id", "=", employee.id),
            "|", "|",
            "&", ("due_at", ">=", start), ("due_at", "<", end),
            "&", ("due_at", "<", start), ("state", "in", OPEN_STATES),
            ("state", "=", "in_progress"),
        ])
        tasks = tasks.filtered(lambda t: t.state != "cancelled").sorted(
            key=lambda t: (not t.is_overdue, t.due_at or datetime.max, t.id)
        )
        return {"employee": {"id": employee.id, "name": employee.name}, "tasks": [t._today_card() for t in tasks]}

    @api.model
    def get_team_today(self):
        """The manager's "where is it stuck?" view for today.

        `pipeline`: one row per rostered site, one cell per pipeline step
        (responsibility, in order), each cell the real task, so a gap is
        visible as exactly which step, at which site, owned by whom.
        `people`: expected / done / overdue / couldn't-do per person.
        Every count carries the task ids behind it."""
        if not self.env.user.has_group("security_work.group_work_supervisor"):
            raise AccessError(self.env._("Team Today is for supervisors, managers and the owner."))
        today, start, end = self._today_bounds()
        Task = self.sudo()
        tasks = Task.search([
            "|",
            "&", ("due_at", ">=", start), ("due_at", "<", end),
            "&", ("roster_date", "=", today), ("responsibility_id", "!=", False),
            ("state", "!=", "cancelled"),
        ])

        steps = tasks.mapped("responsibility_id").sorted(lambda r: (r.sequence, r.id))
        sites = {}
        for task in tasks.filtered("responsibility_id"):
            row = sites.setdefault(task.site_id.id or 0, {
                "site": task.site_id.name or self.env._("No site"), "site_id": task.site_id.id or False, "cells": {},
            })
            row["cells"][task.responsibility_id.id] = {
                "task_id": task.id,
                "state": task.state,
                "is_overdue": task.is_overdue,
                "readiness": task.readiness,
                "employee": task.employee_id.name,
            }

        people = {}
        for task in tasks:
            p = people.setdefault(task.employee_id.id, {
                "employee": task.employee_id.name, "employee_id": task.employee_id.id,
                "expected": [], "done": [], "overdue": [], "could_not_complete": [], "waiting": [],
            })
            p["expected"].append(task.id)
            if task.state in DONE_STATES:
                p["done"].append(task.id)
            if task.is_overdue:
                p["overdue"].append(task.id)
            if task.state == "could_not_complete":
                p["could_not_complete"].append(task.id)
            if task.readiness == "waiting":
                p["waiting"].append(task.id)

        return {
            "date": fields.Date.to_string(today),
            "steps": [{"id": s.id, "name": s.name, "owner": s.employee_id.name} for s in steps],
            "pipeline": sorted(sites.values(), key=lambda r: r["site"]),
            "people": sorted(people.values(), key=lambda p: p["employee"] or ""),
        }
