from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date, datetime


# ─────────────────────────────────────────────────────────────────────────────
# VEHICLE MASTER REGISTER
# ─────────────────────────────────────────────────────────────────────────────

class SecurityVehicle(models.Model):
    _name = "security.vehicle"
    _description = "Fleet Vehicle"
    _order = "plate_number"

    name = fields.Char(compute="_compute_name", store=True)
    plate_number = fields.Char(required=True, string="Registration Plate")
    make = fields.Char(required=True, string="Make / Brand", placeholder="e.g. Toyota")
    model = fields.Char(required=True, string="Model", placeholder="e.g. Hilux")
    year = fields.Integer(string="Year of Manufacture", default=2020)
    colour = fields.Char()
    capacity = fields.Integer(string="Seating Capacity (excl. driver)", default=8)
    odometer = fields.Float(string="Current Odometer (km)", default=0.0)
    state = fields.Selection(
        [
            ("available", "Available"),
            ("in_transit", "In Transit"),
            ("in_service", "In Service / Maintenance"),
            ("scrapped", "Decommissioned"),
        ],
        default="available",
        required=True,
        string="Vehicle Status",
    )
    assigned_driver_id = fields.Many2one(
        "hr.employee",
        string="Primary Driver",
        domain=[("security_guard", "=", True)],
    )
    active = fields.Boolean(default=True)
    notes = fields.Text()

    # Computed stat fields for button box
    fuel_log_count = fields.Integer(compute="_compute_counts")
    service_log_count = fields.Integer(compute="_compute_counts")
    inspection_count = fields.Integer(compute="_compute_counts")
    run_count = fields.Integer(compute="_compute_counts")
    total_fuel_cost = fields.Float(compute="_compute_total_fuel_cost", string="Total Fuel Cost (NAD)")

    @api.depends("plate_number", "make", "model")
    def _compute_name(self):
        for v in self:
            v.name = f"{v.plate_number} – {v.make} {v.model}".strip(" –")

    def _compute_counts(self):
        FuelLog = self.env["security.vehicle.fuel.log"]
        ServiceLog = self.env["security.vehicle.service.log"]
        Inspection = self.env["security.vehicle.inspection"]
        Run = self.env["security.shuttle.run"]
        for v in self:
            v.fuel_log_count = FuelLog.search_count([("vehicle_id", "=", v.id)])
            v.service_log_count = ServiceLog.search_count([("vehicle_id", "=", v.id)])
            v.inspection_count = Inspection.search_count([("vehicle_id", "=", v.id)])
            v.run_count = Run.search_count([("vehicle_id", "=", v.id)])

    def _compute_total_fuel_cost(self):
        FuelLog = self.env["security.vehicle.fuel.log"]
        for v in self:
            logs = FuelLog.search([("vehicle_id", "=", v.id)])
            v.total_fuel_cost = sum(logs.mapped("total_cost"))

    def action_send_to_service(self):
        for v in self:
            v.state = "in_service"

    def action_mark_available(self):
        for v in self:
            v.state = "available"

    def action_decommission(self):
        for v in self:
            v.state = "scrapped"
            v.active = False

    def action_view_runs(self):
        self.ensure_one()
        return {
            "name": "Shuttle Runs",
            "type": "ir.actions.act_window",
            "res_model": "security.shuttle.run",
            "view_mode": "list,form",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {"default_vehicle_id": self.id},
        }

    def action_view_fuel_logs(self):
        self.ensure_one()
        return {
            "name": "Fuel Logs",
            "type": "ir.actions.act_window",
            "res_model": "security.vehicle.fuel.log",
            "view_mode": "list,form",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {"default_vehicle_id": self.id},
        }

    def action_view_service_logs(self):
        self.ensure_one()
        return {
            "name": "Service Logs",
            "type": "ir.actions.act_window",
            "res_model": "security.vehicle.service.log",
            "view_mode": "list,form",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {"default_vehicle_id": self.id},
        }

    def action_view_inspections(self):
        self.ensure_one()
        return {
            "name": "Inspections",
            "type": "ir.actions.act_window",
            "res_model": "security.vehicle.inspection",
            "view_mode": "list,form",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {"default_vehicle_id": self.id},
        }


# ─────────────────────────────────────────────────────────────────────────────
# SHUTTLE ROUTES (Prearranged, reusable)
# ─────────────────────────────────────────────────────────────────────────────

