from odoo import api, fields, models
from odoo.exceptions import ValidationError
from datetime import date


class SecurityEquipmentCategory(models.Model):
    _name = "security.equipment.category"
    _description = "Security Equipment Category"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    description = fields.Text()
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_uniq", "unique(code)", "Category code must be unique!"),
    ]


class SecurityEquipmentType(models.Model):
    _name = "security.equipment.type"
    _description = "Security Equipment Type"
    _order = "name"

    name = fields.Char(required=True)
    category_id = fields.Many2one(
        "security.equipment.category",
        required=True,
        ondelete="restrict",
    )
    is_serialized = fields.Boolean(
        default=False,
        help="Check this if items require serial number tracking (e.g. radios, firearms).",
    )
    requires_license = fields.Boolean(
        default=False,
        help="Check this if items require specific legal licensing (e.g. firearms).",
    )
    qty_total = fields.Integer(
        string="Total In Stock",
        default=0,
        help="Total quantity of non-serialized items in inventory.",
    )
    qty_issued = fields.Integer(
        compute="_compute_inventory_stats",
        string="Quantity Issued",
        store=True,
    )
    qty_available = fields.Integer(
        compute="_compute_inventory_stats",
        string="Quantity Available",
        store=True,
    )
    unit_cost = fields.Float(required=True, default=0.0)
    avg_lifespan_days = fields.Integer(string="Average Lifespan (Days)", default=365)
    active = fields.Boolean(default=True)

    @api.depends("qty_total", "is_serialized")
    def _compute_inventory_stats(self):
        allocation_model = self.env["security.equipment.allocation"]
        item_model = self.env["security.equipment.item"]
        for eq_type in self:
            if eq_type.is_serialized:
                # Count from individual serialized items
                total_items = item_model.search_count([("type_id", "=", eq_type.id)])
                issued_items = item_model.search_count(
                    [("type_id", "=", eq_type.id), ("status", "=", "issued")]
                )
                eq_type.qty_total = total_items
                eq_type.qty_issued = issued_items
                eq_type.qty_available = total_items - issued_items
            else:
                # Aggregate from allocations for non-serialized items
                active_allocations = allocation_model.search(
                    [
                        ("equipment_type_id", "=", eq_type.id),
                        ("state", "in", ["issued", "acknowledged"]),
                    ]
                )
                issued_qty = int(sum(active_allocations.mapped("quantity")))
                eq_type.qty_issued = issued_qty
                eq_type.qty_available = max(eq_type.qty_total - issued_qty, 0)

    @api.constrains("qty_total", "unit_cost")
    def _check_values(self):
        for eq_type in self:
            if eq_type.qty_total < 0:
                raise ValidationError("Inventory stock level cannot be negative.")
            if eq_type.unit_cost < 0.0:
                raise ValidationError("Unit purchase cost cannot be negative.")


class SecurityEquipmentItem(models.Model):
    _name = "security.equipment.item"
    _description = "Serialized Equipment Item"
    _order = "serial_number"

    name = fields.Char(compute="_compute_name", store=True)
    type_id = fields.Many2one(
        "security.equipment.type",
        required=True,
        domain=[("is_serialized", "=", True)],
        ondelete="restrict",
    )
    serial_number = fields.Char(required=True)
    license_number = fields.Char(string="Firearm/Radio License Number")
    license_expiry = fields.Date(string="License Expiry Date")
    condition = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("worn", "Worn"),
            ("damaged", "Damaged"),
            ("scrapped", "Scrapped"),
        ],
        default="excellent",
        required=True,
    )
    status = fields.Selection(
        [
            ("available", "Available"),
            ("issued", "Issued"),
            ("maintenance", "Maintenance/Repair"),
            ("lost", "Lost"),
            ("scrapped", "Scrapped"),
        ],
        default="available",
        required=True,
    )

    is_allocated = fields.Boolean(
        compute="_compute_is_allocated",
        string="Currently Allocated",
        store=False,
    )

    _sql_constraints = [
        ("serial_uniq", "unique(serial_number)", "Serial number must be unique!"),
    ]

    def _compute_is_allocated(self):
        alloc_model = self.env["security.equipment.allocation"]
        for item in self:
            active_alloc = alloc_model.search_count([
                ("equipment_item_id", "=", item.id),
                ("state", "in", ["issued", "acknowledged"]),
            ])
            item.is_allocated = active_alloc > 0

    @api.depends("type_id", "serial_number")
    def _compute_name(self):
        for item in self:
            if item.type_id and item.serial_number:
                item.name = f"{item.type_id.name} ({item.serial_number})"
            else:
                item.name = "New Serialized Item"


