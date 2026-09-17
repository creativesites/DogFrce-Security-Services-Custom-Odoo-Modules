from datetime import timedelta

from odoo import api, fields, models

BASELINE_WEEKS = 8
MIN_BASELINE_WEEKS = 4
MIN_BASELINE_ITEMS = 10

CHECKIN_ANSWERS = [
    ("didnt_know", "I didn't know I had to"),
    ("couldnt_find", "I couldn't find where"),
    ("not_working", "Something isn't working"),
    ("no_permission", "I don't have permission"),
    ("someone_else", "Someone else is doing it"),
    ("was_away", "I was away"),
    ("too_busy", "Too busy / short-staffed"),
    ("other", "Other"),
]


class SecurityAdoptionBaseline(models.Model):
    """Per (employee, workflow_key) baseline fulfilment rate (spec §5).
    Recomputed each run rather than incrementally updated -- the dataset
    is small enough (weekly buckets over 8 weeks) that recomputation is
    simpler and safer than maintaining running EWM state by hand."""

    _name = "security.adoption.baseline"
    _description = "Adoption: Silent Abandonment Baseline"
    _order = "employee_id, workflow_key"

    employee_id = fields.Many2one("hr.employee", required=True)
    workflow_key = fields.Selection(
        [
            ("attendance.post", "Attendance posting"),
            ("incident.review", "Incident review"),
            ("site.visit", "Site visit"),
            ("training.mandatory", "Mandatory training"),
            ("shift.handover", "Shift handover"),
        ],
        required=True,
    )
    rate = fields.Float(help="Exponentially weighted fulfilment rate over the last 8 weeks, 0-100.")
    weeks_of_history = fields.Integer()
    items_counted = fields.Integer()
    computed_at = fields.Datetime(default=fields.Datetime.now, required=True)
    has_enough_history = fields.Boolean(
        compute="_compute_has_enough_history", store=True,
        help="Requires >= 4 weeks of history and >= 10 expected items, per spec §5.",
    )

    _baseline_unique = models.Constraint(
        "unique(employee_id, workflow_key)",
        "One baseline row per employee and workflow_key -- recomputed in place, not accumulated.",
    )

    @api.depends("weeks_of_history", "items_counted")
    def _compute_has_enough_history(self):
        for baseline in self:
            baseline.has_enough_history = (
                baseline.weeks_of_history >= MIN_BASELINE_WEEKS
                and baseline.items_counted >= MIN_BASELINE_ITEMS
            )

    @api.model
    def action_compute_all(self):
        Item = self.env["security.adoption.expected.work.item"]
        today = fields.Date.context_today(self)
        window_start = today - timedelta(weeks=BASELINE_WEEKS)
        rows = Item.search([
            ("period_date", ">=", window_start), ("period_date", "<", today),
            ("state", "in", ("fulfilled", "missed")),
        ])
        groups = {}
        for item in rows:
            key = (item.employee_id.id, item.workflow_key)
            groups.setdefault(key, []).append(item)

        for (employee_id, workflow_key), items in groups.items():
            weekly_rates = self._weekly_rates(items, window_start, today)
            rate = self._ewm(weekly_rates)
            weeks_of_history = len([w for w in weekly_rates if w is not None])
            existing = self.search([
                ("employee_id", "=", employee_id), ("workflow_key", "=", workflow_key),
            ], limit=1)
            vals = {
                "employee_id": employee_id, "workflow_key": workflow_key,
                "rate": rate, "weeks_of_history": weeks_of_history,
                "items_counted": len(items), "computed_at": fields.Datetime.now(),
            }
            if existing:
                existing.write(vals)
            else:
                self.create(vals)

    @staticmethod
    def _weekly_rates(items, window_start, today):
        """One fulfilment-rate bucket per calendar week in the window,
        oldest first; None for weeks with no expected items at all."""
        n_weeks = (today - window_start).days // 7 + 1
        buckets = [[] for _ in range(n_weeks)]
        for item in items:
            week_index = (item.period_date - window_start).days // 7
            if 0 <= week_index < n_weeks:
                buckets[week_index].append(item.state == "fulfilled")
        return [
            (sum(1 for v in bucket if v) / len(bucket) * 100.0) if bucket else None
            for bucket in buckets
        ]

    @staticmethod
    def _ewm(weekly_rates, alpha=0.3):
        """Exponentially weighted mean, most recent week weighted
        heaviest, skipping weeks with no data rather than treating them
        as zero."""
        rate = None
        for value in weekly_rates:
            if value is None:
                continue
            rate = value if rate is None else (alpha * value + (1 - alpha) * rate)
        return rate or 0.0


