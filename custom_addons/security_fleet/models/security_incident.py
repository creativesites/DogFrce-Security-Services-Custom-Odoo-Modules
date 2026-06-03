from odoo import fields, models


class SecurityIncident(models.Model):
    """Extend security.incident to link road incidents to a specific vehicle and shuttle run."""
    _inherit = "security.incident"

    vehicle_id = fields.Many2one(
        "security.vehicle",
        string="Vehicle Involved",
        ondelete="set null",
        help="Link this incident to a specific fleet vehicle (e.g. accident, breakdown during transport).",
    )
    shuttle_run_id = fields.Many2one(
        "security.shuttle.run",
        string="Shuttle Run",
        ondelete="set null",
        domain="[('vehicle_id', '=', vehicle_id)]",
        help="Link to the specific transport run during which this incident occurred.",
    )


class SecurityVehicle(models.Model):
    """Add incident smart button count back on the vehicle form."""
    _inherit = "security.vehicle"

    incident_ids = fields.One2many(
        "security.incident",
        "vehicle_id",
        string="Fleet Incidents",
    )
    incident_count = fields.Integer(compute="_compute_incident_count")

    def _compute_incident_count(self):
        for v in self:
            v.incident_count = self.env["security.incident"].search_count(
                [("vehicle_id", "=", v.id)]
            )

    def action_view_incidents(self):
        self.ensure_one()
        return {
            "name": "Fleet Incidents",
            "type": "ir.actions.act_window",
            "res_model": "security.incident",
            "view_mode": "list,form",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {"default_vehicle_id": self.id},
        }
