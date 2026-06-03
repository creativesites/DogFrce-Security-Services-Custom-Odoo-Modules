import json
from datetime import timedelta

from odoo import api, fields, models

# ──────────────────────────────────────────────────────────────────────────────
# Component library spec — injected at the end of every system prompt
# ──────────────────────────────────────────────────────────────────────────────

_COMPONENT_LIBRARY = """

=== REQUIRED OUTPUT FORMAT ===
Respond with ONLY a single JSON object — no text before or after.
Match this schema exactly:

{
  "summary": "<one sentence — the single most important takeaway>",
  "status": "clean" | "findings",
  "confidence": <integer 1–5>,
  "components": [ <component objects — choose from the types below> ]
}

AVAILABLE COMPONENT TYPES:

ALERT — overall status callout, always place one first:
  {"type":"alert","variant":"success|info|warning|danger","title":"<short>","message":"<detail>"}

METRIC_ROW — 2–4 key numbers displayed side by side:
  {"type":"metric_row","metrics":[
    {"label":"<name>","value":"<number or text>","trend":"up|down|stable","severity":"success|warning|danger|info"}
  ]}

FINDING — one specific issue (repeat for each distinct problem, CRITICAL first):
  {"type":"finding","severity":"CRITICAL|WARNING|INFO",
   "title":"<short title>","detail":"<figures and explanation>","recommendation":"<action to take>"}

RECOMMENDATION — a concrete actionable suggestion:
  {"type":"recommendation","action":"<what to do>","reason":"<why>",
   "guard":"<name or omit>","post":"<name or omit>","date":"<date or omit>"}

TABLE — columnar data:
  {"type":"table","title":"<title>","headers":["Col1","Col2"],"rows":[["val","val"]]}

SECTION — narrative paragraph under a heading:
  {"type":"section","title":"<heading>","body":"<paragraph>"}

BULLET_LIST — simple list:
  {"type":"bullet_list","title":"<title or omit>","items":["item 1","item 2"]}

COMPOSITION RULES:
1. Always begin with exactly one "alert" component.
2. For a clean result: status="clean", alert variant="success".
3. For issues found: status="findings", alert variant="warning" or "danger".
4. Follow with a "metric_row" of the most important numbers from the data.
5. Add one "finding" per distinct issue, sorted CRITICAL → WARNING → INFO.
6. End with actionable "recommendation" or "section" components.
7. Be specific — use actual numbers, names, and dates from the provided data.
8. Omit optional fields (guard, post, date) rather than using empty strings."""


# ──────────────────────────────────────────────────────────────────────────────
# Domain-specific system prompts  (component library appended at call time)
# ──────────────────────────────────────────────────────────────────────────────

_ANOMALY_SYSTEM = (
    "You are an HR analytics assistant for a private security company in Namibia. "
    "Analyse the provided attendance data for a guard's payroll period and identify "
    "genuine operational concerns. Focus on AWOL, unusual hour patterns, excessive late "
    "arrivals, and missing checkouts. Be direct and specific — name the issue, cite the "
    "metric, and recommend a concrete action."
    + _COMPONENT_LIBRARY
)

_RISK_SYSTEM = (
    "You are a guard reliability analyst for a private security company. "
    "Given 90 days of operational history, assess the guard's overall risk level "
    "(LOW / MEDIUM / HIGH / CRITICAL) and explain what drives that rating. "
    "Consider AWOL frequency, absent shifts, late arrivals, missing checkouts, "
    "leave usage, document compliance, and whether the guard is disqualified."
    + _COMPONENT_LIBRARY
)

_BILLING_SYSTEM = (
    "You are a billing accuracy auditor for a private security company. "
    "Compare the provided invoice lines to actual attendance records for the same "
    "period and client. Identify overbilling, underbilling, missing line items, or "
    "rate discrepancies. Flag each issue clearly with specific figures."
    + _COMPONENT_LIBRARY
)

