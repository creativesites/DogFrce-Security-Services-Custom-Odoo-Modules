import logging
from datetime import datetime
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SecurityShuttleRun(models.Model):
    _inherit = "security.shuttle.run"

    delay_minutes = fields.Integer(string="Delay Duration (Minutes)", default=0)
    delay_reason = fields.Char(string="Delay Reason")

    def action_report_delay(self, minutes, reason):
        """
        Reports a transit delay on an active shuttle run, calculates affected client sites
        and scheduled guard shifts, and dispatches a central intelligence warning event.
        """
        for run in self:
            run.write({
                "delay_minutes": minutes,
                "delay_reason": reason,
            })

            # Gather affected passenger employee IDs
            passenger_employees = run.passenger_ids.filtered(lambda p: p.status == "boarded").mapped("employee_id")
            if not passenger_employees:
                continue

            # Check if there's any active roster slots for these guards today
            today = fields.Date.today()
            roster_slots = self.env["security.roster.slot"].search([
                ("employee_id", "in", passenger_employees.ids),
                ("shift_date", "=", today),
            ])

            affected_sites = []
            for slot in roster_slots:
                site_name = slot.site_id.name if slot.site_id else _("Unknown Site")
                post_name = slot.post_id.name if slot.post_id else _("Unknown Post")
                guard_name = slot.employee_id.name
                affected_sites.append(f"{guard_name} ({site_name} - {post_name})")

            payload = {
                "run_name": run.name,
                "vehicle": run.vehicle_id.name,
                "driver": run.driver_id.name,
                "minutes": minutes,
                "reason": reason,
                "affected_sites": affected_sites,
                "passenger_count": len(passenger_employees),
            }

            # Register intelligence event
            self.env["security.event.log"].register_event(
                name="fleet.shuttle_delayed",
                source_model="security.shuttle.run",
                source_id=run.id,
                payload=payload,
            )


class SecurityVehicle(models.Model):
    _inherit = "security.vehicle"

    def write(self, vals):
        """
        Listens to state changes on vehicles and fires central intelligence breakdown alerts.
        """
        res = super().write(vals)

        if "state" in vals and vals["state"] in ["maintenance", "broken_down"]:
            for vehicle in self:
                # Find if vehicle is currently assigned to an active shuttle run
                active_runs = self.env["security.shuttle.run"].search([
                    ("vehicle_id", "=", vehicle.id),
                    ("state", "in", ["boarding", "in_transit"]),
                ])

                payload = {
                    "vehicle_name": vehicle.name,
                    "state": vals["state"],
                    "odometer": vehicle.odometer,
                    "active_runs": active_runs.mapped("name"),
                }

                # Register intelligence event
                self.env["security.event.log"].register_event(
                    name="fleet.breakdown",
                    source_model="security.vehicle",
                    source_id=vehicle.id,
                    payload=payload,
                )

        return res


class SecurityFleetOpsBridge(models.AbstractModel):
    _name = "security.fleet.ops.bridge"
    _description = "Security Fleet and Operations Intelligence Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """
        Handles fleet events from the central intelligence bus, raising dispatch alerts.
        """
        _logger.info("Fleet Ops Bridge | Processing event: %s", event_name)

        if event_name == "fleet.shuttle_delayed":
            run_name = payload.get("run_name", "")
            minutes = payload.get("minutes", 0)
            reason = payload.get("reason", "")
            affected = payload.get("affected_sites", [])

            _logger.warning("Fleet Ops Bridge | Shuttle Run %s delayed by %s mins. Reason: %s", run_name, minutes, reason)

            # Create an operational task or log to alert operations dispatchers
            alert_msg = _(
                "CRITICAL TRANSIT DELAY:\nShuttle Run %s has reported a delay of %s minutes due to: %s.\n\n"
                "The following guards and sites are affected by potential late arrival:\n"
            ) % (run_name, minutes, reason)

            for aff in affected:
                alert_msg += f"- {aff}\n"

            # Post a global channel log or log an operational message
            # We can find or create an alert channel or log it to the event logs
            self.env["security.event.log"].create({
                "name": f"TRANSIT DELAY WARNING: {run_name}",
                "event_type": "transit_delay",
                "severity": "medium",
                "description": alert_msg,
            })

        elif event_name == "fleet.breakdown":
            vehicle_name = payload.get("vehicle_name", "")
            state = payload.get("state", "")
            active_runs = payload.get("active_runs", [])

            _logger.critical("Fleet Ops Bridge | Vehicle %s went out of service! Status: %s", vehicle_name, state)

            alert_msg = _(
                "VEHICLE OUT OF SERVICE ALERT:\nVehicle %s is marked as: %s.\n\n"
            ) % (vehicle_name, state.replace("_", " ").upper())

            if active_runs:
                alert_msg += _("CRITICAL: This vehicle is currently assigned to active runs: %s! Standby replacement vehicle required immediately.") % ", ".join(active_runs)
                severity = "high"
            else:
                alert_msg += _("Vehicle is not currently assigned to active runs.")
                severity = "low"

            self.env["security.event.log"].create({
                "name": f"VEHICLE OUT OF SERVICE: {vehicle_name}",
                "event_type": "vehicle_breakdown",
                "severity": severity,
                "description": alert_msg,
            })
