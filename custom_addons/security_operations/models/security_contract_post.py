from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SecurityContractPost(models.Model):
    _name = "security.contract.post"
    _description = "Contract Post Definition"
    _order = "sequence, id"

    contract_id = fields.Many2one(
        "security.client.contract",
        related="contract_site_id.contract_id",
        store=True,
        index=True,
        string="Contract",
    )
    contract_site_id = fields.Many2one(
        "security.contract.site",
        required=True,
        ondelete="cascade",
        index=True,
        string="Contract Site",
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True, string="Post Name", placeholder="e.g. Main Gate")
    code = fields.Char(string="Post Code")
    post_type_id = fields.Many2one(
        "security.post.type",
        string="Post Type",
        help="Category defining standard attributes, certifications, and requirements.",
    )
    min_grade_id = fields.Many2one(
        "security.grade",
        string="Minimum Grade",
        help="Minimum guard qualification required for this post.",
    )
    required_guard_count = fields.Integer(
        string="Positions / Guards",
        default=1,
        help="Number of guards needed concurrently on this post.",
    )
    post_id = fields.Many2one(
        "security.post",
        string="Linked Operational Post",
        ondelete="set null",
        help="The active operational post record managed by this contract line.",
    )
    requirement_line_ids = fields.One2many(
        "security.contract.shift.requirement",
        "contract_post_id",
        string="Shift Requirements",
    )
    note = fields.Text("Notes")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code"):
                count = self.search_count([]) + 1
                vals["code"] = f"PST-{count:03d}"
            # If post_type_id not provided, try to find or create one from name
            if not vals.get("post_type_id") and vals.get("name"):
                name = vals["name"].strip()
                post_type = self.env["security.post.type"].search([("name", "=ilike", name)], limit=1)
                if not post_type:
                    post_type = self.env["security.post.type"].create({"name": name})
                vals["post_type_id"] = post_type.id
        return super().create(vals_list)

    def action_duplicate_post(self):
        """Duplicate post and its shift requirements under the same site."""
        self.ensure_one()
        new_post = self.copy({
            "name": f"{self.name} (Copy)",
            "code": False,
            "post_id": False,
        })
        for req in self.requirement_line_ids:
            req.copy({
                "contract_post_id": new_post.id,
                "requirement_id": False,
            })
        return True