_ROSTER_SYSTEM = (
    "You are a roster planning assistant for a private security company. "
    "Given the unassigned shifts and the pool of available guards (with their scores "
    "and history), recommend the optimal assignment strategy. Consider fairness, "
    "site familiarity, reliability scores, and grade requirements."
    + _COMPONENT_LIBRARY
)

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_FEEDBACK_STATES = [
    ("pending", "Pending Review"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
    ("flagged", "Flagged for Review"),
]


def _reload_form(record):
    return {
        "type": "ir.actions.act_window",
        "res_model": record._name,
        "res_id": record.id,
        "view_mode": "form",
        "views": [(False, "form")],
        "target": "current",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Feature 1: Attendance Anomaly Detection — extends SecurityPayslip
# ──────────────────────────────────────────────────────────────────────────────

class SecurityPayslip(models.Model):
    _inherit = "security.payslip"

    ai_anomaly_narrative = fields.Text(string="AI Anomaly Analysis", readonly=True)
    ai_anomaly_date = fields.Datetime(string="Analysis Date", readonly=True)
    ai_anomaly_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )
    ai_anomaly_feedback_note = fields.Text(string="Feedback Note")

    def action_ai_detect_anomalies(self):
        engine = self.env["security.ai.engine"]
        for payslip in self:
            records = payslip.attendance_record_ids
            if not records:
                payslip.write({
                    "ai_anomaly_narrative": json.dumps({
                        "summary": "No attendance records linked to this payslip.",
                        "status": "clean",
                        "confidence": 5,
                        "components": [{"type": "alert", "variant": "info",
                                        "title": "No Data", "message": "No attendance records are linked to this payslip."}],
                    }),
                    "ai_anomaly_date": fields.Datetime.now(),
                    "ai_anomaly_feedback": "pending",
                })
                continue

            # Only send anomalous records to keep input tokens manageable.
            # Normal (clean) shifts are counted, not listed individually.
            anomalous_records = records.filtered(
                lambda r: r.absence_type == "awol"
                    or r.late_minutes > 0
                    or r.early_departure_minutes > 0
                    or r.missing_check_out
                    or r.status == "absent"
            )
            normal_count = len(records) - len(anomalous_records)

            data = {
                "employee": payslip.employee_id.name,
                "period": payslip.period_id.name,
                "worked_days": payslip.worked_days,
                "awol_occurrences": payslip.awol_occurrences,
                "late_occurrences": payslip.late_occurrences,
                "early_departure_occurrences": payslip.early_departure_occurrences,
                "normal_hours": round(payslip.normal_hours, 2),
                "saturday_hours": round(payslip.saturday_hours, 2),
                "sunday_hours": round(payslip.sunday_hours, 2),
                "public_holiday_hours": round(payslip.public_holiday_hours, 2),
                "night_hours": round(payslip.night_hours, 2),
                "overtime_hours": round(payslip.overtime_hours, 2),
                "unpaid_hours": round(payslip.unpaid_hours, 2),
                "rule_based_flags": payslip.anomaly_flags or "none",
                "daily_records": {
                    "normal_shifts_no_issues": normal_count,
                    "anomalous_records": [
                        {
                            "date": str(r.shift_date),
                            "status": r.status,
                            "late_min": r.late_minutes,
                            "early_dep_min": r.early_departure_minutes,
                            "absence": r.absence_type,
                            "missing_checkout": r.missing_check_out,
                        }
                        for r in anomalous_records[:20]
                    ],
                },
            }

            response = engine.complete(
                feature="attendance_anomaly",
                system_prompt=_ANOMALY_SYSTEM,
                user_message=json.dumps(data, default=str),
                max_tokens=4096,
            )
            if response:
                payslip.write({
                    "ai_anomaly_narrative": response,
                    "ai_anomaly_date": fields.Datetime.now(),
                    "ai_anomaly_feedback": "pending",
                })

        if len(self) == 1:
            return _reload_form(self)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ai_anomaly_accept(self):
        self.ai_anomaly_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_anomaly_reject(self):
        self.ai_anomaly_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_anomaly_flag(self):
        self.ai_anomaly_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 2: Guard Risk Profiling — extends HrEmployee
# ──────────────────────────────────────────────────────────────────────────────

class HrEmployee(models.Model):
    _inherit = "hr.employee"

    ai_risk_level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")],
        string="AI Risk Level",
        readonly=True,
    )
    ai_risk_narrative = fields.Text(string="AI Risk Analysis", readonly=True)
    ai_risk_date = fields.Datetime(string="Analysis Date", readonly=True)
    ai_risk_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )
    ai_risk_feedback_note = fields.Text(string="Feedback Note")

    def action_ai_risk_profile(self):
        engine = self.env["security.ai.engine"]
        attendance_model = self.env["security.attendance.record"]
        leave_model = (
            self.env["security.leave.request"]
            if "security.leave.request" in self.env
            else False
        )

        for employee in self.filtered("security_guard"):
            cutoff = fields.Date.context_today(self) - timedelta(days=90)

            records = attendance_model.search([
                ("employee_id", "=", employee.id),
                ("shift_date", ">=", cutoff),
            ])
            awol = len(records.filtered(lambda r: r.absence_type == "awol"))
            absent = len(records.filtered(
                lambda r: r.status == "absent" and r.absence_type != "awol"
            ))
            late = len(records.filtered(lambda r: r.late_minutes > 0))
            missing_co = len(records.filtered(lambda r: r.missing_check_out))
            total = len(records)

            leave_days = 0
            if leave_model:
                leaves = leave_model.search([
                    ("employee_id", "=", employee.id),
                    ("state", "=", "approved"),
                    ("date_from", ">=", str(cutoff)),
                ])
                leave_days = sum(leaves.mapped("requested_days"))

            expiring_docs = 0
            if hasattr(employee, "security_expiring_document_count"):
                expiring_docs = employee.security_expiring_document_count

            data = {
                "guard": employee.name,
                "grade": (
                    employee.security_grade_id.name if employee.security_grade_id else "Ungraded"
                ),
                "reliability_score": employee.security_reliability_score,
                "days_analysed": 90,
                "total_shifts": total,
                "awol_incidents": awol,
                "absent_shifts": absent,
                "late_arrivals": late,
                "missing_checkouts": missing_co,
                "approved_leave_days": round(leave_days, 1),
                "expiring_or_expired_documents": expiring_docs,
                "disqualified": employee.security_disqualified,
            }

            response = engine.complete(
                feature="risk_profiling",
                system_prompt=_RISK_SYSTEM,
                user_message=json.dumps(data, default=str),
            )
            if response:
                # Parse risk level from JSON if possible, else fall back to text scan
                level = "low"
                try:
                    parsed = _extract_json(response)
                    status_text = (parsed.get("summary", "") + " " + parsed.get("status", "")).upper()
                    for token in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                        if token in status_text:
                            level = token.lower()
                            break
                    # Also check the alert component variant
                    for comp in parsed.get("components", []):
                        if comp.get("type") == "alert":
                            v = comp.get("variant", "")
                            if v == "danger":
                                level = level if level in ("critical", "high") else "high"
                            elif v == "warning" and level == "low":
                                level = "medium"
                except Exception:
                    for token in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                        if token in response.upper():
                            level = token.lower()
                            break

                employee.write({
                    "ai_risk_level": level,
                    "ai_risk_narrative": response,
                    "ai_risk_date": fields.Datetime.now(),
                    "ai_risk_feedback": "pending",
                })

        if len(self) == 1:
            return _reload_form(self)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ai_risk_accept(self):
        self.ai_risk_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_risk_reject(self):
        self.ai_risk_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_risk_flag(self):
        self.ai_risk_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 3: Billing Auditor — extends SecurityBillingInvoice
