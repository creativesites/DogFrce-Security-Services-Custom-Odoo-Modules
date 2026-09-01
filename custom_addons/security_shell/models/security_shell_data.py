import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

N_HISTOGRAM_BARS = 56

# Fixed action targets for Home-specific widgets (quick actions, attention rows).
# Kept here — not in nav_catalog.js — because these are Home-only shortcuts,
# not part of the curated sidebar tree.
HOME_ACTIONS = {
    "unassigned_slots": "security_operations.action_security_roster_slot",
    "awol": "security_attendance.action_security_attendance_record",
    "expiring_docs": "security_documents.action_security_expiring_document",
    "pending_leave": "security_leave.action_security_leave_request",
    "draft_invoices": "security_billing.action_security_billing_invoice",
    "coverage_trend": "security_reporting.action_security_roster_reporting",
    "approve_overtime": "security_attendance.action_security_attendance_record",
    "run_payroll": "security_payroll_core.action_security_payroll_command_center",
    "billing_status": "security_billing.action_security_billing_invoice",
    "fill_roster_gaps": "security_operations.action_security_roster_slot",
    "add_guard": "hr.open_view_employee_list_my",
    "publish_week": "security_shift_planner.action_security_roster_week",
}

# Attention rows, in display order. Each maps to a model + domain builder and
# is only ever surfaced to roles that can see it (finance keys are dropped
# server-side for non-finance users, never hidden in CSS).
ATTENTION_DEFS = [
    {
        "key": "unassigned_slots",
        "label": "Unassigned posts",
        "model": "security.roster.slot",
        "domain": lambda today, in7: [
            ("state", "=", "confirmed"),
            ("employee_id", "=", False),
            ("shift_date", ">=", today),
        ],
        "finance_only": False,
    },
    {
        "key": "awol",
        "label": "AWOL today",
        "model": "security.attendance.record",
        "domain": lambda today, in7: [
            ("shift_date", "=", today),
            ("absence_type", "=", "awol"),
        ],
        "finance_only": False,
    },
    {
        "key": "expiring_docs",
        "label": "Certifications expiring",
        "model": "security.employee.certification",
        "domain": lambda today, in7: [
            ("expiry_date", ">=", today),
            ("expiry_date", "<=", in7),
        ],
        "finance_only": False,
    },
    {
        "key": "pending_leave",
        "label": "Leave requests pending",
        "model": "security.leave.request",
        "domain": lambda today, in7: [("state", "=", "submitted")],
        "finance_only": False,
    },
    {
        "key": "draft_invoices",
        "label": "Draft invoices",
        "model": "security.billing.invoice",
        "domain": lambda today, in7: [("state", "=", "draft")],
        "finance_only": True,
    },
]

PERIOD_DAYS = {"today": 0, "week": 6, "month": 29}

# Extra live counts for nav-tree leaves that aren't part of the Needs
# Attention card. Reused where the underlying data already exists in
# ATTENTION_DEFS so a leaf and an attention row never diverge.
NAV_COUNT_DEFS = [
    {
        "key": "incidents",
        "model": "security.incident",
        "domain": lambda today, in7: [("state", "=", "draft")],
    },
    {
        "key": "ai_suggestions",
        "model": "security.smart.recommendation",
        "domain": lambda today, in7: [("state", "=", "pending")],
    },
    {
        "key": "late_arrivals",
        "model": "security.attendance.record",
        "domain": lambda today, in7: [
            ("shift_date", "=", today),
            ("late_minutes", ">", 0),
        ],
    },
    {
        "key": "overtime_approvals",
        "model": "security.attendance.record",
        "domain": lambda today, in7: [
            ("overtime_hours", ">", 0),
            ("overtime_approved", "=", False),
        ],
    },
]


