from odoo.tests.common import TransactionCase


class TestBusDispatch(TransactionCase):
    """docs/deployguard/adr/DG-ADR-018-odoo-bridge-addons.md §2 (fixes D-4).
    The dispatcher must find subscribers via the registry, not a hardcoded
    list -- and must call every one of them, including the two that used
    to be dead code (security.mobile.bridge, security.portal.bridge).

    These tests monkey-patch real bridge models from other addons rather
    than a dummy fixture, since Odoo doesn't cleanly support registering a
    throwaway model at test time. security_base does not depend on those
    addons, so each test skips (rather than erroring) if they aren't
    installed in whatever database runs this suite.
    """

    def setUp(self):
        super().setUp()
        if "security.mobile.bridge" not in self.env.registry:
            self.skipTest("security_mobile_bridge not installed in this database")

    def test_dispatch_calls_a_real_bridge(self):
        calls = []
        Bridge = self.env.registry["security.mobile.bridge"]
        original = Bridge._handle_bus_event

        def recording_handler(self, event_name, source_model, source_id, payload):
            calls.append(event_name)

        Bridge._handle_bus_event = recording_handler
        try:
            self.env["security.event.log"].register_event(
                "test.event", "res.partner", 1, {"x": 1}
            )
        finally:
            Bridge._handle_bus_event = original

        self.assertIn("test.event", calls)

    def test_subscriber_not_matching_event_is_skipped(self):
        calls = []
        Bridge = self.env.registry["security.mobile.bridge"]
        original_events = Bridge._bus_events
        original_handler = Bridge._handle_bus_event

        Bridge._bus_events = ["only.this.event"]
        Bridge._handle_bus_event = lambda self, *a: calls.append(a[0])
        try:
            self.env["security.event.log"].register_event(
                "some.other.event", "res.partner", 1, {}
            )
        finally:
            Bridge._bus_events = original_events
            Bridge._handle_bus_event = original_handler

        self.assertEqual(calls, [])

    def test_one_failing_subscriber_does_not_block_another(self):
        calls = []
        Mobile = self.env.registry["security.mobile.bridge"]
        Portal = self.env.registry["security.portal.bridge"]
        orig_mobile, orig_portal = Mobile._handle_bus_event, Portal._handle_bus_event

        def boom(self, *a):
            raise RuntimeError("simulated failure")

        Mobile._handle_bus_event = boom
        Portal._handle_bus_event = lambda self, *a: calls.append("portal")
        try:
            log = self.env["security.event.log"].register_event(
                "test.event", "res.partner", 1, {}
            )
        finally:
            Mobile._handle_bus_event = orig_mobile
            Portal._handle_bus_event = orig_portal

        self.assertIn("portal", calls)
        self.assertEqual(log.state, "processed", "one bad subscriber must not fail the event")

    def test_get_bus_subscriber_model_names_finds_installed_bridges(self):
        """Asserts against whichever of the seven known bridges are actually
        installed in this database, rather than assuming all seven are --
        security_base depends on none of them."""
        names = set(self.env["security.event.log"]._get_bus_subscriber_model_names())
        known_bridges = {
            "security.operations.crm.bridge",
            "security.discipline.payroll.bridge",
            "security.fleet.ops.bridge",
            "security.equipment.payroll.bridge",
            "security.compliance.roster.bridge",
            "security.mobile.bridge",
            "security.portal.bridge",
        }
        installed_known_bridges = {
            name for name in known_bridges if name in self.env.registry
        }
        self.assertTrue(installed_known_bridges, "expected at least one bridge installed")
        self.assertTrue(installed_known_bridges.issubset(names))
        self.assertNotIn("security.bus.subscriber", names, "the mixin must not call itself")