# ──────────────────────────────────────────────────────────────────────────────

class SecurityBillingInvoice(models.Model):
    _inherit = "security.billing.invoice"

    ai_audit_notes = fields.Text(string="AI Billing Audit", readonly=True)
    ai_audit_date = fields.Datetime(string="Audit Date", readonly=True)
    ai_audit_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )
    ai_audit_feedback_note = fields.Text(string="Feedback Note")

    def action_ai_audit_billing(self):
        engine = self.env["security.ai.engine"]
        attendance_model = self.env["security.attendance.record"]

        for invoice in self:
            partner_id = invoice.partner_id.id if invoice.partner_id else False

            invoice_lines = [
                {
                    "description": line.name or "",
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "amount": line.subtotal,
                    "date": str(line.service_date_from) if line.service_date_from else "",
                }
                for line in invoice.line_ids
            ]

            domain = [("status", "in", ["present", "late", "early_leave"])]
            if partner_id:
                domain.append(("partner_id", "=", partner_id))
            if invoice.service_date_from:
                domain.append(("shift_date", ">=", invoice.service_date_from))
            if invoice.service_date_to:
                domain.append(("shift_date", "<=", invoice.service_date_to))

            records = attendance_model.search(domain)
            actual = {
                "total_shifts_worked": len(records),
                "normal_hours": round(sum(records.mapped("normal_hours")), 2),
                "sunday_hours": round(sum(records.mapped("sunday_hours")), 2),
                "public_holiday_hours": round(
                    sum(records.mapped("public_holiday_hours")), 2
                ),
                "saturday_hours": round(sum(records.mapped("saturday_hours")), 2),
                "night_hours": round(sum(records.mapped("night_hours")), 2),
            }

            data = {
                "client": invoice.partner_id.name if invoice.partner_id else "Unknown",
                "invoice_ref": invoice.name,
                "period": f"{invoice.service_date_from} to {invoice.service_date_to}",
                "invoice_total": invoice.total_amount,
                "invoice_lines": invoice_lines,
                "actual_attendance": actual,
            }

            response = engine.complete(
                feature="billing_auditor",
                system_prompt=_BILLING_SYSTEM,
                user_message=json.dumps(data, default=str),
            )
            if response:
                invoice.write({
                    "ai_audit_notes": response,
                    "ai_audit_date": fields.Datetime.now(),
                    "ai_audit_feedback": "pending",
                })

        if len(self) == 1:
            return _reload_form(self)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ai_audit_accept(self):
        self.ai_audit_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_audit_reject(self):
        self.ai_audit_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_audit_flag(self):
        self.ai_audit_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 4: Roster Optimizer — extends SecurityRosterBatch
# ──────────────────────────────────────────────────────────────────────────────