class SecurityEquipmentAllocation(models.Model):
    _name = "security.equipment.allocation"
    _description = "Security Equipment Allocation Log"
    _order = "issue_date desc, id desc"

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default="Draft",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        domain=[("security_guard", "=", True)],
        ondelete="restrict",
    )
    equipment_type_id = fields.Many2one(
        "security.equipment.type",
        required=True,
        ondelete="restrict",
    )
    is_serialized = fields.Boolean(related="equipment_type_id.is_serialized", store=True)
    equipment_item_id = fields.Many2one(
        "security.equipment.item",
        domain="[('type_id', '=', equipment_type_id), ('status', '=', 'available')]",
        ondelete="restrict",
        help="Link the specific serialized item.",
    )
    quantity = fields.Float(
        default=1.0,
        help="Use quantity for non-serialized assets (e.g. 2 trousers).",
    )
    issue_date = fields.Date(required=True, default=date.today)
    expected_return_date = fields.Date()
    actual_return_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("issued", "Issued"),
            ("acknowledged", "Acknowledged"),
            ("returned", "Returned"),
            ("lost", "Lost"),
            ("damaged", "Damaged"),
        ],
        default="draft",
        required=True,
        copy=False,
    )
    issued_by_id = fields.Many2one(
        "res.users",
        default=lambda self: self.env.user.id,
        readonly=True,
    )
    condition_on_issue = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("worn", "Worn"),
        ],
        default="excellent",
        required=True,
    )
    condition_on_return = fields.Selection(
        [
            ("excellent", "Excellent"),
            ("good", "Good"),
            ("worn", "Worn"),
            ("damaged", "Damaged"),
        ]
    )
    notes = fields.Text()
    # H-9: Acknowledgment and return fields
    acknowledged_date = fields.Datetime(readonly=True, string="Acknowledged Date")
    acknowledged_by_id = fields.Many2one("res.users", readonly=True, string="Acknowledged By")
    return_date = fields.Date(string="Return Date")
    return_condition = fields.Selection(
        [("good", "Good"), ("damaged", "Damaged"), ("lost", "Lost")],
        string="Return Condition",
    )
    return_notes = fields.Text(string="Return Notes")

    @api.constrains("quantity", "is_serialized", "equipment_item_id")
    def _check_quantities(self):
        for alloc in self:
            if alloc.quantity <= 0.0:
                raise ValidationError("Allocation quantity must be greater than zero.")
            if alloc.is_serialized:
                if not alloc.equipment_item_id:
                    raise ValidationError("You must specify a trackable serial item for serialized equipment types.")
                if alloc.quantity != 1.0:
                    raise ValidationError("Serialized allocations must have a quantity of exactly 1.0.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Draft") == "Draft":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("security.equipment.allocation")
                    or "EQP/NEW"
                )
        return super().create(vals_list)

    def action_issue(self):
        for alloc in self:
            if alloc.state != "draft":
                continue
            if alloc.is_serialized:
                if alloc.equipment_item_id.status != "available":
                    raise ValidationError(f"The item {alloc.equipment_item_id.name} is already issued or unavailable.")
                alloc.equipment_item_id.write(
                    {
                        "status": "issued",
                        "condition": alloc.condition_on_issue,
                    }
                )
            else:
                if alloc.equipment_type_id.qty_available < alloc.quantity:
                    raise ValidationError(f"Insufficient stock for {alloc.equipment_type_id.name}. Available: {alloc.equipment_type_id.qty_available}")
            
            alloc.state = "issued"
            alloc.equipment_type_id._compute_inventory_stats()

    def action_acknowledge(self):
        for alloc in self:
            if alloc.state == "issued":
                alloc.state = "acknowledged"
                alloc.acknowledged_date = fields.Datetime.now()
                alloc.acknowledged_by_id = self.env.user.id

    def action_open_return_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "security.equipment.return.wizard",
            "views": [[False, "form"]],
            "context": {"default_allocation_id": self.id},
            "target": "new",
        }

    def action_return(self):
        for alloc in self:
            if alloc.state not in ("issued", "acknowledged"):
                continue

            return_condition = alloc.return_condition
            if alloc.is_serialized:
                item_status = "available"
                item_condition = alloc.condition_on_return or "good"
                if return_condition == "lost":
                    item_status = "lost"
                    item_condition = "scrapped"
                elif return_condition == "damaged":
                    item_status = "maintenance"
                    item_condition = "damaged"
                alloc.equipment_item_id.write(
                    {
                        "status": item_status,
                        "condition": item_condition,
                    }
                )

            alloc.return_date = fields.Date.context_today(self)
            alloc.actual_return_date = fields.Date.context_today(self)
            alloc.state = "returned"
            alloc.equipment_type_id._compute_inventory_stats()

            # Auto-create damage record for damaged or lost equipment
            if return_condition in ("damaged", "lost"):
                self.env["security.equipment.damage"].create({
                    "allocation_id": alloc.id,
                    "occurrence_date": fields.Date.context_today(self),
                    "incident_type": "loss" if return_condition == "lost" else "damage",
                    "description": alloc.return_notes or f"Equipment reported as {return_condition} on return",
                    "cost_repair_replace": alloc.equipment_type_id.unit_cost or 1.0,
                    "state": "draft",
                })


