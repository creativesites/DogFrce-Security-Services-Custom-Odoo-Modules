import uuid

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class SecurityReconciliationRule(models.Model):
    _name = "security.reconciliation.rule"
    _description = "Reconciliation Sync Rule"
    _order = "sequence, name, id"
    _check_company_auto = True

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    adapter_code = fields.Char(required=True, index=True, help="Stable code owned by a reconciliation adapter.")
    source_model = fields.Char(required=True)
    target_model = fields.Char(required=True)
    sync_direction = fields.Selection([
        ("bidirectional", "Bidirectional"),
        ("deployguard_to_odoo", "DeployGuard to Odoo"),
        ("odoo_to_deployguard", "Odoo to DeployGuard"),
    ], required=True, default="bidirectional")
    sync_mode = fields.Selection([
        ("queued", "Queued"),
        ("inline_validation", "Inline Validation"),
        ("batch", "Scheduled Batch"),
    ], required=True, default="queued")
    conflict_policy = fields.Selection([
        ("manual", "Manual Resolution"),
        ("source_wins", "Source Wins"),
        ("target_wins", "Target Wins"),
    ], required=True, default="manual")
    handler_model = fields.Char(help="Adapter service model that processes queued jobs.")
    handler_method = fields.Char(default="_process_reconciliation_job")
    max_attempts = fields.Integer(default=5)
    retry_delay_minutes = fields.Integer(default=5)
    notes = fields.Text()
    job_count = fields.Integer(compute="_compute_counts")
    conflict_count = fields.Integer(compute="_compute_counts")

    _reconciliation_rule_company_code_uniq = models.Constraint(
        "UNIQUE(company_id, adapter_code)",
        "An adapter code can only have one rule per company.",
    )

    @api.constrains("max_attempts", "retry_delay_minutes")
    def _check_retry_values(self):
        for rule in self:
            if rule.max_attempts < 1 or rule.retry_delay_minutes < 1:
                raise ValidationError(_("Retry attempts and delay must both be at least one."))

    def _compute_counts(self):
        Job = self.env["security.reconciliation.job"]
        Conflict = self.env["security.reconciliation.conflict"]
        for rule in self:
            rule.job_count = Job.search_count([("rule_id", "=", rule.id), ("state", "in", ("pending", "retry", "running"))])
            rule.conflict_count = Conflict.search_count([("rule_id", "=", rule.id), ("state", "in", ("open", "assigned"))])


