from datetime import timedelta

from odoo import api, fields, models

EXCUSAL_REASONS = [
    ("leave", "Approved leave"),
    ("absence", "Attendance shows absent"),
    ("no_shift", "No shift scheduled"),
    ("reassigned", "Reassigned per roster"),
    ("site_inactive", "Site inactive"),
    ("system_fault", "System fault (retroactive)"),
    ("suppressed_by_admin", "Suppressed by admin"),
]


class SecurityAdoptionExpectedWorkItem(models.Model):
    """One resolved expectation for one employee, one period
    (docs/deployguard/09-adoption-engine.md §2). Materialised for the
    day/week that has just closed (T-1 by server date) -- never for a
    future period, since "expected, not yet due" for a day that hasn't
    happened yet would require predicting shift-assignment resolution,
    which this repo's own security.work.schedule.rule explicitly declines
    to guess at (see that model's docstring). By the time this module
    looks at a period, the answer (fulfilled/missed/excused) is already a
    fact, not a projection."""

    _name = "security.adoption.expected.work.item"
    _description = "Adoption: Expected Work Item"
    _order = "period_date desc, id desc"

    definition_id = fields.Many2one(
        "security.adoption.expected.work.definition", required=True, ondelete="cascade"
    )
    workflow_key = fields.Selection(related="definition_id.workflow_key", store=True)
    employee_id = fields.Many2one("hr.employee", required=True)
    site_id = fields.Many2one("security.client.site")
    period_date = fields.Date(required=True, help="The shift-day or week-start this item covers.")
    due_at = fields.Datetime()

    state = fields.Selection(
        [
            ("fulfilled", "Fulfilled"),
            ("missed", "Missed"),
            ("excused", "Excused"),
        ],
        required=True,
    )
    excusal_reason = fields.Selection(EXCUSAL_REASONS)
    fulfilled_at = fields.Datetime()
    on_time = fields.Boolean(help="Fulfilled at or before due_at. Feeds F2 timeliness.")

    source_model = fields.Char(help="Model of the record that proves fulfilment, e.g. security.attendance.batch.")
    source_res_id = fields.Integer(help="Id (in source_model) of the record that proves fulfilment.")

    # Cadence-based workflows (attendance.post, site.visit, shift.handover)
    # are one-per-(employee, site, period): the constraint below covers
    # them. Per-instance workflows (incident.review, training.mandatory)
    # are one-per-source-record instead, and are deduplicated by their
    # materialisers checking (source_model, source_res_id) directly --
    # see those methods -- rather than by this constraint, since two
    # incidents due the same reviewer on the same day are two different
    # expected items, not one.
    _item_unique = models.Constraint(
        "unique(definition_id, employee_id, site_id, period_date, source_res_id)",
        "This expected work item has already been materialised for this employee, site and period.",
    )

    # -- Materialisation ------------------------------------------------

    @api.model
    def action_materialize_all(self):
        """Cron entry point. Idempotent per (definition, employee, site,
        period_date) via the unique constraint above -- each per-workflow
        materialiser checks for an existing row before creating one."""
        for definition in self.env["security.adoption.expected.work.definition"].search([("active", "=", True)]):
            method = getattr(self, f"_materialize_{definition.workflow_key.replace('.', '_')}", None)
            if method:
                method(definition)

    def _excusal_for_employee_date(self, employee, target_date):
        """Shared excusal check: approved leave covering target_date.
        Workflow-specific excusals (no_shift, site_inactive...) are
        checked by each materialiser, which has the roster/site context
        this shared check doesn't."""
        on_leave = self.env["security.leave.request"].search([
            ("employee_id", "=", employee.id),
            ("state", "=", "approved"),
            ("date_from", "<=", target_date),
            ("date_to", ">=", target_date),
        ], limit=1)
        return "leave" if on_leave else False

    def _create_if_missing(self, definition, employee, site, period_date, **vals):
        domain = [
            ("definition_id", "=", definition.id),
            ("employee_id", "=", employee.id),
            ("site_id", "=", site.id if site else False),
            ("period_date", "=", period_date),
            ("source_res_id", "=", vals.get("source_res_id") or 0),
        ]
        existing = self.search(domain, limit=1)
        if existing:
            return existing
        vals.update({
            "definition_id": definition.id,
            "employee_id": employee.id,
            "site_id": site.id if site else False,
            "period_date": period_date,
        })
        return self.create(vals)

    def _materialize_attendance_post(self, definition):
        target_date = fields.Date.context_today(self) - timedelta(days=1)
        sites = self.env["security.client.site"].search([
            ("active", "=", True), ("supervisor_id", "!=", False),
        ])
        for site in sites:
            employee = site.supervisor_id
            if self.search_count([
                ("definition_id", "=", definition.id), ("employee_id", "=", employee.id),
                ("site_id", "=", site.id), ("period_date", "=", target_date),
            ]):
                continue

            has_shift = self.env["security.roster.slot"].search_count([
                ("site_id", "=", site.id), ("shift_date", "=", target_date),
                ("state", "!=", "cancelled"), ("employee_id", "!=", False),
            ])
            if not has_shift:
                self._create_if_missing(definition, employee, site, target_date,
                                         state="excused", excusal_reason="no_shift")
                continue

            leave_reason = self._excusal_for_employee_date(employee, target_date)
            if leave_reason:
                self._create_if_missing(definition, employee, site, target_date,
                                         state="excused", excusal_reason=leave_reason)
                continue

            batch = self.env["security.attendance.batch"].search([
                ("site_id", "=", site.id), ("attendance_date", "=", target_date),
                ("state", "in", ("reviewed", "locked")),
            ], limit=1)
            if batch:
                self._create_if_missing(
                    definition, employee, site, target_date,
                    state="fulfilled", fulfilled_at=batch.write_date, on_time=True,
                    source_model="security.attendance.batch", source_res_id=batch.id,
                )
            else:
                self._create_if_missing(definition, employee, site, target_date, state="missed")

    def _materialize_site_visit(self, definition):
        self._materialize_weekly_work_task(definition, "site.visit")

    def _materialize_shift_handover(self, definition):
        self._materialize_weekly_work_task(definition, "shift.handover", weekly=False)

    def _materialize_weekly_work_task(self, definition, template_code, weekly=True):
        """Shared logic for the two workflow_keys whose source of truth is
        a security.work.task against a fixed checklist template code.
        site.visit is weekly (only materialised the day the week just
        closed, i.e. Monday); shift.handover is daily, per spec's V1
        template phase-in."""
        today = fields.Date.context_today(self)
        if weekly and today.weekday() != 0:  # only run the weekly check on Mondays
            return
        target_date = today - timedelta(days=7 if weekly else 1)
        period_start = target_date - timedelta(days=target_date.weekday()) if weekly else target_date
        period_end = period_start + timedelta(days=6) if weekly else target_date

        sites = self.env["security.client.site"].search([
            ("active", "=", True), ("supervisor_id", "!=", False),
        ])
        for site in sites:
            employee = site.supervisor_id
            if self.search_count([
                ("definition_id", "=", definition.id), ("employee_id", "=", employee.id),
                ("site_id", "=", site.id), ("period_date", "=", period_start),
            ]):
                continue

            leave_reason = self._excusal_for_employee_date(employee, period_end)
            if leave_reason:
                self._create_if_missing(definition, employee, site, period_start,
                                         state="excused", excusal_reason=leave_reason)
                continue

            task = self.env["security.work.task"].search([
                ("site_id", "=", site.id), ("employee_id", "=", employee.id),
                ("checklist_template_id.code", "=", template_code),
                ("due_at", ">=", fields.Datetime.to_string(period_start)),
                ("due_at", "<", fields.Datetime.to_string(period_end + timedelta(days=1))),
                ("state", "in", ("submitted", "verified")),
            ], limit=1)
            if task:
                self._create_if_missing(
                    definition, employee, site, period_start,
                    state="fulfilled",
                    fulfilled_at=task.submitted_at,
                    on_time=bool(task.due_at and task.submitted_at and task.submitted_at <= task.due_at),
                    source_model="security.work.task", source_res_id=task.id,
                )
            else:
                self._create_if_missing(definition, employee, site, period_start, state="missed")

    def _incident_reviewer_employee(self):
        """No field on security.incident names a reviewer -- see this
        module's manifest description. Falls back to the first active
        member of security_base.group_security_manager as the notional
        owner of an unreviewed incident until it's actually approved, at
        which point the item is attributed to the real approver."""
        group = self.env.ref("security_base.group_security_manager", raise_if_not_found=False)
        if not group:
            return self.env["hr.employee"]
        manager_users = self.env["res.users"].search([("group_ids", "in", group.id)], limit=1)
        if not manager_users:
            return self.env["hr.employee"]
        return self.env["hr.employee"].search([("user_id", "=", manager_users.id)], limit=1)

    def _materialize_incident_review(self, definition):
        sla_cutoff = fields.Date.context_today(self) - timedelta(days=1)
        incidents = self.env["security.incident"].search([
            ("incident_date", "<=", sla_cutoff),
        ])
        for incident in incidents:
            if self.search_count([
                ("definition_id", "=", definition.id),
                ("source_model", "=", "security.incident"), ("source_res_id", "=", incident.id),
            ]):
                continue

            if incident.state in ("approved", "resolved") and incident.approved_by_id:
                reviewer = self.env["hr.employee"].search(
                    [("user_id", "=", incident.approved_by_id.id)], limit=1
                )
                reviewer = reviewer or self._incident_reviewer_employee()
                if not reviewer:
                    continue
                # No site_id: security.incident isn't tied to a site, and
                # this workflow is tenant/ops-level, not site-level -- see
                # spec §9 ("Ops officer / manager").
                self._create_if_missing(
                    definition, reviewer, False, incident.incident_date,
                    state="fulfilled", fulfilled_at=incident.write_date,
                    on_time=True,
                    source_model="security.incident", source_res_id=incident.id,
                )
            else:
                reviewer = self._incident_reviewer_employee()
                if not reviewer:
                    continue
                self._create_if_missing(
                    definition, reviewer, False, incident.incident_date,
                    state="missed",
                    source_model="security.incident", source_res_id=incident.id,
                )

    def _materialize_training_mandatory(self, definition):
        overdue_cutoff = fields.Date.context_today(self) - timedelta(days=1)
        assignments = self.env["security.training.assignment"].search([
            ("due_date", "!=", False), ("due_date", "<=", overdue_cutoff),
        ])
        for assignment in assignments:
            employee = assignment.employee_id
            if self.search_count([
                ("definition_id", "=", definition.id),
                ("source_model", "=", "security.training.assignment"),
                ("source_res_id", "=", assignment.id),
            ]):
                continue

            if assignment.state == "completed":
                self._create_if_missing(
                    definition, employee, False, assignment.due_date,
                    state="fulfilled",
                    fulfilled_at=assignment.completed_at,
                    on_time=bool(
                        assignment.completed_at
                        and fields.Datetime.to_datetime(assignment.completed_at).date() <= assignment.due_date
                    ),
                    source_model="security.training.assignment", source_res_id=assignment.id,
                )
            else:
                leave_reason = self._excusal_for_employee_date(employee, assignment.due_date)
                if leave_reason:
                    self._create_if_missing(definition, employee, False, assignment.due_date,
                                             state="excused", excusal_reason=leave_reason)
                else:
                    self._create_if_missing(
                        definition, employee, False, assignment.due_date, state="missed",
                        source_model="security.training.assignment", source_res_id=assignment.id,
                    )