class SecurityRosterBatch(models.Model):
    _inherit = "security.roster.batch"

    ai_roster_notes = fields.Text(string="AI Roster Recommendations", readonly=True)
    ai_roster_date = fields.Datetime(string="Analysis Date", readonly=True)
    ai_roster_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )
    ai_roster_feedback_note = fields.Text(string="Feedback Note")

    def action_ai_optimize_roster(self):
        engine = self.env["security.ai.engine"]

        for batch in self:
            unassigned = batch.slot_ids.filtered(
                lambda s: not s.employee_id and s.state != "cancelled"
            )
            if not unassigned:
                batch.write({
                    "ai_roster_notes": json.dumps({
                        "summary": "All slots are already assigned — no optimization needed.",
                        "status": "clean",
                        "confidence": 5,
                        "components": [{"type": "alert", "variant": "success",
                                        "title": "All Slots Assigned",
                                        "message": "Every slot in this batch has an assigned guard."}],
                    }),
                    "ai_roster_date": fields.Datetime.now(),
                    "ai_roster_feedback": "pending",
                })
                continue

            guard_pool = {}
            for slot in unassigned:
                for sug in slot.suggestion_ids:
                    eid = sug.employee_id.id
                    if eid not in guard_pool:
                        guard_pool[eid] = {
                            "name": sug.employee_id.name,
                            "grade": (
                                sug.employee_grade_id.name if sug.employee_grade_id else "—"
                            ),
                            "avg_score": sug.score,
                            "suggestions_for": 1,
                        }
                    else:
                        g = guard_pool[eid]
                        g["avg_score"] = (
                            g["avg_score"] * g["suggestions_for"] + sug.score
                        ) / (g["suggestions_for"] + 1)
                        g["suggestions_for"] += 1

            unassigned_summary = [
                {
                    "slot_id": slot.id,
                    "post": slot.post_id.name if slot.post_id else "—",
                    "site": slot.site_id.name if slot.site_id else "—",
                    "date": str(slot.shift_date),
                    "shift": (
                        slot.shift_template_id.name if slot.shift_template_id else "—"
                    ),
                    "top_suggestions": [
                        {"guard": s.employee_id.name, "score": round(s.score, 1)}
                        for s in slot.suggestion_ids[:3]
                    ],
                }
                for slot in unassigned
            ]

            data = {
                "batch": batch.name,
                "date_range": f"{batch.date_from} to {batch.date_to}",
                "unassigned_count": len(unassigned),
                "unassigned_slots": unassigned_summary[:30],
                "available_guards": list(guard_pool.values())[:20],
            }

            response = engine.complete(
                feature="roster_optimizer",
                system_prompt=_ROSTER_SYSTEM,
                user_message=json.dumps(data, default=str),
            )
            if response:
                batch.write({
                    "ai_roster_notes": response,
                    "ai_roster_date": fields.Datetime.now(),
                    "ai_roster_feedback": "pending",
                })

        if len(self) == 1:
            return _reload_form(self)
        return {"type": "ir.actions.client", "tag": "reload"}

    def action_ai_roster_accept(self):
        self.ai_roster_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_roster_reject(self):
        self.ai_roster_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_roster_flag(self):
        self.ai_roster_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# System prompts — new features
# ──────────────────────────────────────────────────────────────────────────────

_SHIFT_FILL_SYSTEM = (
    "You are a shift replacement advisor for a private security company in Namibia. "
    "Given a vacant shift and a pool of available guards, recommend the TOP 3 best "
    "replacements. Rank by: (1) grade match — guard must meet the minimum grade, "
    "(2) reliability score — higher is better, (3) workload fairness — prefer guards "
    "with fewer shifts this month. Explain each recommendation concisely. "
    "Flag any document compliance concerns. If fewer than 3 suitable guards exist, "
    "recommend as many as possible and explain why others are unsuitable."
    + _COMPONENT_LIBRARY
)

_INCIDENT_ADVISOR_SYSTEM = (
    "You are a disciplinary consequence advisor for a private security company in Namibia. "
    "Given a behavioral incident and the guard's 12-month history, recommend an appropriate "
    "consequence using the progressive discipline framework: "
    "Verbal Warning → Written Warning → Final Written Warning → Suspension → Dismissal. "
    "Consider severity, recurrence, pattern, and proportionality. "
    "Be specific and document-ready — include exact language that could appear in the "
    "disciplinary letter. Also list mitigating and aggravating factors."
    + _COMPONENT_LIBRARY
)

_LEAVE_COVERAGE_SYSTEM = (
    "You are a roster coverage analyst for a private security company in Namibia. "
    "Given a guard's leave request, their assigned shifts during that period, and the "
    "current coverage state at their sites, assess whether approving this leave creates "
    "operational risk. Rate each affected site as: "
    "NO IMPACT / MANAGEABLE / COVERAGE CONCERN / CRITICAL GAP. "
    "Be specific about which dates and shifts are most at risk. "
    "Suggest practical mitigations for any coverage concerns."
    + _COMPONENT_LIBRARY
)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 5: Smart Shift Fill — extends SecurityAttendanceRecord
# ──────────────────────────────────────────────────────────────────────────────