class SecurityReconciliationLink(models.Model):
    _name = "security.reconciliation.link"
    _description = "Reconciliation Record Link"
    _order = "write_date desc, id desc"
    _check_company_auto = True

    rule_id = fields.Many2one("security.reconciliation.rule", required=True, ondelete="restrict", check_company=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    adapter_code = fields.Char(related="rule_id.adapter_code", store=True, index=True)
    source_model = fields.Char(required=True, index=True)
    source_res_id = fields.Integer(required=True, index=True)
    target_model = fields.Char(required=True, index=True)
    target_res_id = fields.Integer(required=True, index=True)
    external_key = fields.Char(index=True)
    state = fields.Selection([
        ("active", "Active"), ("broken", "Broken"), ("superseded", "Superseded"), ("archived", "Archived"),
    ], required=True, default="active", index=True)
    source_fingerprint = fields.Char()
    target_fingerprint = fields.Char()
    last_source_sync_at = fields.Datetime()
    last_target_sync_at = fields.Datetime()
    last_job_id = fields.Many2one("security.reconciliation.job", ondelete="set null")
    note = fields.Text()

    _reconciliation_link_source_uniq = models.Constraint(
        "UNIQUE(rule_id, source_model, source_res_id)",
        "This source record already has a link for this rule.",
    )
    _reconciliation_link_target_uniq = models.Constraint(
        "UNIQUE(rule_id, target_model, target_res_id)",
        "This target record already has a link for this rule.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        Rule = self.env["security.reconciliation.rule"]
        for vals in vals_list:
            if vals.get("rule_id"):
                vals["company_id"] = Rule.browse(vals["rule_id"]).company_id.id
        return super().create(vals_list)

    def action_open_source(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": self.source_model, "res_id": self.source_res_id, "views": [[False, "form"]], "target": "current"}

    def action_open_target(self):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "res_model": self.target_model, "res_id": self.target_res_id, "views": [[False, "form"]], "target": "current"}


class SecurityReconciliationJob(models.Model):
    _name = "security.reconciliation.job"
    _description = "Reconciliation Job"
    _order = "next_attempt_at, id"
    _check_company_auto = True

    name = fields.Char(required=True, default="New", copy=False)
    rule_id = fields.Many2one("security.reconciliation.rule", required=True, ondelete="restrict", check_company=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    link_id = fields.Many2one("security.reconciliation.link", ondelete="set null", check_company=True)
    origin_model = fields.Char(required=True, index=True)
    origin_res_id = fields.Integer(required=True, index=True)
    direction = fields.Selection([
        ("deployguard_to_odoo", "DeployGuard to Odoo"), ("odoo_to_deployguard", "Odoo to DeployGuard"),
        ("reconcile", "Reconcile"), ("repair", "Repair"),
    ], required=True, default="reconcile")
    event_type = fields.Selection([
        ("create", "Create"), ("write", "Write"), ("state_change", "State Change"),
        ("delete_request", "Delete Request"), ("sweep", "Sweep"), ("repair", "Repair"),
    ], required=True, default="write")
    payload_json = fields.Json(default=dict)
    correlation_id = fields.Char(required=True, default=lambda self: str(uuid.uuid4()), copy=False, index=True)
    state = fields.Selection([
        ("pending", "Pending"), ("running", "Running"), ("retry", "Retry"), ("done", "Done"),
        ("conflict", "Conflict"), ("failed", "Failed"), ("cancelled", "Cancelled"),
    ], required=True, default="pending", index=True)
    attempt_count = fields.Integer(default=0)
    next_attempt_at = fields.Datetime(default=fields.Datetime.now, index=True)
    started_at = fields.Datetime()
    completed_at = fields.Datetime()
    error_message = fields.Text()
    log_ids = fields.One2many("security.reconciliation.log", "job_id")
    conflict_ids = fields.One2many("security.reconciliation.conflict", "job_id")

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        Rule = self.env["security.reconciliation.rule"]
        for vals in vals_list:
            if vals.get("name") in (False, "New"):
                vals["name"] = sequence.next_by_code("security.reconciliation.job") or "New"
            if vals.get("rule_id"):
                vals["company_id"] = Rule.browse(vals["rule_id"]).company_id.id
        return super().create(vals_list)

    def _log(self, result, message, details=None):
        for job in self:
            self.env["security.reconciliation.log"].create({"job_id": job.id, "rule_id": job.rule_id.id, "company_id": job.company_id.id, "result": result, "message": message, "details_json": details or {}})

    def action_requeue(self):
        self.filtered(lambda job: job.state in ("failed", "retry", "cancelled", "conflict")).write({"state": "pending", "next_attempt_at": fields.Datetime.now(), "error_message": False})

    def action_cancel(self):
        self.filtered(lambda job: job.state in ("pending", "retry")).write({"state": "cancelled"})

    @api.model
    def action_dispatch_jobs(self, limit=50):
        now = fields.Datetime.now()
        jobs = self.search([("state", "in", ("pending", "retry")), ("next_attempt_at", "<=", now)], limit=limit, order="next_attempt_at, id")
        for job in jobs:
            job._process()
        return len(jobs)

    def _process(self):
        self.ensure_one()
        if self.state not in ("pending", "retry"):
            return
        self.write({"state": "running", "started_at": fields.Datetime.now(), "attempt_count": self.attempt_count + 1, "error_message": False})
        rule = self.rule_id
        try:
            if not rule.handler_model or not rule.handler_method:
                raise UserError(_("Rule '%s' has no registered adapter handler.") % rule.name)
            handler = self.env[rule.handler_model]
            getattr(handler.with_context(reconciliation_origin=rule.adapter_code, reconciliation_job_id=self.id, reconciliation_correlation_id=self.correlation_id), rule.handler_method)(self)
            self.write({"state": "done", "completed_at": fields.Datetime.now()})
            self._log("done", _("Synchronization job completed."))
        except ValidationError as error:
            self.write({"state": "conflict", "completed_at": fields.Datetime.now(), "error_message": str(error)})
            self._log("conflict", str(error))
        except Exception as error:
            if self.attempt_count >= rule.max_attempts:
                values = {"state": "failed", "completed_at": fields.Datetime.now(), "error_message": str(error)}
            else:
                delay = rule.retry_delay_minutes * (2 ** max(self.attempt_count - 1, 0))
                values = {"state": "retry", "next_attempt_at": fields.Datetime.add(fields.Datetime.now(), minutes=delay), "error_message": str(error)}
            self.write(values)
            self._log(values["state"], str(error))


class SecurityReconciliationLog(models.Model):
    _name = "security.reconciliation.log"
    _description = "Reconciliation Audit Log"
    _order = "create_date desc, id desc"
    _check_company_auto = True

    job_id = fields.Many2one("security.reconciliation.job", required=True, ondelete="cascade", check_company=True)
    rule_id = fields.Many2one("security.reconciliation.rule", required=True, ondelete="restrict", check_company=True)
    company_id = fields.Many2one("res.company", required=True, index=True)
    result = fields.Selection([( "done", "Done"), ("skipped", "Skipped"), ("conflict", "Conflict"), ("retry", "Retry"), ("failed", "Failed")], required=True)
    message = fields.Text(required=True)
    details_json = fields.Json(default=dict)


class SecurityReconciliationConflict(models.Model):
    _name = "security.reconciliation.conflict"
    _description = "Reconciliation Conflict"
    _order = "severity desc, create_date desc"
    _check_company_auto = True

    name = fields.Char(required=True, default="New")
    job_id = fields.Many2one("security.reconciliation.job", required=True, ondelete="cascade", check_company=True)
    rule_id = fields.Many2one("security.reconciliation.rule", required=True, ondelete="restrict", check_company=True)
    link_id = fields.Many2one("security.reconciliation.link", ondelete="set null", check_company=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    severity = fields.Selection([( "warning", "Warning"), ("blocking", "Blocking"), ("financial", "Financial")], required=True, default="warning")
    state = fields.Selection([( "open", "Open"), ("assigned", "Assigned"), ("resolved", "Resolved"), ("dismissed", "Dismissed")], required=True, default="open")
    field_diffs_json = fields.Json(default=dict)
    assigned_to_id = fields.Many2one("res.users")
    resolution = fields.Selection([( "use_source", "Use Source"), ("use_target", "Use Target"), ("manual_adjustment", "Manual Adjustment"), ("ignore", "Ignore")])
    resolution_note = fields.Text()
    resolved_by_id = fields.Many2one("res.users", readonly=True)
    resolved_at = fields.Datetime(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        Job = self.env["security.reconciliation.job"]
        for vals in vals_list:
            if vals.get("name") in (False, "New"):
                vals["name"] = sequence.next_by_code("security.reconciliation.conflict") or "New"
            if vals.get("job_id"):
                job = Job.browse(vals["job_id"])
                vals.update({"rule_id": job.rule_id.id, "company_id": job.company_id.id})
        return super().create(vals_list)

    def action_assign_to_me(self):
        self.write({"assigned_to_id": self.env.user.id, "state": "assigned"})

    def action_resolve(self):
        for conflict in self:
            if not conflict.resolution or not conflict.resolution_note:
                raise UserError(_("Choose a resolution and provide an audit note before resolving a conflict."))
            conflict.write({"state": "resolved", "resolved_by_id": self.env.user.id, "resolved_at": fields.Datetime.now()})
