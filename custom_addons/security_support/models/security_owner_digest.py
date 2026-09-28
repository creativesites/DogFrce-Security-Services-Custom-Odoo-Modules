from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError

OWNER_GROUPS = ("security_base.group_security_owner", "security_base.group_security_manager")

CLOSED_TASK_STATES = ("submitted", "verified")
LIVE_TASK_STATES = ("open", "in_progress", "submitted", "verified", "could_not_complete", "rejected")


class SecurityOwnerDigest(models.AbstractModel):
    """The owner/GM overview (docs/deployguard/31-dogforce-rollout.md,
    "What is happening? What is going wrong? Where?").

    Every tile is computed from real records, and every tile carries the
    `drill` domain of exactly those records, so any number on the screen can
    be opened and checked. Nothing here is estimated, modelled or AI-generated.
    Optional sources (exceptions, training, attendance) are included only
    when their module is installed."""

    _name = "security.owner.digest"
    _description = "Owner Overview"

    def _check_viewer(self):
        if not any(self.env.user.has_group(g) for g in OWNER_GROUPS):
            raise AccessError(self.env._("The owner overview is only available to managers and the owner."))

    @api.model
    def _day_bounds(self, day):
        start = datetime.combine(day, time.min)
        return fields.Datetime.to_string(start), fields.Datetime.to_string(start + timedelta(days=1))

    @api.model
    def _tile(self, key, label, value, detail, model, domain, fields_, tone="neutral", total=None, trend=None):
        return {
            "key": key,
            "label": label,
            "value": value,
            "total": total,
            "detail": detail,
            "tone": tone,
            "trend": trend,
            "drill": {"model": model, "domain": domain, "fields": fields_, "title": label},
        }

    @api.model
    def get_owner_overview(self):
        self._check_viewer()
        # Counting runs with elevated rights after the group check above; the
        # drill-downs the desktop then opens run as the viewer, whose manager
        # and owner groups imply work supervision.
        Task = self.env["security.work.task"].sudo()
        today = fields.Date.context_today(self)
        start, end = self._day_bounds(today)
        task_fields = ["name", "employee_id", "site_id", "due_at", "state"]
        tiles = []

        due_today = [("due_at", ">=", start), ("due_at", "<", end), ("state", "in", LIVE_TASK_STATES)]
        expected = Task.search_count(due_today)
        done_domain = due_today[:2] + [("state", "in", CLOSED_TASK_STATES)]
        done = Task.search_count(done_domain)
        tiles.append(self._tile(
            "tasks_today", "Work done today", done,
            f"{done} of {expected} tasks due today are done." if expected else "No tasks are due today.",
            "security.work.task", due_today, task_fields,
            tone="success" if expected and done == expected else "neutral", total=expected,
            trend=self._completion_trend(Task, today),
        ))

        overdue_domain = [("is_overdue", "=", True)]
        overdue = Task.search_count(overdue_domain)
        tiles.append(self._tile(
            "overdue", "Overdue work", overdue,
            "Tasks past their due time and not done." if overdue else "Nothing is overdue.",
            "security.work.task", overdue_domain, task_fields, tone="danger" if overdue else "success",
        ))

        week_ago = fields.Datetime.to_string(fields.Datetime.now() - timedelta(days=7))
        cnc_domain = [("state", "=", "could_not_complete"), ("write_date", ">=", week_ago)]
        cnc = Task.search_count(cnc_domain)
        tiles.append(self._tile(
            "could_not_complete", "Couldn't be done (7 days)", cnc,
            "Each one has the employee's reason attached." if cnc else "No work was reported blocked this week.",
            "security.work.task", cnc_domain, task_fields + ["cnc_reason", "cnc_note"],
            tone="warning" if cnc else "neutral",
        ))

        if "security.exception.instance" in self.env:
            Exc = self.env["security.exception.instance"].sudo()
            open_exc = [("state", "in", ("open", "stale_paused", "acknowledged"))]
            critical = Exc.search_count(open_exc + [("tier", "=", "critical")])
            total_exc = Exc.search_count(open_exc)
            tiles.append(self._tile(
                "exceptions", "Open exceptions", total_exc,
                f"{critical} critical." if total_exc else "No open operational issues.",
                "security.exception.instance", open_exc, ["title", "tier", "state", "site_id", "first_seen_at"],
                tone="danger" if critical else ("warning" if total_exc else "success"),
            ))

        if "security.training.assignment" in self.env:
            Asg = self.env["security.training.assignment"].sudo()
            late_domain = [("state", "in", ("assigned", "in_progress")), ("due_date", "<", fields.Date.to_string(today))]
            late = Asg.search_count(late_domain)
            tiles.append(self._tile(
                "training_overdue", "Training overdue", late,
                "Assigned courses past their due date." if late else "All assigned training is on time.",
                "security.training.assignment", late_domain, ["employee_id", "course_id", "due_date", "state"],
                tone="warning" if late else "success",
            ))

        Req = self.env["security.support.request"].sudo()
        open_req = [("state", "!=", "resolved")]
        req = Req.search_count(open_req)
        urgent = Req.search_count(open_req + [("priority", "=", "3")])
        tiles.append(self._tile(
            "support", "Problems reported", req,
            f"{urgent} say they are blocked from working." if urgent else ("Open reports from staff." if req else "No open problem reports."),
            "security.support.request", open_req, ["name", "subject", "user_id", "priority", "state", "create_date"],
            tone="danger" if urgent else ("warning" if req else "success"),
        ))

        return {
            "period_start": fields.Date.to_string(today),
            "period_end": fields.Date.to_string(today),
            "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
            "tiles": tiles,
        }

    @api.model
    def _completion_trend(self, Task, today):
        """This week's completion rate against last week's, with the counts
        behind both, so "improving" is never an unexplained arrow."""
        def rate(first_day, last_day):
            start = fields.Datetime.to_string(datetime.combine(first_day, time.min))
            end = fields.Datetime.to_string(datetime.combine(last_day + timedelta(days=1), time.min))
            domain = [("due_at", ">=", start), ("due_at", "<", end), ("state", "in", LIVE_TASK_STATES)]
            total = Task.search_count(domain)
            done = Task.search_count(domain[:2] + [("state", "in", CLOSED_TASK_STATES)])
            return done, total

        this_done, this_total = rate(today - timedelta(days=6), today)
        last_done, last_total = rate(today - timedelta(days=13), today - timedelta(days=7))
        if not this_total or not last_total:
            return None
        this_pct = round(100 * this_done / this_total)
        last_pct = round(100 * last_done / last_total)
        direction = "up" if this_pct > last_pct + 2 else ("down" if this_pct < last_pct - 2 else "flat")
        return {
            "direction": direction,
            "current_pct": this_pct,
            "previous_pct": last_pct,
            "explanation": (
                f"Last 7 days: {this_done} of {this_total} tasks done ({this_pct}%). "
                f"The 7 days before: {last_done} of {last_total} ({last_pct}%)."
            ),
        }
