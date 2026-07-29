# -*- coding: utf-8 -*-
from odoo import models, fields, api

class SecurityRosterSlotResource(models.Model):
    _name = "security.roster.slot.resource"
    _description = "Roster Slot Allocated Resource"
    _order = "is_mandatory desc, resource_category asc, name asc"

    slot_id = fields.Many2one(
        "security.roster.slot",
        string="Roster Slot",
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
    qty_required = fields.Integer(string="Required Qty", default=1, required=True)
    qty_allocated = fields.Integer(
        string="Allocated Qty",
        compute="_compute_allocation",
        store=True,
    )
    is_mandatory = fields.Boolean(string="Mandatory", default=True)
    is_fulfilled = fields.Boolean(
        string="Fulfilled",
        compute="_compute_allocation",
        store=True,
    )

    notes = fields.Text(string="Allocation Notes")

    def _compute_allocation(self):
        for rec in self:
            if rec.resource_category in ["guard", "supervisor"]:
                rec.qty_allocated = 1 if rec.slot_id.employee_id else 0
            elif rec.resource_category == "vehicle" and hasattr(rec, "vehicle_id"):
                rec.qty_allocated = 1 if rec.vehicle_id else 0
            elif hasattr(rec, "equipment_ids"):
                rec.qty_allocated = len(getattr(rec, "equipment_ids", []))
            else:
                rec.qty_allocated = 0
            rec.is_fulfilled = rec.qty_allocated >= rec.qty_required