class SecurityShellData(models.AbstractModel):
    _name = "security.shell.data"
    _description = "DeployGuard shell dashboard payload"

    def _count_safe(self, model_name, domain):
        """Count records for (model_name, domain), never raising.

        Returns None when the model/field doesn't exist on this database so
        a half-installed database still renders the dashboard.
        """
        if model_name not in self.env:
            return None
        try:
            return self.env[model_name].sudo().search_count(domain)
        except Exception:
            _logger.warning(
                "DeployGuard Shell: count failed for %s domain=%s",
                model_name,
                domain,
                exc_info=True,
            )
            return None

    def _get_roles(self):
        user = self.env.user
        return {
            "isOwner": user.has_group("security_base.group_security_owner"),
            "isManager": user.has_group("security_base.group_security_manager"),
            "isSupervisor": user.has_group("security_base.group_security_supervisor"),
            "isHR": user.has_group("hr.group_hr_user"),
            "isFinance": user.has_group("account.group_account_invoice"),
        }

    def _get_attention(self, roles, today, in7):
        rows = []
        is_finance = roles["isOwner"] or roles["isFinance"]
        for adef in ATTENTION_DEFS:
            if adef["finance_only"] and not is_finance:
                continue
            count = self._count_safe(adef["model"], adef["domain"](today, in7))
            rows.append({
                "key": adef["key"],
                "label": adef["label"],
                "count": count,
                "action": HOME_ACTIONS.get(adef["key"]),
            })
        return rows

    def _get_nav_counts(self, roles, today, in7):
        """Live counts for nav-tree leaves, keyed the same as nav_catalog.js's
        countKey. Reuses attention counts where the leaf mirrors an
        attention row so the two never disagree.
        """
        counts = {
            "unassigned_slots": self._count_safe(
                "security.roster.slot", [
                    ("state", "=", "confirmed"),
                    ("employee_id", "=", False),
                    ("shift_date", ">=", today),
                ]
            ),
            "awol": self._count_safe("security.attendance.record", [
                ("shift_date", "=", today), ("absence_type", "=", "awol"),
            ]),
            "expiring_docs": self._count_safe("security.employee.certification", [
                ("expiry_date", ">=", today), ("expiry_date", "<=", in7),
            ]),
            "pending_leave": self._count_safe("security.leave.request", [
                ("state", "=", "submitted"),
            ]),
        }
        is_finance = roles["isOwner"] or roles["isFinance"]
        if is_finance:
            counts["draft_invoices"] = self._count_safe("security.billing.invoice", [
                ("state", "=", "draft"),
            ])
        for cdef in NAV_COUNT_DEFS:
            counts[cdef["key"]] = self._count_safe(cdef["model"], cdef["domain"](today, in7))
        return counts

    def _date_range(self, today, period):
        span = PERIOD_DAYS.get(period, 0)
        return today, today + timedelta(days=span)

    def _get_coverage(self, period, today):
        if "security.roster.slot" not in self.env:
            return None
        try:
            Slot = self.env["security.roster.slot"].sudo()
            date_from, date_to = self._date_range(today, period)
            slots = Slot.search([
                ("shift_date", ">=", date_from),
                ("shift_date", "<=", date_to),
                ("state", "!=", "cancelled"),
            ])
            total = len(slots)
            filled = len(slots.filtered(
                lambda s: s.employee_id and s.state in ("assigned", "confirmed")
            ))
            percent = round((filled / total * 100.0), 1) if total else 0.0

            today_slots = slots.filtered(lambda s: s.shift_date == today)
            histogram = self._coverage_histogram(today_slots)

            if percent >= 95:
                status = "covered"
            elif percent >= 80:
                status = "at_risk"
            else:
                status = "gaps"

            return {
                "filled": filled,
                "required": total,
                "percent": percent,
                "status": status,
                "histogram": histogram,
            }
        except Exception:
            _logger.warning("DeployGuard Shell: coverage computation failed", exc_info=True)
            return None

    def _coverage_histogram(self, slots):
        bucket_width = 24.0 / N_HISTOGRAM_BARS
        totals = [0.0] * N_HISTOGRAM_BARS
        filled = [0.0] * N_HISTOGRAM_BARS

        for slot in slots:
            tmpl = slot.shift_template_id
            if not tmpl:
                continue
            start = tmpl.start_hour % 24.0
            duration = tmpl.duration_hours or 0.0
            if duration <= 0:
                continue
            is_filled = bool(slot.employee_id) and slot.state in ("assigned", "confirmed")
            for i in range(N_HISTOGRAM_BARS):
                bucket_start = i * bucket_width
                offset = (bucket_start - start) % 24.0
                if offset < duration:
                    totals[i] += 1
                    if is_filled:
                        filled[i] += 1

        return [
            round((filled[i] / totals[i] * 100.0), 1) if totals[i] else 0.0
            for i in range(N_HISTOGRAM_BARS)
        ]

    def _get_metrics(self, roles, today):
        is_finance = roles["isOwner"] or roles["isFinance"]
        metrics = []

        guards_count = self._count_safe(
            "hr.employee", [("security_guard", "=", True), ("active", "=", True)]
        )
        metrics.append({
            "key": "active_guards",
            "label": "Active guards",
            "value": guards_count,
            "meta": "On the roster",
        })

        sites_count = self._count_safe("security.client.site", [("active", "=", True)])
        metrics.append({
            "key": "sites",
            "label": "Client sites",
            "value": sites_count,
            "meta": "Under contract",
        })

        if "security.roster.slot" in self.env:
            open_shifts = self._count_safe("security.roster.slot", [
                ("state", "in", ("draft", "assigned")),
                ("shift_date", ">=", today),
            ])
            metrics.append({
                "key": "open_shifts",
                "label": "Open shifts (7d)",
                "value": open_shifts,
                "meta": "Not yet confirmed",
            })

        if is_finance:
            revenue = self._sum_safe(
                "security.billing.invoice",
                "amount_total",
                [("state", "!=", "draft"), ("state", "!=", "cancelled")],
            )
            metrics.append({
                "key": "billed_revenue",
                "label": "Billed revenue",
                "value": revenue,
                "meta": "All confirmed invoices",
            })

        return metrics

    def _sum_safe(self, model_name, field_name, domain):
        if model_name not in self.env:
            return None
        try:
            records = self.env[model_name].sudo().search(domain)
            if field_name not in records._fields:
                return None
            return sum(records.mapped(field_name))
        except Exception:
            _logger.warning(
                "DeployGuard Shell: sum failed for %s.%s", model_name, field_name,
                exc_info=True,
            )
            return None

    @api.model
    def get_home_payload(self, period="today"):
        """Returns {roles, attention[], coverage, metrics[], sites_count, actions{}}"""
        if period not in PERIOD_DAYS:
            period = "today"

        today = fields.Date.context_today(self)
        in7 = today + timedelta(days=7)

        roles = self._get_roles()
        sites_count = self._count_safe("security.client.site", [("active", "=", True)])

        return {
            "roles": roles,
            "attention": self._get_attention(roles, today, in7),
            "coverage": self._get_coverage(period, today),
            "metrics": self._get_metrics(roles, today),
            "sites_count": sites_count,
            "actions": HOME_ACTIONS,
            "nav_counts": self._get_nav_counts(roles, today, in7),
            "period": period,
        }
