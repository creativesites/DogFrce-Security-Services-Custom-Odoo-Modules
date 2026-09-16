from odoo import api, models


class SecurityResponseMap(models.AbstractModel):
    """Data provider for the Live Callout Map OWL component. Kept separate
    from security.response.unit so the map's read shape can evolve
    independently of the unit model."""
    _name = "security.response.map"
    _description = "Live Callout Map Data Provider"

    @api.model
    def get_map_data(self):
        config = self.env["ir.config_parameter"].sudo()
        api_key = config.get_param("security_armed_response.gmaps_api_key", "")

        units = self.env["security.response.unit"].search([("active", "=", True)])
        unit_payload = [
            {
                "id": unit.id,
                "name": unit.name,
                "status": unit.status,
                "lat": unit.last_lat,
                "lng": unit.last_lng,
                "last_position_at": unit.last_position_at and str(unit.last_position_at) or None,
                "is_stale": unit.position_is_stale,
                "commander": unit.commander_id.name or "",
                "active_dispatch_id": unit.active_dispatch_id.id or False,
                "active_dispatch_name": unit.active_dispatch_id.name or "",
            }
            for unit in units
            if unit.last_lat and unit.last_lng
        ]

        open_dispatches = self.env["security.response.dispatch"].search([
            ("state", "not in", ("resolved", "cancelled")),
        ])
        dispatch_payload = [
            {
                "id": dispatch.id,
                "name": dispatch.name,
                "state": dispatch.state,
                "priority": dispatch.priority,
                "site_id": dispatch.site_id.id,
                "site_name": dispatch.site_id.name or "",
                "lat": dispatch.site_id.gps_lat,
                "lng": dispatch.site_id.gps_lng,
                "unit_id": dispatch.unit_id.id or False,
                "unit_name": dispatch.unit_id.name or "",
            }
            for dispatch in open_dispatches
            if dispatch.site_id.gps_lat and dispatch.site_id.gps_lng
        ]

        return {
            "api_key": api_key,
            "units": unit_payload,
            "dispatches": dispatch_payload,
        }
