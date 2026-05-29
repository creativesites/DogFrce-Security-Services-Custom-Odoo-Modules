from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityDocumentType(models.Model):
    _name = "security.document.type"
    _description = "Security Document Type"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char()
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [
            ("identity", "Identity"),
            ("employment", "Employment"),
            ("training", "Training"),
            ("medical", "Medical"),
            ("clearance", "Clearance"),
            ("client", "Client Requirement"),
            ("other", "Other"),
        ],
        default="other",
        required=True,
    )
    expiry_required = fields.Boolean(default=False)
    default_validity_months = fields.Integer()
    required_for_active_guard = fields.Boolean(default=False)
    required_for_firearm_post = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    note = fields.Text()

    @api.constrains("default_validity_months")
    def _check_validity_months(self):
        for document_type in self:
            if document_type.default_validity_months < 0:
                raise ValidationError("Default validity months cannot be negative.")


class SecurityEmployeeDocument(models.Model):
    _name = "security.employee.document"
    _description = "Security Employee Document"
    _order = "expiry_date, employee_id, document_type_id"

    name = fields.Char(compute="_compute_name", store=True)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
    )
    document_type_id = fields.Many2one("security.document.type", required=True)
    document_number = fields.Char()
    issue_date = fields.Date()
    expiry_date = fields.Date()
    issuing_authority = fields.Char()
    attachment = fields.Binary()
    attachment_filename = fields.Char()
    verified_by_id = fields.Many2one("res.users")
    verified_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("verified", "Verified"),
            ("expired", "Expired"),
            ("rejected", "Rejected"),
        ],
        compute="_compute_state",
        inverse="_inverse_state",
        store=True,
    )
    manual_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("verified", "Verified"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
    )
    days_to_expiry = fields.Integer(compute="_compute_expiry_status", store=True)
    expiry_status = fields.Selection(
        [
            ("no_expiry", "No Expiry"),
            ("valid", "Valid"),
            ("expiring", "Expiring Soon"),
            ("expired", "Expired"),
        ],
        compute="_compute_expiry_status",
        store=True,
    )
    note = fields.Text()

    @api.depends("employee_id", "document_type_id", "document_number")
    def _compute_name(self):
        for document in self:
            parts = [
                document.employee_id.name or "",
                document.document_type_id.name or "",
                document.document_number or "",
            ]
            document.name = " - ".join(part for part in parts if part) or "Employee Document"

    @api.depends("expiry_date")
    def _compute_expiry_status(self):
        today = fields.Date.context_today(self)
        for document in self:
            if not document.expiry_date:
                document.days_to_expiry = 0
                document.expiry_status = "no_expiry"
                continue
            days = (document.expiry_date - today).days
            document.days_to_expiry = days
            if days < 0:
                document.expiry_status = "expired"
            elif days <= 30:
                document.expiry_status = "expiring"
            else:
                document.expiry_status = "valid"

    @api.depends("manual_state", "expiry_status")
    def _compute_state(self):
        for document in self:
            if document.expiry_status == "expired":
                document.state = "expired"
            else:
                document.state = document.manual_state

    def _inverse_state(self):
        for document in self:
            if document.state in ("draft", "verified", "rejected"):
                document.manual_state = document.state

    @api.constrains("issue_date", "expiry_date", "document_type_id")
    def _check_dates(self):
        for document in self:
            if document.expiry_date and document.issue_date and document.expiry_date < document.issue_date:
                raise ValidationError("Document expiry date cannot be earlier than issue date.")
            if document.document_type_id.expiry_required and not document.expiry_date:
                raise ValidationError("This document type requires an expiry date.")

    def action_verify(self):
        for document in self:
            if document.expiry_status == "expired":
                raise ValidationError("Expired documents cannot be verified.")
            document.manual_state = "verified"
            document.verified_by_id = self.env.user
            document.verified_date = fields.Date.context_today(self)

    def action_reject(self):
        for document in self:
            document.manual_state = "rejected"

    def action_reset_to_draft(self):
        for document in self:
            document.manual_state = "draft"


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    security_document_ids = fields.One2many(
        "security.employee.document",
        "employee_id",
        string="Security Documents",
    )
    security_document_count = fields.Integer(
        compute="_compute_security_document_count",
    )
    security_expiring_document_count = fields.Integer(
        compute="_compute_security_document_count",
    )

    def _compute_security_document_count(self):
        for employee in self:
            documents = employee.security_document_ids
            employee.security_document_count = len(documents)
            employee.security_expiring_document_count = len(
                documents.filtered(lambda doc: doc.expiry_status in ("expiring", "expired"))
            )
