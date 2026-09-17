from odoo import fields, models


class SecurityExceptionEscalationPolicy(models.Model):
    """Two-level escalation timing (docs/deployguard/BUILD-STATUS-AND-
    PHASE-PLAN.md Phase 6.3). `use_working_calendar` computes elapsed time
    via resource.calendar.get_work_hours_count -- a real, existing Odoo
    API -- against the company's calendar, rather than a hand-rolled
    business-hours clock. Without it, elapsed time is plain wall-clock
    minutes (appropriate for e.g. a roster gap, which doesn't stop
    mattering outside office hours)."""

    _name = "security.exception.escalation.policy"
    _description = "Exception Escalation Policy"
    _order = "name"

    name = fields.Char(required=True)
    use_working_calendar = fields.Boolean(
        default=False,
        help="Measure delay in working hours against the company's resource.calendar instead of wall-clock minutes.",
    )
    level1_delay_minutes = fields.Integer(required=True, default=15)
    level1_group_id = fields.Many2one("res.groups", required=True)
    level2_delay_minutes = fields.Integer(required=True, default=60)
    level2_group_id = fields.Many2one("res.groups", required=True)

    def _elapsed_minutes(self, since, until=None):
        """Minutes elapsed between `since` and `until` (default: now),
        in working time if use_working_calendar, else wall-clock."""
        self.ensure_one()
        until = until or fields.Datetime.now()
        if not self.use_working_calendar:
            return (until - since).total_seconds() / 60.0

        calendar = self.env.company.resource_calendar_id
        if not calendar:
            return (until - since).total_seconds() / 60.0
        return calendar.get_work_hours_count(since, until) * 60.0