class SecurityEquipmentDamage(models.Model):
    _name = "security.equipment.damage"
    _description = "Security Equipment Loss & Damage Register"
    _order = "occurrence_date desc, id desc"

    name = fields.Char(
        required=True,
        copy=False,
        readonly=True,
        default="Draft",
    )
    allocation_id = fields.Many2one(
        "security.equipment.allocation",
        required=True,
        domain="[('state', 'in', ['issued', 'acknowledged', 'returned'])]",
        ondelete="restrict",
    )
    employee_id = fields.Many2one(
        related="allocation_id.employee_id",
        store=True,
    )
    equipment_type_id = fields.Many2one(
        related="allocation_id.equipment_type_id",
        store=True,
    )
    equipment_item_id = fields.Many2one(
        related="allocation_id.equipment_item_id",
        store=True,
    )
    occurrence_date = fields.Date(required=True, default=date.today)
    incident_type = fields.Selection(
        [
            ("damage", "Damaged Equipment"),
            ("loss", "Lost Equipment"),
            ("negligence", "Gross Negligence Damage"),
        ],
        required=True,
        default="damage",
    )
    description = fields.Text(required=True)
    cost_repair_replace = fields.Float(string="Repair/Replacement Cost", required=True)
    deduction_amount = fields.Float(
        string="Guard Payroll Deduction Amount",
        default=0.0,
        help="Cost to be deducted from the guard's salary payslip.",
    )
    deduction_repayment_months = fields.Integer(
        string="Deduction Installment Months",
        default=1,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("investigation", "Under Investigation"),
            ("approved", "Approved (Deduction Pending)"),
            ("deducted", "Deducted on Payroll"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        required=True,
        copy=False,
    )
    approved_by_id = fields.Many2one(
        "res.users",
        readonly=True,
    )
    payslip_id = fields.Many2one(
        "security.payslip",
        readonly=True,
        ondelete="set null",
    )

    @api.constrains("cost_repair_replace", "deduction_amount", "deduction_repayment_months")
    def _check_financials(self):
        for dmg in self:
            if dmg.cost_repair_replace <= 0.0:
                raise ValidationError("Repair/replacement cost must be greater than zero.")
            if dmg.deduction_amount < 0.0:
                raise ValidationError("Deduction amount cannot be negative.")
            if dmg.deduction_amount > dmg.cost_repair_replace:
                raise ValidationError("Payroll deduction amount cannot exceed the replacement/repair cost.")
            if dmg.deduction_repayment_months <= 0:
                raise ValidationError("Repayment months must be greater than zero.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "Draft") == "Draft":
                vals["name"] = (
                    self.env["ir.sequence"].next_by_code("security.equipment.damage")
                    or "DMG/NEW"
                )
        return super().create(vals_list)

    def action_investigate(self):
        for dmg in self:
            dmg.state = "investigation"

    def action_approve(self):
        for dmg in self:
            if dmg.state != "investigation":
                continue
            
            # Update physical items condition/status automatically
            if dmg.allocation_id.is_serialized:
                if dmg.incident_type == "loss":
                    dmg.allocation_id.equipment_item_id.write(
                        {
                            "status": "lost",
                            "condition": "scrapped",
                        }
                    )
                else:
                    dmg.allocation_id.equipment_item_id.write(
                        {
                            "status": "maintenance",
                            "condition": "damaged",
                        }
                    )
            
            # Close the allocation status
            dmg.allocation_id.state = "lost" if dmg.incident_type == "loss" else "damaged"
            dmg.allocation_id.equipment_type_id._compute_inventory_stats()
            
            dmg.approved_by_id = self.env.user.id
            dmg.state = "approved"

    def action_reject(self):
        for dmg in self:
            dmg.state = "rejected"

    def action_reset_draft(self):
        for dmg in self:
            dmg.state = "draft"
