import json
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SecurityEventLog(models.Model):
    _name = "security.event.log"
    _description = "DogForce Intelligence Bus Event Log"
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
    def register_event(self, name, source_model, source_id, event_data=None, payload=None, **kwargs):
        """
        Primary API to broadcast an operational event into the DogForce Intelligence Bus.
        Creates an audit event log and immediately dispatches it to registered loops.
        Accepts both event_data and payload for robust cross-module compatibility.
        """
        data = event_data if event_data is not None else payload
        if data is None and kwargs:
            data = kwargs

        data_str = ""
        if data:
            try:
                data_str = json.dumps(data)
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

    def _get_bus_subscriber_model_names(self):
        """Every installed model inheriting security.bus.subscriber, found
        via the registry rather than a hardcoded list (DG-ADR-018 §2, fixes
        defect D-4). `env.registry` behaves as a mapping of model name ->
        model class."""
        subscriber_cls = type(self.env["security.bus.subscriber"])
        return [
            name for name, cls in self.env.registry.items()
            if name != "security.bus.subscriber" and issubclass(cls, subscriber_cls)
        ]

    def _dispatch_event(self):
        """
        Routes the logged event to every installed security.bus.subscriber
        whose _bus_events includes this event (or declares "*"). Safe
        execution: handles downstream exceptions cleanly without blocking
        the original transaction.
        """
        self.ensure_one()
        payload = {}
        if self.event_data:
            try:
                payload = json.loads(self.event_data)
            except Exception:
                payload = {}

        _logger.info("Intelligence Bus | Dispatched event: %s | Source: %s(%s)", self.name, self.source_model, self.source_id)

        for model_name in self._get_bus_subscriber_model_names():
            model = self.env[model_name]
            bus_events = getattr(model, "_bus_events", [])
            if "*" not in bus_events and self.name not in bus_events:
                continue
            try:
                with self.env.cr.savepoint():
                    model._handle_bus_event(self.name, self.source_model, self.source_id, payload)
            except Exception as e:
                _logger.error("Downstream %s Failed for event %s: %s", model_name, self.name, e)

        self.write({"state": "processed"})