class SecurityAttendanceRecord(models.Model):
    _inherit = "security.attendance.record"

    ai_replacement_suggestion = fields.Text(
        string="AI Replacement Suggestions", readonly=True
    )
    ai_replacement_date = fields.Datetime(string="Suggestion Date", readonly=True)
    ai_replacement_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )

    def action_ai_find_replacement(self):
        """Find the best available replacement guard for this absent/AWOL shift."""
        self.ensure_one()
        engine = self.env["security.ai.engine"]
        record = self

        shift_date = record.shift_date
        site = record.site_id
        post = record.post_id

        # Guards already scheduled anywhere that day
        already_scheduled = self.env["security.roster.slot"].search([
            ("shift_date", "=", shift_date),
            ("employee_id", "!=", False),
            ("state", "not in", ["cancelled"]),
        ]).mapped("employee_id").ids

        # Guards site-excluded
        excluded = []
        if site:
            excluded = self.env["security.guard.exclusion"].search([
                ("site_id", "=", site.id),
                ("active", "=", True),
            ]).mapped("employee_id").ids

        # Guards on approved leave that day
        on_leave = self.env["security.leave.request"].search([
            ("state", "=", "approved"),
            ("date_from", "<=", str(shift_date)),
            ("date_to", ">=", str(shift_date)),
        ]).mapped("employee_id").ids

        unavailable = list(set(already_scheduled + excluded + on_leave))

        # Grade requirement for this post
        required_grade_seq = None
        required_grade_name = "Any"
        if post and post.post_type_id and post.post_type_id.min_grade_id:
            mg = post.post_type_id.min_grade_id
            required_grade_seq = mg.sequence
            required_grade_name = mg.name

        # Candidate pool — active, not disqualified, not unavailable
        candidates = self.env["hr.employee"].search([
            ("security_guard", "=", True),
            ("active", "=", True),
            ("security_disqualified", "=", False),
            ("id", "not in", unavailable),
        ], order="security_reliability_score desc", limit=25)

        # Workload last 30 days
        month_ago = fields.Date.context_today(self) - timedelta(days=30)
        guard_list = []
        for g in candidates:
            workload = self.env["security.roster.slot"].search_count([
                ("employee_id", "=", g.id),
                ("shift_date", ">=", month_ago),
                ("state", "=", "confirmed"),
            ])
            grade_seq = g.security_grade_id.sequence if g.security_grade_id else 9999
            meets_grade = (
                required_grade_seq is None or grade_seq <= required_grade_seq
            )
            guard_list.append({
                "name": g.name,
                "grade": g.security_grade_id.name if g.security_grade_id else "Ungraded",
                "grade_sequence": grade_seq,
                "meets_grade_requirement": meets_grade,
                "reliability_score": g.security_reliability_score,
                "shifts_last_30d": workload,
                "expiring_docs": getattr(g, "security_expiring_document_count", 0),
            })

        data = {
            "vacant_shift": {
                "date": str(shift_date),
                "site": site.name if site else "—",
                "post": post.name if post else "—",
                "shift_template": (
                    record.shift_template_id.name if record.shift_template_id else "—"
                ),
                "required_grade": required_grade_name,
            },
            "absent_guard": {
                "name": record.employee_id.name if record.employee_id else "—",
                "absence_type": record.absence_type or record.status,
            },
            "total_candidates": len(guard_list),
            "grade_qualified_candidates": sum(
                1 for g in guard_list if g["meets_grade_requirement"]
            ),
            "available_guards": guard_list,
        }

        response = engine.complete(
            feature="shift_fill",
            system_prompt=_SHIFT_FILL_SYSTEM,
            user_message=json.dumps(data, default=str),
        )
        if response:
            record.write({
                "ai_replacement_suggestion": response,
                "ai_replacement_date": fields.Datetime.now(),
                "ai_replacement_feedback": "pending",
            })

        return _reload_form(self)

    def action_ai_replacement_accept(self):
        self.ai_replacement_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_replacement_reject(self):
        self.ai_replacement_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_replacement_flag(self):
        self.ai_replacement_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 6: Incident Consequence Advisor — extends SecurityIncident
# ──────────────────────────────────────────────────────────────────────────────

class SecurityIncident(models.Model):
    _inherit = "security.incident"

    ai_consequence_recommendation = fields.Text(
        string="AI Consequence Recommendation", readonly=True
    )
    ai_consequence_date = fields.Datetime(string="Analysis Date", readonly=True)
    ai_consequence_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )

    def action_ai_consequence_advisor(self):
        """Generate a disciplinary consequence recommendation for this incident."""
        self.ensure_one()
        engine = self.env["security.ai.engine"]
        record = self
        employee = record.employee_id

        # 12-month incident history for this guard
        cutoff = fields.Date.context_today(self) - timedelta(days=365)
        history = self.env["security.incident"].search([
            ("employee_id", "=", employee.id),
            ("incident_date", ">=", str(cutoff)),
            ("id", "!=", record.id),
            ("state", "in", ["approved", "resolved"]),
        ], order="incident_date desc")

        history_summary = [
            {
                "date": str(h.incident_date),
                "type": h.incident_type_id.name if h.incident_type_id else "—",
                "deduction": h.deduction_amount,
                "state": h.state,
                "high_trust_exclusion": h.high_trust_exclusion,
            }
            for h in history
        ]

        # Count incidents by type in history
        type_counts = {}
        for h in history:
            t = h.incident_type_id.name if h.incident_type_id else "Unknown"
            type_counts[t] = type_counts.get(t, 0) + 1

        # Same type recurrence count
        current_type = record.incident_type_id.name if record.incident_type_id else ""
        recurrence_count = type_counts.get(current_type, 0)

        data = {
            "guard": employee.name,
            "grade": (
                employee.security_grade_id.name if employee.security_grade_id else "Ungraded"
            ),
            "reliability_score": employee.security_reliability_score,
            "current_incident": {
                "date": str(record.incident_date),
                "type": current_type,
                "deduction_amount": record.deduction_amount,
                "reliability_score_delta": record.reliability_score_delta,
                "high_trust_exclusion": record.high_trust_exclusion,
                "description": record.note or "No description provided.",
            },
            "discipline_history_12m": {
                "total_incidents": len(history),
                "incidents_by_type": type_counts,
                "same_type_recurrences": recurrence_count,
                "total_deductions_ytd": sum(history.mapped("deduction_amount")),
                "recent_incidents": history_summary[:10],
            },
        }

        response = engine.complete(
            feature="incident_advisor",
            system_prompt=_INCIDENT_ADVISOR_SYSTEM,
            user_message=json.dumps(data, default=str),
        )
        if response:
            record.write({
                "ai_consequence_recommendation": response,
                "ai_consequence_date": fields.Datetime.now(),
                "ai_consequence_feedback": "pending",
            })

        return _reload_form(self)

    def action_ai_consequence_accept(self):
        self.ai_consequence_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_consequence_reject(self):
        self.ai_consequence_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_consequence_flag(self):
        self.ai_consequence_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 7: Leave Coverage Check — extends SecurityLeaveRequest