class SecurityShuttleRoute(models.Model):
    _name = "security.shuttle.route"
    _description = "Prearranged Shuttle Route"
    _order = "name"

    name = fields.Char(required=True, placeholder="e.g. Morning Northern Circuit")
    route_type = fields.Selection(
        [
            ("pickup", "Morning Pick-Up (Depot → Sites)"),
            ("dropoff", "Evening Drop-Off (Sites → Depot)"),
            ("rotation", "Mid-Shift Rotation"),
        ],
        required=True,
        default="pickup",
        string="Route Type",
    )
    stop_ids = fields.One2many(
        "security.shuttle.route.stop",
        "route_id",
        string="Route Stops",
    )
    total_stops = fields.Integer(compute="_compute_total_stops", store=True)
    estimated_duration_mins = fields.Integer(
        string="Estimated Total Duration (mins)",
        compute="_compute_estimated_duration",
        store=True,
    )
    active = fields.Boolean(default=True)
    notes = fields.Text()

    @api.depends("stop_ids")
    def _compute_total_stops(self):
        for route in self:
            route.total_stops = len(route.stop_ids)

    @api.depends("stop_ids.cumulative_duration_mins")
    def _compute_estimated_duration(self):
        for route in self:
            if route.stop_ids:
                route.estimated_duration_mins = max(
                    route.stop_ids.mapped("cumulative_duration_mins") or [0]
                )
            else:
                route.estimated_duration_mins = 0


