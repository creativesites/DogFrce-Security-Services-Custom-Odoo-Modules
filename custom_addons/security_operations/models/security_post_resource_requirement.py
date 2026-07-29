# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SecurityPostResourceRequirement(models.Model):
    _name = "security.post.resource.requirement"
    _description = "Site Post Operational Resource Requirement"
    _order = "is_mandatory desc, resource_category asc, name asc"

    post_id = fields.Many2one(
        "security.post",
        string="Site Post",
        required=True,
        ondelete="cascade",
        index=True,
    )
    resource_category = fields.Selection(
        [
            ("guard", "Security Guard"),
            ("supervisor", "Field Supervisor"),
            ("vehicle", "Patrol Vehicle"),
            ("firearm", "Firearm / Weapon"),
            ("radio", "Two-Way Radio"),
            ("bodycam", "Body Camera"),
            ("keys", "Site Master Keys"),
            ("dog", "K9 Patrol Dog"),
            ("generator", "Backup Generator"),
            ("uniform", "Uniform / Tactical Gear"),
            ("ppe", "PPE Safety Gear"),
            ("mobile", "Patrol Smartphone / Tablet"),
        ],
        string="Resource Category",
        required=True,
        default="guard",
    )
    name = fields.Char(string="Resource Description", required=True)
    qty_required = fields.Integer(string="Quantity Required", default=1, required=True)
    is_mandatory = fields.Boolean(string="Mandatory for Shift", default=True)
    notes = fields.Text(string="Requirements / Specifications")

    @api.onchange("resource_category")
    def _onchange_resource_category(self):
        if self.resource_category and not self.name:
            labels = dict(self._fields["resource_category"].selection)
            self.name = labels.get(self.resource_category, "Resource")
