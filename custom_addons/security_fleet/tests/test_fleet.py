from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta


class TestSecurityFleet(TransactionCase):

    def setUp(self):
        super().setUp()

        # Create test guards/drivers
        self.driver = self.env["hr.employee"].create({
            "name": "Johannes Nangolo",
            "security_guard": True,
        })
        self.guard_1 = self.env["hr.employee"].create({
            "name": "Petrus Shilongo",
            "security_guard": True,
        })
        self.guard_2 = self.env["hr.employee"].create({
            "name": "Maria Angula",
            "security_guard": True,
        })

        # Create a vehicle
        self.vehicle = self.env["security.vehicle"].create({
            "plate_number": "N 12345 W",
            "make": "Toyota",
            "model": "Hiace",
            "year": 2021,
            "capacity": 14,
            "odometer": 50000.0,
            "assigned_driver_id": self.driver.id,
        })

        # Create a route with 2 stops
        self.route = self.env["security.shuttle.route"].create({
            "name": "Morning Northern Circuit",
            "route_type": "pickup",
            "stop_ids": [
                (0, 0, {"sequence": 10, "stop_label": "Katutura Taxi Rank", "stop_type": "pickup", "cumulative_duration_mins": 10}),
                (0, 0, {"sequence": 20, "stop_label": "Klein Windhoek Guard Post", "stop_type": "site", "cumulative_duration_mins": 35}),
            ],
        })

    # ─────────────────────────────────────────────────────────────────────
    def test_01_inspection_pass_does_not_ground_vehicle(self):
        """A passing inspection keeps the vehicle available."""
        self.env["security.vehicle.inspection"].create({
            "vehicle_id": self.vehicle.id,
            "inspected_by_id": self.driver.id,
            "odometer_reading": 50100.0,
        })
        self.assertEqual(self.vehicle.state, "available")

    def test_02_inspection_fail_grounds_vehicle(self):
        """A failed inspection auto-transitions vehicle to in_service."""
        self.env["security.vehicle.inspection"].create({
            "vehicle_id": self.vehicle.id,
            "inspected_by_id": self.driver.id,
            "check_brakes": "fail",
            "odometer_reading": 50100.0,
        })
        self.assertEqual(self.vehicle.state, "in_service")

    def test_03_grounded_vehicle_blocks_boarding(self):
        """A vehicle in_service cannot start boarding on a run."""
        self.vehicle.state = "in_service"
        run = self.env["security.shuttle.run"].create({
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
            "route_id": self.route.id,
            "shift_date": date.today(),
        })
        with self.assertRaises(ValidationError):
            run.action_start_boarding()

    def test_04_full_shuttle_run_lifecycle(self):
        """Test the full run: draft → boarding → in_transit → completed."""
        run = self.env["security.shuttle.run"].create({
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
            "route_id": self.route.id,
            "shift_date": date.today(),
            "odometer_start": 50100.0,
            "passenger_ids": [
                (0, 0, {"employee_id": self.guard_1.id, "status": "expected"}),
                (0, 0, {"employee_id": self.guard_2.id, "status": "expected"}),
            ],
        })
        self.assertEqual(run.state, "draft")
        self.assertEqual(run.total_passengers, 2)

        # Start boarding — vehicle goes in_transit
        run.action_start_boarding()
        self.assertEqual(run.state, "boarding")
        self.assertEqual(self.vehicle.state, "in_transit")

        # Mark passenger statuses
        run.passenger_ids[0].status = "boarded"
        run.passenger_ids[1].status = "no_show"

        # Depart
        run.action_depart()
        self.assertEqual(run.state, "in_transit")
        self.assertIsNotNone(run.actual_departure)

        # Complete — requires odometer_end
        run.odometer_end = 50145.0
        run.action_complete()
        self.assertEqual(run.state, "completed")
        self.assertEqual(run.km_driven, 45.0)
        # Vehicle odometer updated
        self.assertAlmostEqual(self.vehicle.odometer, 50145.0)
        # Vehicle released back to available
        self.assertEqual(self.vehicle.state, "available")
        # no_show count
        self.assertEqual(run.no_show_count, 1)
        self.assertEqual(run.boarded_count, 1)

    def test_05_odometer_validation(self):
        """Odometer end cannot be less than start."""
        run = self.env["security.shuttle.run"].create({
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
            "route_id": self.route.id,
            "shift_date": date.today(),
            "odometer_start": 50200.0,
        })
        with self.assertRaises(ValidationError):
            run.odometer_end = 50100.0
            run._check_odometer()

    def test_06_fuel_log_updates_odometer(self):
        """Fuel log with higher odometer updates vehicle odometer."""
        self.env["security.vehicle.fuel.log"].create({
            "vehicle_id": self.vehicle.id,
            "fuel_date": date.today(),
            "fueled_by_id": self.driver.id,
            "odometer_reading": 51500.0,
            "liters": 60.0,
            "cost_per_liter": 25.50,
        })
        self.assertAlmostEqual(self.vehicle.odometer, 51500.0)

    def test_07_fuel_log_total_cost(self):
        """Fuel total cost = liters × cost_per_liter."""
        log = self.env["security.vehicle.fuel.log"].create({
            "vehicle_id": self.vehicle.id,
            "fuel_date": date.today(),
            "fueled_by_id": self.driver.id,
            "odometer_reading": 50500.0,
            "liters": 40.0,
            "cost_per_liter": 27.00,
        })
        self.assertAlmostEqual(log.total_cost, 1080.0)

    def test_08_service_log_completes_and_releases_vehicle(self):
        """Completing a service log returns the vehicle to available."""
        self.vehicle.state = "in_service"
        service = self.env["security.vehicle.service.log"].create({
            "vehicle_id": self.vehicle.id,
            "service_provider": "Windhoek Auto Repairs",
            "date_in": date.today(),
            "description": "Full service + brake pad replacement",
            "cost": 3500.0,
            "odometer_at_service": 52000.0,
        })
        self.assertEqual(service.state, "open")
        service.action_complete_service()
        self.assertEqual(service.state, "completed")
        self.assertEqual(self.vehicle.state, "available")
        self.assertAlmostEqual(self.vehicle.odometer, 52000.0)

    def test_09_incident_linked_to_vehicle_and_run(self):
        """An incident can reference a specific vehicle and shuttle run."""
        incident_type = self.env["security.incident.type"].create({
            "name": "Vehicle Accident",
            "code": "ACCIDENT",
        })
        run = self.env["security.shuttle.run"].create({
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
            "route_id": self.route.id,
            "shift_date": date.today(),
        })
        incident = self.env["security.incident"].create({
            "employee_id": self.driver.id,
            "incident_type_id": incident_type.id,
            "incident_date": date.today(),
            "vehicle_id": self.vehicle.id,
            "shuttle_run_id": run.id,
        })
        self.assertEqual(incident.vehicle_id.id, self.vehicle.id)
        self.assertEqual(incident.shuttle_run_id.id, run.id)
        self.assertEqual(self.vehicle.incident_count, 1)
