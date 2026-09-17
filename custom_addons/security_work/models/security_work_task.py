from odoo import api, fields, models
from odoo.exceptions import UserError


class SecurityWorkTask(models.Model):
    _name = "security.work.task"
    _description = "Work Task"
    _inherit = ["mail.thread", "mail.activity.mixin", "security.bus.subscriber"]
    _order = "due_at, id"

    # Auto-completion (docs/deployguard/BUILD-STATUS-AND-PHASE-PLAN.md Phase
    # 3.2): security_attendance emits these on the internal Intelligence Bus
    # (security_attendance/models/security_attendance.py's action_review/
    # action_lock). Only attendance is wired today -- security_discipline
    # does not yet emit any incident lifecycle events, so incident-triggered
    # auto-completion is not attempted here rather than built against
    # nothing real.
    _bus_events = ["attendance.batch.reviewed", "attendance.batch.locked"]

    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    employee_id = fields.Many2one("hr.employee", required=True, tracking=True, string="Assigned to")
    site_id = fields.Many2one("security.client.site")
    due_at = fields.Datetime(tracking=True)
    is_overdue = fields.Boolean(compute="_compute_is_overdue", search="_search_is_overdue")

    state = fields.Selection(
        [
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("submitted", "Submitted"),
            ("verified", "Verified"),
            ("could_not_complete", "Could Not Complete"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="open",
        required=True,
        tracking=True,
    )

    cnc_reason = fields.Selection(
        [
            ("blocked_permission", "Blocked / no permission"),
            ("system_error", "System error"),
            ("information_missing", "Information missing"),
            ("site_access", "Could not access site"),
            ("time", "Ran out of time"),
            ("other", "Other"),
        ],
        string="Could-not-complete reason",
    )
    cnc_note = fields.Char(string="Could-not-complete details")
    reject_reason = fields.Char()
    cancel_reason = fields.Char()

    checklist_template_id = fields.Many2one("security.work.checklist.template")
    response_ids = fields.One2many("security.work.checklist.response", "task_id", string="Checklist responses")

    created_by_id = fields.Many2one("res.users", default=lambda self: self.env.user, readonly=True)
    submitted_at = fields.Datetime(readonly=True)
    verified_by_id = fields.Many2one("res.users", readonly=True)
    verified_at = fields.Datetime(readonly=True)

    note = fields.Text()

    overdue_flagged_at = fields.Datetime(
        readonly=True,
        help="Set the first time the overdue sweep notices this task, so it "
             "is only flagged once rather than every run.",
    )

    @api.depends("due_at", "state")
    def _compute_is_overdue(self):
        now = fields.Datetime.now()
        open_states = ("open", "in_progress")
        for task in self:
            task.is_overdue = bool(task.due_at and task.due_at < now and task.state in open_states)

    def _search_is_overdue(self, operator, value):
        now = fields.Datetime.now()
        open_states = ["open", "in_progress"]
        is_overdue_domain = ["&", ("due_at", "<", now), ("state", "in", open_states)]
        matches_true = (operator == "=" and value) or (operator == "!=" and not value)
        if matches_true:
            return is_overdue_domain
        return ["|", ("due_at", ">=", now), ("state", "not in", open_states)]

    @api.model_create_multi
    def create(self, vals_list):
        tasks = super().create(vals_list)
        for task in tasks:
            if task.checklist_template_id:
                task._sync_checklist_responses()
        return tasks

    def write(self, vals):
        result = super().write(vals)
        if "checklist_template_id" in vals:
            for task in self:
                task._sync_checklist_responses()
        return result

    def _sync_checklist_responses(self):
        """Create a blank response row for every item in the template that
        doesn't already have one. Never removes existing responses (a
        template swap shouldn't destroy answers already given)."""
        for task in self:
            if not task.checklist_template_id:
                continue
            existing_item_ids = set(task.response_ids.mapped("item_def_id").ids)
            missing_items = task.checklist_template_id.item_ids.filtered(lambda i: i.id not in existing_item_ids)
            for item in missing_items:
                self.env["security.work.checklist.response"].create({
                    "task_id": task.id,
                    "item_def_id": item.id,
                })

    def _check_transition(self, allowed_from):
        for task in self:
            if task.state not in allowed_from:
                raise UserError(
                    f"Can't do that from state '{task.state}' — task {task.name} "
                    f"needs to be in one of: {', '.join(allowed_from)}."
                )

    def action_start(self):
        self._check_transition(["open"])
        self.write({"state": "in_progress"})

    def action_submit(self):
        self._check_transition(["open", "in_progress"])
        missing_required = self.response_ids.filtered(
            lambda r: r.item_def_id.required
            and r.item_type in ("text", "number")
            and not (r.value_text or r.value_number)
        )
        if missing_required:
            raise UserError(
                self.env._("Answer all required checklist items before submitting: %s")
                % ", ".join(missing_required.mapped("label"))
            )
        self.write({"state": "submitted", "submitted_at": fields.Datetime.now()})

    def action_verify(self):
        self._check_transition(["submitted"])
        self.write({
            "state": "verified",
            "verified_by_id": self.env.user.id,
            "verified_at": fields.Datetime.now(),
        })

    def action_reject(self, reason=None):
        self._check_transition(["submitted"])
        self.write({"state": "in_progress", "reject_reason": reason or False})

    def action_could_not_complete(self, reason, note=None):
        self._check_transition(["open", "in_progress"])
        if not reason:
            raise UserError(self.env._("A reason is required to mark work as could-not-complete."))
        self.write({"state": "could_not_complete", "cnc_reason": reason, "cnc_note": note or False})

    def action_cancel(self, reason=None):
        self._check_transition(["open", "in_progress", "could_not_complete"])
        self.write({"state": "cancelled", "cancel_reason": reason or False})

    def action_reopen(self):
        """Manual escape hatch for could_not_complete/cancelled — not part
        of the documented lifecycle, but supervisors need a way to put a
        task back to work without recreating it from scratch."""
        self._check_transition(["could_not_complete", "cancelled"])
        self.write({"state": "open"})

    # -- Auto-completion (security.bus.subscriber) --------------------------

    # -- Overdue sweep (BUILD-STATUS-AND-PHASE-PLAN.md Phase 3.6) -----------

    @api.model
    def action_sweep_overdue(self):
        """Cron entry point. Flags newly-overdue tasks once each -- a
        chatter note plus a mail.activity for the assignee -- rather than
        renotifying every run. This is a detection hook for Phase 6's
        exception engine to consume later, not a full escalation ladder;
        posting to the task's own chatter/activity is real signal today,
        not a placeholder."""
        now = fields.Datetime.now()
        overdue = self.sudo().search([
            ("due_at", "<", now),
            ("state", "in", ("open", "in_progress")),
            ("overdue_flagged_at", "=", False),
        ])
        for task in overdue:
            task.message_post(
                body=f"Overdue: this task was due {task.due_at} and has not been completed."
            )
            task.activity_schedule(
                "mail.mail_activity_data_todo",
                summary="Overdue work task",
                note=f"'{task.name}' was due {task.due_at}.",
                user_id=task.employee_id.user_id.id or self.env.user.id,
            )
            task.overdue_flagged_at = fields.Datetime.now()
        return overdue

    # -- Auto-completion (security.bus.subscriber) --------------------------

    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """Auto-verifies attendance.post tasks matching the reviewed/locked
        batch's site and date. The matched fact is recorded as a chatter
        note on the task (BUILD-STATUS-AND-PHASE-PLAN.md Phase 3.2's
        "matched fact recorded as evidence").

        Deliberately narrow matching: only tasks still open/submittable
        (open, in_progress, submitted) using the attendance.post template,
        for the same site and due date as the batch. A task already
        verified, rejected or cancelled is left alone -- auto-completion
        only ever moves a task forward, never overrides a human decision.
        """
        site_id = payload.get("site_id")
        attendance_date = payload.get("attendance_date")
        if not site_id or not attendance_date:
            return

        domain = [
            ("site_id", "=", site_id),
            ("checklist_template_id.code", "=", "attendance.post"),
            ("state", "in", ("open", "in_progress", "submitted")),
            ("due_at", ">=", f"{attendance_date} 00:00:00"),
            ("due_at", "<=", f"{attendance_date} 23:59:59"),
        ]
        # sudo(): this runs as whoever reviewed/locked the attendance batch
        # (often Front Desk, per the review gate in security_attendance),
        # who has no reason to hold write access on another employee's task.
        # The match itself, not the triggering user, is the authority here.
        matching_tasks = self.sudo().search(domain)
        for task in matching_tasks:
            task.message_post(
                body=(
                    f"Auto-completed: matched attendance batch #{source_id} "
                    f"({event_name}) for this site and date."
                )
            )
            task.write({
                "state": "verified",
                "verified_by_id": self.env.ref("base.user_root").id,
                "verified_at": fields.Datetime.now(),
            })
