from datetime import timedelta

from odoo import api, fields, models

WINDOW_DAYS = 7
RULE_VERSION = "1.0"

FACTOR_WEIGHTS = {
    "f1_coverage": 0.40,
    "f2_timeliness": 0.20,
    "f3_training": 0.15,
    "f4_responsiveness": 0.15,
    "f5_quality": 0.10,
}
FACTOR_LABELS = {
    "f1_coverage": "Workflow coverage",
    "f2_timeliness": "Timeliness",
    "f3_training": "Training & competency currency",
    "f4_responsiveness": "Responsiveness",
    "f5_quality": "Reporting quality",
}


class SecurityAdoptionSnapshot(models.Model):
    """One employee's rolling-window score (docs/deployguard/
    09-adoption-engine.md §3, §6). rule_version is stored on every row so
    a future change to weights/thresholds never silently rewrites
    history -- new versions apply forward only, per spec §6."""

    _name = "security.adoption.snapshot"
    _description = "Adoption: Score Snapshot"
    _order = "window_end desc, id desc"

    employee_id = fields.Many2one("hr.employee", required=True)
    window_start = fields.Date(required=True)
    window_end = fields.Date(required=True)
    computed_at = fields.Datetime(default=fields.Datetime.now, required=True)
    rule_version = fields.Char(default=RULE_VERSION, required=True)

    expected_total = fields.Integer(help="fulfilled + missed items in the window (excused rows are not counted as expected).")
    excused_total = fields.Integer()
    score = fields.Integer(help="Rounded weighted score, 0-100. Not meaningful below Low confidence -- see confidence.")
    confidence = fields.Selection(
        [
            ("insufficient", "Insufficient (< 5)"),
            ("low", "Low (5-14)"),
            ("medium", "Medium (15-39)"),
            ("high", "High (>= 40)"),
        ],
        required=True,
    )
    factor_ids = fields.One2many("security.adoption.score.factor", "snapshot_id", string="Factors")

    @api.model
    def action_compute_all(self, window_days=WINDOW_DAYS):
        """Cron entry point. One snapshot per employee who has at least
        one expected-work item ever materialised -- an employee with zero
        items simply never gets a snapshot (nothing to measure), rather
        than a fabricated zero score."""
        window_end = fields.Date.context_today(self) - timedelta(days=1)
        window_start = window_end - timedelta(days=window_days - 1)
        Item = self.env["security.adoption.expected.work.item"]
        employee_ids = Item.search([]).mapped("employee_id").ids
        for employee_id in employee_ids:
            self._compute_for_employee(employee_id, window_start, window_end)

    def _compute_for_employee(self, employee_id, window_start, window_end):
        Item = self.env["security.adoption.expected.work.item"]
        items = Item.search([
            ("employee_id", "=", employee_id),
            ("period_date", ">=", window_start), ("period_date", "<=", window_end),
        ])
        fulfilled = items.filtered(lambda i: i.state == "fulfilled")
        missed = items.filtered(lambda i: i.state == "missed")
        excused = items.filtered(lambda i: i.state == "excused")
        expected_total = len(fulfilled) + len(missed)

        f1 = (len(fulfilled) / expected_total * 100.0) if expected_total else 0.0
        on_time = fulfilled.filtered(lambda i: i.on_time)
        f2 = (len(on_time) / len(fulfilled) * 100.0) if fulfilled else 0.0
        f3 = self._factor_training_currency(employee_id)
        f4 = self._factor_responsiveness(employee_id, window_start, window_end)
        f5 = self._factor_reporting_quality(employee_id, window_start, window_end)

        raw_values = {
            "f1_coverage": f1, "f2_timeliness": f2, "f3_training": f3,
            "f4_responsiveness": f4, "f5_quality": f5,
        }
        score = round(sum(FACTOR_WEIGHTS[k] * v for k, v in raw_values.items()))

        if expected_total < 5:
            confidence = "insufficient"
        elif expected_total < 15:
            confidence = "low"
        elif expected_total < 40:
            confidence = "medium"
        else:
            confidence = "high"

        snapshot = self.create({
            "employee_id": employee_id, "window_start": window_start, "window_end": window_end,
            "expected_total": expected_total, "excused_total": len(excused),
            "score": score, "confidence": confidence,
        })
        factor_model = self.env["security.adoption.score.factor"]
        for key, raw in raw_values.items():
            factor_model.create({
                "snapshot_id": snapshot.id, "factor_key": key,
                "weight": FACTOR_WEIGHTS[key], "raw_value": raw,
                "weighted_value": FACTOR_WEIGHTS[key] * raw,
            })
        return snapshot

    def _factor_training_currency(self, employee_id):
        """100 minus a 20-point penalty per overdue mandatory-training
        assignment, floored at 0 -- spec §3's "penalty(overdue mandatory
        training, expired required competencies)" without a separate
        competency-expiry model to check yet (documented gap, see
        manifest)."""
        overdue_count = self.env["security.training.assignment"].search_count([
            ("employee_id", "=", employee_id),
            ("state", "!=", "completed"),
            ("due_date", "!=", False),
            ("due_date", "<", fields.Date.context_today(self)),
        ])
        return max(0.0, 100.0 - 20.0 * overdue_count)

    def _factor_responsiveness(self, employee_id, window_start, window_end):
        """Approximates spec §3's "share of items acknowledged/verified
        within SLA" using this employee's own security.work.task
        submissions in the window (the verification-style workflows this
        repo actually has -- site.visit, shift.handover, incident.review
        tasks). No penalty (100) when there's nothing to measure, so a
        thin sample doesn't drag the score down by default; the
        confidence gate is what tells the reader to discount it."""
        Task = self.env["security.work.task"]
        tasks = Task.search([
            ("employee_id", "=", employee_id),
            ("submitted_at", "!=", False),
            ("submitted_at", ">=", fields.Datetime.to_string(window_start)),
            ("submitted_at", "<=", fields.Datetime.to_string(window_end + timedelta(days=1))),
        ])
        if not tasks:
            return 100.0
        on_time = tasks.filtered(lambda t: not t.due_at or t.submitted_at <= t.due_at)
        return len(on_time) / len(tasks) * 100.0

    def _factor_reporting_quality(self, employee_id, window_start, window_end):
        """100 minus the rework rate: security.work.task submissions in
        the window that were ever sent back (reject_count > 0) ÷ total
        submissions. Defaults to 100 (no penalty) with nothing submitted."""
        Task = self.env["security.work.task"]
        tasks = Task.search([
            ("employee_id", "=", employee_id),
            ("submitted_at", "!=", False),
            ("submitted_at", ">=", fields.Datetime.to_string(window_start)),
            ("submitted_at", "<=", fields.Datetime.to_string(window_end + timedelta(days=1))),
        ])
        if not tasks:
            return 100.0
        reworked = tasks.filtered(lambda t: t.reject_count > 0)
        return 100.0 - (len(reworked) / len(tasks) * 100.0)


class SecurityAdoptionScoreFactor(models.Model):
    """One factor's contribution to a snapshot, stored per-snapshot rather
    than folded into a bare number -- spec §3's explanation panel needs
    the per-factor breakdown, not just the total."""

    _name = "security.adoption.score.factor"
    _description = "Adoption: Score Factor"
    _order = "snapshot_id, factor_key"

    snapshot_id = fields.Many2one("security.adoption.snapshot", required=True, ondelete="cascade")
    factor_key = fields.Selection(
        [(k, v) for k, v in FACTOR_LABELS.items()], required=True,
    )
    weight = fields.Float(required=True)
    raw_value = fields.Float(help="Normalised 0-100 value for this factor before weighting.")
    weighted_value = fields.Float()
