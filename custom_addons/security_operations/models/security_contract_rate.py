from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityContractRate(models.Model):
    _name = "security.contract.rate"
    _description = "Contract Billing Rate"
    _order = "shift_category, grade_id"
    _rec_name = "shift_category"

    contract_id = fields.Many2one(
        "security.client.contract",
        required=True,
        ondelete="cascade",
    )
    shift_category = fields.Selection(
        [
            ("normal", "Normal / Day"),
            ("night", "Night"),
            ("saturday", "Saturday"),
            ("sunday", "Sunday"),
            ("public_holiday", "Public Holiday"),
        ],
        required=True,
        string="Shift Category",
    )
    grade_id = fields.Many2one(
        "security.grade",
        string="Grade",
        help="Leave blank to apply this rate to all grades for this category.",
    )
    hourly_rate = fields.Float(
        required=True,
        string="Rate (N$/hr)",
        digits=(10, 2),
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="contract_id.currency_id",
        string="Currency",
    )

    @api.constrains("contract_id", "shift_category", "grade_id")
    def _check_unique_rate(self):
        for rate in self:
            domain = [
                ("contract_id", "=", rate.contract_id.id),
                ("shift_category", "=", rate.shift_category),
                ("id", "!=", rate.id),
            ]
            if rate.grade_id:
                domain.append(("grade_id", "=", rate.grade_id.id))
            else:
                domain.append(("grade_id", "=", False))
            if self.search_count(domain):
                grade_label = rate.grade_id.name if rate.grade_id else "All Grades"
                raise ValidationError(
                    f"A '{rate.shift_category}' rate for '{grade_label}' "
                    "already exists on this contract."
                )
