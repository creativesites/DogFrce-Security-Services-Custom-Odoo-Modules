from odoo import api, fields, models


class SecurityEquipmentReturnWizard(models.TransientModel):
    _name = "security.equipment.return.wizard"
    _description = "Equipment Return Wizard"

    allocation_id = fields.Many2one("security.equipment.allocation", required=True)
    return_date = fields.Date(required=True, default=fields.Date.context_today)
    condition = fields.Selection(
        [("good", "Good — No damage"), ("damaged", "Damaged"), ("lost", "Lost")],
        required=True,
        default="good",
    )
    notes = fields.Text(string="Notes / Damage Description")

    def action_confirm_return(self):
        self.ensure_one()
        alloc = self.allocation_id
        alloc.return_date = self.return_date
        alloc.actual_return_date = self.return_date
        alloc.return_condition = self.condition
        alloc.return_notes = self.notes
        alloc.state = "returned"

        if alloc.is_serialized:
            item_status = "available"
            item_condition = "good"
            if self.condition == "lost":
                item_status = "lost"
                item_condition = "scrapped"
            elif self.condition == "damaged":
                item_status = "maintenance"
                item_condition = "damaged"
            alloc.equipment_item_id.write({
                "status": item_status,
                "condition": item_condition,
            })

        alloc.equipment_type_id._compute_inventory_stats()

        if self.condition in ("damaged", "lost"):
            self.env["security.equipment.damage"].create({
                "allocation_id": alloc.id,
                "occurrence_date": self.return_date,
                "incident_type": "loss" if self.condition == "lost" else "damage",
                "description": self.notes or f"Equipment {self.condition} on return",
                "cost_repair_replace": alloc.equipment_type_id.unit_cost or 1.0,
                "state": "draft",
            })

        return {"type": "ir.actions.act_window_close"}
