from odoo import api, fields, models


class SecurityWorkChecklistTemplate(models.Model):
    _name = "security.work.checklist.template"
    _description = "Work Checklist Template"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(help="Stable machine key, e.g. 'site.visit' — used to look up this template from other modules without relying on the record's display name.")
    description = fields.Text()
    active = fields.Boolean(default=True)
    item_ids = fields.One2many("security.work.checklist.item.def", "template_id", string="Items")
    item_count = fields.Integer(compute="_compute_item_count")

    _code_unique = models.Constraint(
        "unique(code)",
        "A checklist template with this code already exists.",
    )

    @api.depends("item_ids")
    def _compute_item_count(self):
        for template in self:
            template.item_count = len(template.item_ids)


class SecurityWorkChecklistItemDef(models.Model):
    _name = "security.work.checklist.item.def"
    _description = "Work Checklist Item Definition"
    _order = "template_id, sequence, id"

    template_id = fields.Many2one("security.work.checklist.template", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    label = fields.Char(required=True)
    item_type = fields.Selection(
        [
            ("boolean", "Yes / No"),
            ("text", "Text"),
            ("number", "Number"),
            ("photo", "Photo evidence"),
        ],
        default="boolean",
        required=True,
    )
    required = fields.Boolean(default=True)
    help_text = fields.Char()


class SecurityWorkChecklistResponse(models.Model):
    _name = "security.work.checklist.response"
    _description = "Work Checklist Response"
    _order = "item_def_id"

    task_id = fields.Many2one("security.work.task", required=True, ondelete="cascade")
    item_def_id = fields.Many2one("security.work.checklist.item.def", required=True, ondelete="restrict")
    label = fields.Char(related="item_def_id.label", string="Item", readonly=True)
    item_type = fields.Selection(related="item_def_id.item_type", readonly=True)
    value_bool = fields.Boolean()
    value_text = fields.Char()
    value_number = fields.Float()
    photo = fields.Binary(attachment=True)
    note = fields.Char()

    _task_item_unique = models.Constraint(
        "unique(task_id, item_def_id)",
        "This item already has a response on this task.",
    )
