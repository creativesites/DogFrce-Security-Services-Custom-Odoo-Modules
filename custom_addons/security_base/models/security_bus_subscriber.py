from odoo import models


class SecurityBusSubscriber(models.AbstractModel):
    """Mixin for anything that wants to react to security.event.log events.

    Replaces the hardcoded 5-bridge dispatch list in
    security.event.log._dispatch_event (defect D-4, DG-ADR-018 §2): any
    installed model inheriting this mixin gets called automatically, so
    security.mobile.bridge and security.portal.bridge (which implemented
    _handle_bus_event but were never invoked) now actually receive events.

    Subclasses set `_bus_events` to the event names they care about, or
    `["*"]` for all of them, and implement `_handle_bus_event`.
    """

    _name = "security.bus.subscriber"
    _description = "Intelligence Bus Subscriber"

    _bus_events = []

    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        raise NotImplementedError(
            f"{self._name} inherits security.bus.subscriber but does not "
            "implement _handle_bus_event."
        )