class SecurityShuttleRouteStop(models.Model):
    _name = "security.shuttle.route.stop"
    _description = "Route Stop"
    _order = "route_id, sequence"

    route_id = fields.Many2one(
        "security.shuttle.route",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10, string="Stop #")
    stop_label = fields.Char(required=True, string="Stop Name / Address", placeholder="e.g. Katutura Taxi Rank")
    site_id = fields.Many2one(
        "security.client.site",
        string="Linked Guard Post / Site",
        help="Link to a security site if this stop is a guard post destination.",
    )
    stop_type = fields.Selection(
        [
            ("pickup", "Pick-Up Point"),
            ("dropoff", "Drop-Off Point"),
            ("site", "Guard Post / Site"),
            ("depot", "Depot / Home Base"),
        ],
        required=True,
        default="pickup",
    )
    cumulative_duration_mins = fields.Integer(
        string="ETA from Depot (mins)",
        help="Cumulative travel time from the depot to this stop.",
        default=0,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SHUTTLE RUNS (Executed trips)
# ─────────────────────────────────────────────────────────────────────────────

class SecurityShuttleRun(models.Model):
    _name = "security.shuttle.run"
    _description = "Shuttle Transport Run"
    _order = "shift_date desc, id desc"

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default="Draft",
        string="Run Reference",
    )
    vehicle_id = fields.Many2one(
        "security.vehicle",
        required=True,
        domain=[("state", "=", "available")],
        ondelete="restrict",
    )
    driver_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
        string="Driver",
    )
    route_id = fields.Many2one(
        "security.shuttle.route",
        required=True,
        ondelete="restrict",
        string="Prearranged Route",
    )
    run_type = fields.Selection(
        related="route_id.route_type",
        store=True,
        string="Run Type",
    )
    shift_date = fields.Date(required=True, default=date.today, string="Shift Date")
    scheduled_departure = fields.Datetime(string="Scheduled Departure Time")
    actual_departure = fields.Datetime(string="Actual Departure Time")
    actual_arrival = fields.Datetime(string="Actual Arrival Time")
    odometer_start = fields.Float(string="Odometer at Departure (km)")
    odometer_end = fields.Float(string="Odometer at Arrival (km)")
    km_driven = fields.Float(
        compute="_compute_km",
        store=True,
        string="Distance Driven (km)",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("boarding", "Boarding"),
            ("in_transit", "In Transit"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
        copy=False,
    )
    passenger_ids = fields.One2many(
        "security.shuttle.run.passenger",
        "run_id",
        string="Passenger Manifest",
    )
    total_passengers = fields.Integer(compute="_compute_passenger_stats", store=True)
    boarded_count = fields.Integer(compute="_compute_passenger_stats", store=True)
    no_show_count = fields.Integer(compute="_compute_passenger_stats", store=True)
    notes = fields.Text()

    @api.depends("odometer_start", "odometer_end")
    def _compute_km(self):
        for run in self:
            if run.odometer_end and run.odometer_start:
                run.km_driven = max(run.odometer_end - run.odometer_start, 0.0)
            else:
                run.km_driven = 0.0

    @api.depends("passenger_ids.status")
    def _compute_passenger_stats(self):
        for run in self:
            run.total_passengers = len(run.passenger_ids)
            run.boarded_count = len(run.passenger_ids.filtered(lambda p: p.status == "boarded"))
            run.no_show_count = len(run.passenger_ids.filtered(lambda p: p.status == "no_show"))

    @api.constrains("odometer_start", "odometer_end")
    def _check_odometer(self):
        for run in self:
            if run.odometer_end and run.odometer_start:
                if run.odometer_end < run.odometer_start:
                    raise ValidationError(
                        "Odometer at arrival cannot be less than odometer at departure."
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Draft") == "Draft":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("security.shuttle.run")
                    or "RUN/NEW"
                )
        return super().create(vals_list)

    def action_start_boarding(self):
        for run in self:
            if run.state != "draft":
                continue
            if run.vehicle_id.state != "available":
                raise ValidationError(
                    f"Vehicle {run.vehicle_id.name} is not available. "
                    f"Current status: {dict(run.vehicle_id._fields['state'].selection).get(run.vehicle_id.state)}"
                )
            run.vehicle_id.state = "in_transit"
            run.state = "boarding"

    def action_depart(self):
        for run in self:
            if run.state != "boarding":
                continue
            if not run.odometer_start:
                raise ValidationError("Please record the departure odometer reading before departing.")
            run.actual_departure = datetime.now()
            run.state = "in_transit"

    def action_complete(self):
        for run in self:
            if run.state != "in_transit":
                continue
            if not run.odometer_end:
                raise ValidationError("Please record the arrival odometer reading before completing the run.")
            run.actual_arrival = datetime.now()
            # Update vehicle odometer to latest reading
            if run.odometer_end > run.vehicle_id.odometer:
                run.vehicle_id.odometer = run.odometer_end
            run.vehicle_id.state = "available"
            # Mark any passengers still "in_transit" as dropped off
            run.passenger_ids.filtered(lambda p: p.status == "boarded").write({"status": "dropped_off"})
            run.state = "completed"

    def action_cancel(self):
        for run in self:
            if run.state in ("completed",):
                continue
            if run.vehicle_id.state == "in_transit":
                run.vehicle_id.state = "available"
            run.state = "cancelled"


class SecurityShuttleRunPassenger(models.Model):
    _name = "security.shuttle.run.passenger"
    _description = "Shuttle Run Passenger"
    _order = "run_id, sequence"

    run_id = fields.Many2one(
        "security.shuttle.run",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
        string="Security Guard",
    )
    boarding_stop_id = fields.Many2one(
        "security.shuttle.route.stop",
        string="Boarding / Drop-Off Stop",
        domain="[('route_id', '=', parent.route_id)]",
    )
    status = fields.Selection(
        [
            ("expected", "Expected"),
            ("boarded", "Boarded ✓"),
            ("no_show", "No-Show ✗"),
            ("dropped_off", "Dropped Off ✓"),
        ],
        default="expected",
        required=True,
    )
    notes = fields.Char(string="Notes / Reason")


# ─────────────────────────────────────────────────────────────────────────────
# FUEL LOGS
# ─────────────────────────────────────────────────────────────────────────────

class SecurityVehicleFuelLog(models.Model):
    _name = "security.vehicle.fuel.log"
    _description = "Vehicle Fuel Log"
    _order = "fuel_date desc, id desc"

    vehicle_id = fields.Many2one("security.vehicle", required=True, ondelete="restrict")
    fuel_date = fields.Date(required=True, default=date.today)
    fueled_by_id = fields.Many2one(
        "hr.employee",
        string="Fueled By",
        domain=[("security_guard", "=", True)],
    )
    odometer_reading = fields.Float(string="Odometer at Fueling (km)", required=True)
    liters = fields.Float(string="Liters Pumped", required=True)
    cost_per_liter = fields.Float(string="Cost per Liter (NAD)", required=True)
    total_cost = fields.Float(
        compute="_compute_total_cost",
        store=True,
        string="Total Cost (NAD)",
    )
    fuel_station = fields.Char(string="Fuel Station / Supplier")
    receipt_reference = fields.Char(string="Receipt / Invoice Number")
    notes = fields.Text()

    @api.depends("liters", "cost_per_liter")
    def _compute_total_cost(self):
        for log in self:
            log.total_cost = log.liters * log.cost_per_liter

    @api.constrains("liters", "cost_per_liter", "odometer_reading")
    def _check_values(self):
        for log in self:
            if log.liters <= 0:
                raise ValidationError("Liters pumped must be greater than zero.")
            if log.cost_per_liter <= 0:
                raise ValidationError("Cost per liter must be greater than zero.")
            if log.odometer_reading < 0:
                raise ValidationError("Odometer reading cannot be negative.")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # Update vehicle odometer if newer
            if rec.odometer_reading > rec.vehicle_id.odometer:
                rec.vehicle_id.odometer = rec.odometer_reading
        return records


# ─────────────────────────────────────────────────────────────────────────────
# PRE-DEPARTURE INSPECTIONS
# ─────────────────────────────────────────────────────────────────────────────

class SecurityVehicleInspection(models.Model):
    _name = "security.vehicle.inspection"
    _description = "Vehicle Pre-Departure Inspection"
    _order = "inspection_date desc, id desc"

    vehicle_id = fields.Many2one("security.vehicle", required=True, ondelete="restrict")
    inspected_by_id = fields.Many2one(
        "hr.employee",
        string="Inspected By",
        required=True,
        domain=[("security_guard", "=", True)],
    )
    inspection_date = fields.Datetime(required=True, default=datetime.now)
    linked_run_id = fields.Many2one(
        "security.shuttle.run",
        string="Linked Run (Optional)",
        domain="[('vehicle_id', '=', vehicle_id), ('state', '=', 'draft')]",
    )

    # Safety checklist items
    check_tyres = fields.Selection([("pass", "Pass ✓"), ("fail", "Fail ✗")], string="Tyres", required=True, default="pass")
    check_lights = fields.Selection([("pass", "Pass ✓"), ("fail", "Fail ✗")], string="Lights & Indicators", required=True, default="pass")
    check_brakes = fields.Selection([("pass", "Pass ✓"), ("fail", "Fail ✗")], string="Brakes", required=True, default="pass")
    check_fluids = fields.Selection([("pass", "Pass ✓"), ("fail", "Fail ✗")], string="Fluids (Oil, Water, Brake)", required=True, default="pass")
    check_bodywork = fields.Selection([("pass", "Pass ✓"), ("fail", "Fail ✗")], string="Bodywork / Windscreen", required=True, default="pass")
    check_first_aid = fields.Selection([("pass", "Pass ✓"), ("fail", "Fail ✗")], string="First Aid Kit", required=True, default="pass")
    check_fire_ext = fields.Selection([("pass", "Pass ✓"), ("fail", "Fail ✗")], string="Fire Extinguisher", required=True, default="pass")

    overall_result = fields.Selection(
        [("pass", "Pass — Vehicle Cleared for Departure"), ("fail", "Fail — Vehicle Grounded")],
        compute="_compute_overall_result",
        store=True,
        string="Overall Result",
    )
    odometer_reading = fields.Float(string="Odometer at Inspection (km)")
    notes = fields.Text(string="Defects / Notes")

    @api.depends(
        "check_tyres", "check_lights", "check_brakes",
        "check_fluids", "check_bodywork", "check_first_aid", "check_fire_ext",
    )
    def _compute_overall_result(self):
        checks = [
            "check_tyres", "check_lights", "check_brakes",
            "check_fluids", "check_bodywork", "check_first_aid", "check_fire_ext",
        ]
        for insp in self:
            if any(getattr(insp, c) == "fail" for c in checks):
                insp.overall_result = "fail"
            else:
                insp.overall_result = "pass"

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # Auto-ground vehicle if inspection fails
            if rec.overall_result == "fail" and rec.vehicle_id.state == "available":
                rec.vehicle_id.state = "in_service"
            # Update odometer
            if rec.odometer_reading and rec.odometer_reading > rec.vehicle_id.odometer:
                rec.vehicle_id.odometer = rec.odometer_reading
        return records

    def write(self, vals):
        res = super().write(vals)
        for insp in self:
            if insp.overall_result == "fail" and insp.vehicle_id.state == "available":
                insp.vehicle_id.state = "in_service"
        return res


# ─────────────────────────────────────────────────────────────────────────────
# SERVICE LOGS
# ─────────────────────────────────────────────────────────────────────────────

class SecurityVehicleServiceLog(models.Model):
    _name = "security.vehicle.service.log"
    _description = "Vehicle Service / Repair Log"
    _order = "date_in desc, id desc"

    vehicle_id = fields.Many2one("security.vehicle", required=True, ondelete="restrict")
    service_provider = fields.Char(required=True, string="Workshop / Provider")
    date_in = fields.Date(required=True, default=date.today, string="Date Vehicle Submitted")
    date_out = fields.Date(string="Date Vehicle Returned")
    description = fields.Text(required=True, string="Work Done / Description")
    cost = fields.Float(string="Service Cost (NAD)", default=0.0)
    odometer_at_service = fields.Float(string="Odometer at Service (km)")
    invoice_reference = fields.Char(string="Invoice / Job Card Reference")
    state = fields.Selection(
        [
            ("open", "In Workshop"),
            ("completed", "Service Completed"),
        ],
        default="open",
        required=True,
    )

    def action_complete_service(self):
        for log in self:
            log.date_out = date.today()
            log.state = "completed"
            if log.vehicle_id.state == "in_service":
                log.vehicle_id.state = "available"
            if log.odometer_at_service and log.odometer_at_service > log.vehicle_id.odometer:
                log.vehicle_id.odometer = log.odometer_at_service