# ──────────────────────────────────────────────────────────────────────────────

class SecurityLeaveRequest(models.Model):
    _inherit = "security.leave.request"

    ai_coverage_assessment = fields.Text(
        string="AI Coverage Assessment", readonly=True
    )
    ai_coverage_date = fields.Datetime(string="Assessment Date", readonly=True)
    ai_coverage_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )

    def action_ai_coverage_check(self):
        """Check whether this leave request creates roster coverage gaps."""
        self.ensure_one()
        engine = self.env["security.ai.engine"]
        record = self
        employee = record.employee_id
        date_from = record.date_from
        date_to = record.date_to

        # Guard's confirmed roster slots in the leave period
        my_slots = self.env["security.roster.slot"].search([
            ("employee_id", "=", employee.id),
            ("shift_date", ">=", date_from),
            ("shift_date", "<=", date_to),
            ("state", "=", "confirmed"),
        ])

        # Other guards already on approved leave during the same window
        other_leaves = self.env["security.leave.request"].search([
            ("state", "=", "approved"),
            ("date_from", "<=", str(date_to)),
            ("date_to", ">=", str(date_from)),
            ("id", "!=", record.id),
        ])
        other_leave_emp_ids = set(other_leaves.mapped("employee_id.id"))

        # Per-site impact analysis
        affected_sites = my_slots.mapped("site_id")
        site_impact = []
        for site in affected_sites:
            all_site_slots = self.env["security.roster.slot"].search([
                ("site_id", "=", site.id),
                ("shift_date", ">=", date_from),
                ("shift_date", "<=", date_to),
                ("state", "=", "confirmed"),
            ])
            my_site_slots = all_site_slots.filtered(
                lambda s: s.employee_id.id == employee.id
            )
            other_on_leave_at_site = all_site_slots.filtered(
                lambda s: s.employee_id.id in other_leave_emp_ids
                and s.employee_id.id != employee.id
            )
            remaining = len(all_site_slots) - len(my_site_slots) - len(other_on_leave_at_site)

            site_impact.append({
                "site": site.name,
                "client": site.partner_id.name if site.partner_id else "—",
                "total_slots_in_period": len(all_site_slots),
                "guard_slots_to_vacate": len(my_site_slots),
                "other_guards_on_leave": len(
                    set(other_on_leave_at_site.mapped("employee_id.id"))
                ),
                "estimated_remaining_coverage": max(0, remaining),
            })

        # Unique dates the guard is scheduled
        scheduled_dates = sorted(set(str(s.shift_date) for s in my_slots))

        data = {
            "guard": employee.name,
            "grade": (
                employee.security_grade_id.name if employee.security_grade_id else "Ungraded"
            ),
            "leave_request": {
                "type": record.leave_type_id.name if record.leave_type_id else "—",
                "date_from": str(date_from),
                "date_to": str(date_to),
                "days_requested": record.requested_days,
                "remaining_balance_after": record.remaining_balance_after,
            },
            "scheduled_during_leave": {
                "total_shifts": len(my_slots),
                "dates": scheduled_dates[:20],
                "sites_affected": [s["site"] for s in site_impact],
            },
            "other_guards_on_leave_same_period": len(other_leave_emp_ids),
            "site_coverage_analysis": site_impact,
        }

        response = engine.complete(
            feature="leave_coverage",
            system_prompt=_LEAVE_COVERAGE_SYSTEM,
            user_message=json.dumps(data, default=str),
        )
        if response:
            record.write({
                "ai_coverage_assessment": response,
                "ai_coverage_date": fields.Datetime.now(),
                "ai_coverage_feedback": "pending",
            })

        return _reload_form(self)

    def action_ai_coverage_accept(self):
        self.ai_coverage_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_coverage_reject(self):
        self.ai_coverage_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_coverage_flag(self):
        self.ai_coverage_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# System prompts — remaining features
# ──────────────────────────────────────────────────────────────────────────────

_DOC_RENEWAL_SYSTEM = (
    "You are an HR administrator for a private security company in Namibia. "
    "Draft a professional, formal letter to a security guard requesting renewal of their "
    "expiring or expired document. The letter must be specific: include the exact document "
    "type, current document number, expiry date, submission deadline (at least 10 working days "
    "before expiry, or immediately if already expired), and the list of materials needed for renewal. "
    "State clearly that failure to renew will result in suspension from active duty until the "
    "document is renewed. Use a professional but empathetic tone. Address the guard by name."
    + _COMPONENT_LIBRARY
)

_PERFORMANCE_REVIEW_SYSTEM = (
    "You are an HR manager generating a formal quarterly performance review for a security guard. "
    "Evaluate the guard across four dimensions: (1) Attendance & Punctuality, "
    "(2) Discipline & Conduct, (3) Document Compliance, (4) Reliability & Consistency. "
    "Assign an overall rating: OUTSTANDING / SATISFACTORY / NEEDS IMPROVEMENT / UNSATISFACTORY. "
    "Provide specific metric-backed observations for each dimension. Include developmental "
    "recommendations and any commendations. Be objective, fair, and document-ready — "
    "this review may be placed in the guard's personnel file."
    + _COMPONENT_LIBRARY
)

