import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SecurityEventLog(models.Model):
    _name = "security.event.log"
    _description = "DeployGuard Intelligence Bus Event Log"
    _order = "create_date desc, id desc"

    name = fields.Char(
        required=True,
        string="Event Name",
        index=True,
        help="System-wide event identifier (e.g. 'attendance.missed', 'document.expired', 'fleet.delayed').",
    )
    source_model = fields.Char(
        required=True,
        string="Source Model",
        index=True,
    )
    source_id = fields.Integer(
        required=True,
        string="Source Record ID",
        index=True,
    )
    event_data = fields.Text(
        string="Event JSON Data",
        help="Serialized operational metadata payload.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("processed", "Processed"),
            ("failed", "Failed"),
        ],
        default="draft",
        required=True,
        index=True,
    )
    error_message = fields.Text(string="Error Message")

    @api.model
    def register_event(self, name, source_model, source_id, event_data=None):
        """
        Primary API to broadcast an operational event into the DeployGuard Intelligence Bus.
        Creates an audit event log and immediately dispatches it to registered loops.
        """
        data_str = ""
        if event_data:
            try:
                data_str = json.dumps(event_data)
            except Exception as e:
                _logger.warning("Failed to serialize event_data for event %s: %s", name, e)

        log = self.create({
            "name": name,
            "source_model": source_model,
            "source_id": source_id,
            "event_data": data_str,
            "state": "draft",
        })
        log._dispatch_event()
        return log

    def _dispatch_event(self):
        """
        Routes the logged event to active module bridge interceptors.
        Safe execution: handles downstream exceptions cleanly without blocking original transactions.
        """
        self.ensure_one()
        payload = {}
        if self.event_data:
            try:
                payload = json.loads(self.event_data)
            except Exception:
                payload = {}

        _logger.info("Intelligence Bus | Dispatched event: %s | Source: %s(%s)", self.name, self.source_model, self.source_id)

        # 1. CRM Operations Intelligence Loop Bridge
        if "security.operations.crm.bridge" in self.env:
            try:
                self.env["security.operations.crm.bridge"]._handle_bus_event(self.name, self.source_model, self.source_id, payload)
            except Exception as e:
                _logger.error("Downstream CRM Loop Failed for event %s: %s", self.name, e)

        # 2. Reliability, Attendance, and Discipline Loop Bridge
        if "security.discipline.payroll.bridge" in self.env:
            try:
                self.env["security.discipline.payroll.bridge"]._handle_bus_event(self.name, self.source_model, self.source_id, payload)
            except Exception as e:
                _logger.error("Downstream Discipline Loop Failed for event %s: %s", self.name, e)

        # 3. Fleet delay and Route Attendance Bridge
        if "security.fleet.ops.bridge" in self.env:
            try:
                self.env["security.fleet.ops.bridge"]._handle_bus_event(self.name, self.source_model, self.source_id, payload)
            except Exception as e:
                _logger.error("Downstream Fleet Ops Loop Failed for event %s: %s", self.name, e)

        # 4. Equipment, Damage Repairs, and Payroll Bridge
        if "security.equipment.payroll.bridge" in self.env:
            try:
                self.env["security.equipment.payroll.bridge"]._handle_bus_event(self.name, self.source_model, self.source_id, payload)
            except Exception as e:
                _logger.error("Downstream Equipment Loop Failed for event %s: %s", self.name, e)

        # 5. Document compliance warnings Bridge
        if "security.compliance.roster.bridge" in self.env:
            try:
                self.env["security.compliance.roster.bridge"]._handle_bus_event(self.name, self.source_model, self.source_id, payload)
            except Exception as e:
                _logger.error("Downstream Compliance Roster Loop Failed for event %s: %s", self.name, e)

        self.write({"state": "processed"})