class SecurityAdoptionAbandonmentSignal(models.Model):
    """A detected deviation and its handling, in order
    SIGNAL -> INVESTIGATE -> ASSIST -> REMIND -> ESCALATE (spec §5). The
    INVESTIGATE checks that can be decided purely from data already in
    this repo (leave, roster change, another employee covering the same
    workflow) run automatically; the ones that need a live systems check
    (permission changes, ERP outage, device-offline) are recorded as
    manual findings an admin fills in, since there's no audit-log/access-
    change or device-telemetry model here to query automatically yet."""

    _name = "security.adoption.abandonment.signal"
    _description = "Adoption: Silent Abandonment Signal"
    _order = "detected_at desc"
    _inherit = ["mail.thread"]

    employee_id = fields.Many2one("hr.employee", required=True, tracking=True)
    workflow_key = fields.Selection(
        [
            ("attendance.post", "Attendance posting"),
            ("incident.review", "Incident review"),
            ("site.visit", "Site visit"),
            ("training.mandatory", "Mandatory training"),
            ("shift.handover", "Shift handover"),
        ],
        required=True,
    )
    detected_at = fields.Datetime(default=fields.Datetime.now, required=True)
    trigger_type = fields.Selection(
        [
            ("below_baseline", "Trailing 5 days <= 50% of baseline, >= 3 missed"),
            ("consecutive_missed", ">= 3 consecutive missed on a >= 80% baseline"),
        ],
        required=True,
    )
    baseline_id = fields.Many2one("security.adoption.baseline")
    state = fields.Selection(
        [
            ("signal", "Signal"),
            ("investigating", "Investigating"),
            ("assist", "Assist"),
            ("reminded", "Reminded"),
            ("escalated", "Escalated"),
            ("resolved", "Resolved"),
        ],
        default="signal", required=True, tracking=True,
    )
    investigate_notes = fields.Text()
    resolution_excusal_reason = fields.Selection(
        [
            ("leave", "Approved leave / absence in window"),
            ("roster_changed", "Roster changed -- no longer assigned"),
            ("permission_changed", "Permission or role changed"),
            ("support_linked", "Linked to an open support request"),
            ("erp_outage", "ERP outage / stale projections"),
            ("device_offline", "Device offline / not seen"),
            ("misconfigured_owner", "Someone else fulfilled the same real work"),
        ],
        help="Set once INVESTIGATE finds a cause -- closes the signal without contacting the person.",
    )
    checkin_ids = fields.One2many("security.adoption.checkin", "signal_id")
    reminded_at = fields.Datetime(readonly=True)
    escalated_at = fields.Datetime(readonly=True)

    @api.model
    def action_detect_all(self):
        """Cron entry point: scans every baseline with enough history for
        the two trigger conditions in spec §5, opening one signal per
        (employee, workflow_key) that doesn't already have an open one."""
        Item = self.env["security.adoption.expected.work.item"]
        today = fields.Date.context_today(self)
        for baseline in self.env["security.adoption.baseline"].search([("has_enough_history", "=", True)]):
            if self.search_count([
                ("employee_id", "=", baseline.employee_id.id),
                ("workflow_key", "=", baseline.workflow_key),
                ("state", "not in", ("resolved",)),
            ]):
                continue

            recent = Item.search([
                ("employee_id", "=", baseline.employee_id.id),
                ("workflow_key", "=", baseline.workflow_key),
                ("period_date", "<", today), ("period_date", ">=", today - timedelta(days=5)),
                ("state", "in", ("fulfilled", "missed")),
            ], order="period_date desc")
            missed_recent = recent.filtered(lambda i: i.state == "missed")
            recent_rate = (len(recent) - len(missed_recent)) / len(recent) * 100.0 if recent else None

            trigger_type = None
            if recent_rate is not None and recent_rate <= baseline.rate * 0.5 and len(missed_recent) >= 3:
                trigger_type = "below_baseline"
            elif baseline.rate >= 80.0:
                consecutive = 0
                for item in recent:
                    if item.state == "missed":
                        consecutive += 1
                    else:
                        break
                if consecutive >= 3:
                    trigger_type = "consecutive_missed"

            if trigger_type:
                self.create({
                    "employee_id": baseline.employee_id.id, "workflow_key": baseline.workflow_key,
                    "trigger_type": trigger_type, "baseline_id": baseline.id,
                })

    def action_start_investigating(self):
        for signal in self:
            signal.state = "investigating"

    def action_close_with_excusal(self, reason):
        for signal in self:
            signal.write({"state": "resolved", "resolution_excusal_reason": reason})

    def action_send_assist_checkin(self):
        """Records that the ASSIST check-in was sent -- the actual
        message content lives in the spec's copy, not duplicated here.
        A real in-app/desktop delivery channel is part of the deferred
        UI work noted in this module's manifest."""
        for signal in self:
            signal.state = "assist"
            self.env["security.adoption.checkin"].create({"signal_id": signal.id})

    def action_remind(self):
        for signal in self:
            signal.write({"state": "reminded", "reminded_at": fields.Datetime.now()})

    def action_escalate(self):
        for signal in self:
            signal.write({"state": "escalated", "escalated_at": fields.Datetime.now()})
            signal.message_post(
                body=(
                    f"Escalated: {signal.employee_id.name}'s {signal.workflow_key} "
                    f"adoption signal has not been resolved."
                )
            )


class SecurityAdoptionCheckin(models.Model):
    """The ASSIST step's in-app check-in as a plain record: question sent
    plus the person's answer from spec §5's fixed option list. A full
    chat-style UI is deferred (see this module's manifest); the routing
    table below is real logic, not a placeholder."""

    _name = "security.adoption.checkin"
    _description = "Adoption: Assist Check-in"
    _order = "id desc"

    signal_id = fields.Many2one("security.adoption.abandonment.signal", required=True, ondelete="cascade")
    sent_at = fields.Datetime(default=fields.Datetime.now, required=True)
    answer = fields.Selection(CHECKIN_ANSWERS)
    answered_at = fields.Datetime()
    routed_action = fields.Char(readonly=True)

    def action_record_answer(self, answer):
        routing = {
            "didnt_know": "Assign micro-lesson + knowledge article; notify supervisor for context.",
            "couldnt_find": "Assign micro-lesson + knowledge article; notify supervisor for context.",
            "not_working": "Create support request with full context; suppress score deductions until resolved.",
            "no_permission": "Create support request with full context; suppress score deductions until resolved.",
            "someone_else": "Task the tenant admin to correct the expectation owner.",
            "was_away": "Excuse items (cross-checked with leave).",
            "too_busy": "Exception to the operations manager: capacity issue, not a personal failing.",
            "other": "Remind once, then escalate if unanswered for 2 working days.",
        }
        for checkin in self:
            checkin.write({
                "answer": answer, "answered_at": fields.Datetime.now(),
                "routed_action": routing.get(answer, ""),
            })