_PAYSLIP_EXPLAIN_SYSTEM = (
    "You are an HR assistant explaining a security guard's monthly payslip in plain, simple English. "
    "Assume the guard has limited financial literacy. For every earning line, explain what it is "
    "and exactly how the figure was calculated (e.g. '22 days × N$X/day'). "
    "For every deduction, explain what it is, why it is deducted, and whether it is a legal "
    "requirement (e.g. PAYE, SSC) or a voluntary deduction (e.g. loan repayment). "
    "Show how the take-home pay is reached. Use everyday language — no jargon. "
    "End with a note on how to raise queries within 5 working days."
    + _COMPONENT_LIBRARY
)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 8: Document Renewal Letter — extends SecurityEmployeeDocument
# ──────────────────────────────────────────────────────────────────────────────

class SecurityEmployeeDocument(models.Model):
    _inherit = "security.employee.document"

    ai_renewal_letter = fields.Text(string="AI Renewal Letter", readonly=True)
    ai_renewal_letter_date = fields.Datetime(string="Letter Generated", readonly=True)
    ai_renewal_letter_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )

    def action_ai_generate_renewal_letter(self):
        """Draft a formal document renewal notice for this guard document."""
        self.ensure_one()
        engine = self.env["security.ai.engine"]
        record = self

        doc_type = record.document_type_id
        employee = record.employee_id

        data = {
            "guard_name": employee.name if employee else "Unknown",
            "grade": (
                employee.security_grade_id.name if employee and employee.security_grade_id else "Ungraded"
            ),
            "document": {
                "type": doc_type.name if doc_type else "Unknown Document",
                "category": doc_type.category if doc_type else "—",
                "document_number": record.document_number or "—",
                "issuing_authority": record.issuing_authority or "—",
                "issue_date": str(record.issue_date) if record.issue_date else "—",
                "expiry_date": str(record.expiry_date) if record.expiry_date else "—",
                "days_to_expiry": record.days_to_expiry,
                "expiry_status": record.expiry_status,
                "required_for_active_duty": (
                    doc_type.required_for_active_guard if doc_type else False
                ),
            },
        }

        response = engine.complete(
            feature="doc_renewal_letter",
            system_prompt=_DOC_RENEWAL_SYSTEM,
            user_message=json.dumps(data, default=str),
        )
        if response:
            record.write({
                "ai_renewal_letter": response,
                "ai_renewal_letter_date": fields.Datetime.now(),
                "ai_renewal_letter_feedback": "pending",
            })

        return _reload_form(self)

    def action_ai_renewal_accept(self):
        self.ai_renewal_letter_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_renewal_reject(self):
        self.ai_renewal_letter_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_renewal_flag(self):
        self.ai_renewal_letter_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 9: Guard Performance Review — extends HrEmployee (additional fields)
# ──────────────────────────────────────────────────────────────────────────────

class HrEmployeePerformance(models.Model):
    _inherit = "hr.employee"

    ai_performance_review = fields.Text(string="AI Performance Review", readonly=True)
    ai_performance_review_date = fields.Datetime(string="Review Date", readonly=True)
    ai_performance_review_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )

    def action_ai_performance_review(self):
        """Generate a formal quarterly performance review for this guard."""
        self.ensure_one()
        engine = self.env["security.ai.engine"]
        employee = self

        if not employee.security_guard:
            return

        cutoff_90 = fields.Date.context_today(self) - timedelta(days=90)
        cutoff_365 = fields.Date.context_today(self) - timedelta(days=365)

        # Attendance in last 90 days
        att = self.env["security.attendance.record"].search([
            ("employee_id", "=", employee.id),
            ("shift_date", ">=", cutoff_90),
        ])
        total_shifts = len(att)
        present = len(att.filtered(lambda r: r.status in ("present", "late")))
        awol = len(att.filtered(lambda r: r.absence_type == "awol"))
        absent = total_shifts - present - awol
        late = len(att.filtered(lambda r: r.late_minutes > 0))
        missing_co = len(att.filtered(lambda r: r.missing_check_out))
        attendance_rate = (present / total_shifts * 100) if total_shifts else 0

        # Incidents in last 90 days
        incidents_90d = self.env["security.incident"].search([
            ("employee_id", "=", employee.id),
            ("incident_date", ">=", str(cutoff_90)),
            ("state", "in", ["approved", "resolved"]),
        ])
        # Incidents in last 365 days
        incidents_365d = self.env["security.incident"].search([
            ("employee_id", "=", employee.id),
            ("incident_date", ">=", str(cutoff_365)),
            ("state", "in", ["approved", "resolved"]),
        ])

        # Documents
        all_docs = getattr(employee, "security_document_ids", self.env["security.employee.document"])
        expired_docs = len(all_docs.filtered(lambda d: d.expiry_status == "expired"))
        expiring_docs = len(all_docs.filtered(lambda d: d.expiry_status == "expiring"))
        verified_docs = len(all_docs.filtered(lambda d: d.state == "verified"))

        # Leave in last 90 days
        leave_90d = 0
        try:
            leaves = self.env["security.leave.request"].search([
                ("employee_id", "=", employee.id),
                ("state", "=", "approved"),
                ("date_from", ">=", str(cutoff_90)),
            ])
            leave_90d = sum(leaves.mapped("requested_days"))
        except Exception:
            pass

        # Certifications
        certs = []
        if hasattr(employee, "security_certification_ids"):
            certs = employee.security_certification_ids.mapped("name")

        data = {
            "guard": employee.name,
            "grade": (
                employee.security_grade_id.name if employee.security_grade_id else "Ungraded"
            ),
            "reliability_score": employee.security_reliability_score,
            "is_disqualified": employee.security_disqualified,
            "certifications": certs,
            "review_period_days": 90,
            "attendance": {
                "total_shifts": total_shifts,
                "present": present,
                "absent": absent,
                "awol": awol,
                "late_arrivals": late,
                "missing_checkouts": missing_co,
                "attendance_rate_pct": round(attendance_rate, 1),
                "leave_days": round(leave_90d, 1),
            },
            "discipline": {
                "incidents_last_90d": len(incidents_90d),
                "incidents_last_365d": len(incidents_365d),
                "incident_types_90d": [
                    i.incident_type_id.name for i in incidents_90d if i.incident_type_id
                ],
                "total_deductions_90d": sum(incidents_90d.mapped("deduction_amount")),
            },
            "documents": {
                "total": len(all_docs),
                "verified": verified_docs,
                "expiring_soon": expiring_docs,
                "expired": expired_docs,
            },
        }

        response = engine.complete(
            feature="performance_review",
            system_prompt=_PERFORMANCE_REVIEW_SYSTEM,
            user_message=json.dumps(data, default=str),
        )
        if response:
            employee.write({
                "ai_performance_review": response,
                "ai_performance_review_date": fields.Datetime.now(),
                "ai_performance_review_feedback": "pending",
            })

        return _reload_form(self)

    def action_ai_performance_accept(self):
        self.ai_performance_review_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_performance_reject(self):
        self.ai_performance_review_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_performance_flag(self):
        self.ai_performance_review_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Feature 10: Payslip Plain-English Explanation — extends SecurityPayslip
# ──────────────────────────────────────────────────────────────────────────────

class SecurityPayslipExplain(models.Model):
    _inherit = "security.payslip"

    ai_payslip_explanation = fields.Text(string="AI Payslip Explanation", readonly=True)
    ai_payslip_explanation_date = fields.Datetime(string="Explanation Date", readonly=True)
    ai_payslip_explanation_feedback = fields.Selection(
        _FEEDBACK_STATES, string="Feedback", default="pending"
    )

    def action_ai_explain_payslip(self):
        """Generate a plain-English explanation of this payslip for the guard."""
        self.ensure_one()
        engine = self.env["security.ai.engine"]
        payslip = self

        earning_lines = [
            {
                "name": line.name,
                "code": line.code,
                "quantity": line.quantity,
                "rate": line.rate,
                "amount": line.amount,
            }
            for line in payslip.earning_line_ids
        ]
        deduction_lines = [
            {
                "name": line.name,
                "code": line.code,
                "quantity": line.quantity,
                "rate": line.rate,
                "amount": line.amount,
            }
            for line in payslip.deduction_line_ids
        ]

        data = {
            "guard_name": payslip.employee_id.name if payslip.employee_id else "—",
            "pay_period": payslip.period_id.name if payslip.period_id else "—",
            "summary": {
                "worked_days": payslip.worked_days,
                "normal_hours": round(payslip.normal_hours, 2),
                "saturday_hours": round(payslip.saturday_hours, 2),
                "sunday_hours": round(payslip.sunday_hours, 2),
                "public_holiday_hours": round(payslip.public_holiday_hours, 2),
                "night_hours": round(payslip.night_hours, 2),
                "overtime_hours": round(payslip.overtime_hours, 2),
                "unpaid_hours": round(payslip.unpaid_hours, 2),
                "awol_occurrences": payslip.awol_occurrences,
                "late_occurrences": payslip.late_occurrences,
                "paid_leave_days": payslip.paid_leave_days,
                "unpaid_leave_days": payslip.unpaid_leave_days,
            },
            "financials": {
                "total_earnings": payslip.total_earnings,
                "total_deductions": payslip.total_deductions,
                "net_pay": payslip.net_pay,
            },
            "earning_lines": earning_lines,
            "deduction_lines": deduction_lines,
        }

        response = engine.complete(
            feature="payslip_explain",
            system_prompt=_PAYSLIP_EXPLAIN_SYSTEM,
            user_message=json.dumps(data, default=str),
        )
        if response:
            payslip.write({
                "ai_payslip_explanation": response,
                "ai_payslip_explanation_date": fields.Datetime.now(),
                "ai_payslip_explanation_feedback": "pending",
            })

        return _reload_form(self)

    def action_ai_explain_accept(self):
        self.ai_payslip_explanation_feedback = "accepted"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_explain_reject(self):
        self.ai_payslip_explanation_feedback = "rejected"
        if len(self) == 1:
            return _reload_form(self)

    def action_ai_explain_flag(self):
        self.ai_payslip_explanation_feedback = "flagged"
        if len(self) == 1:
            return _reload_form(self)


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _extract_json(text):
    """Extract and parse the first JSON object from an AI response string."""
    import re
    s = (text or "").strip()
    # Strip ```json fences if present
    m = re.search(r"```json\s*([\s\S]*?)\s*```", s)
    if m:
        s = m.group(1)
    # Find the first { ... } block
    start = s.find("{")
    if start >= 0:
        return json.loads(s[start:])
    raise ValueError("No JSON object found in response")
