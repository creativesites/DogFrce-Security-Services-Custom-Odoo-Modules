import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class SecurityPayslip(models.Model):
    _inherit = "security.payslip"

    def action_compute_from_sources(self):
        """
        Extends payslip calculations to identify unreturned gear (allocated uniforms, kit, or weapons)
        and automatically appends replacement-cost payroll deductions if this is a final paycheck
        or if the employee is marked for exit.
        """
        super().action_compute_from_sources()

        allocation_model = self.env["security.equipment.allocation"]
        for payslip in self:
            if not payslip.employee_id or not payslip.period_id:
                continue

            # Check if guard has unreturned gear allocated
            unreturned_allocations = allocation_model.search([
                ("employee_id", "=", payslip.employee_id.id),
                ("state", "=", "issued"),
            ])

            if not unreturned_allocations:
                continue

            # We deduct replacement costs under two conditions:
            # 1. The employee's standard contract is ending, or their Odoo employee status is inactive/terminating.
            # 2. Or, this is a final clearance payslip (indicated by note, name, or system context).
            is_final_clearance = False
            if hasattr(payslip.employee_id, "active") and not payslip.employee_id.active:
                is_final_clearance = True
            elif payslip.period_id.name and "final" in payslip.period_id.name.lower():
                is_final_clearance = True
            elif payslip.note and "final" in payslip.note.lower():
                is_final_clearance = True

            if not is_final_clearance:
                continue

            deduction_lines = []
            for alloc in unreturned_allocations:
                # Replacement cost calculation (fallback to default cost of N$ 350.0 if not defined)
                cost = getattr(alloc.equipment_type_id, "cost", 350.0) or 350.0

                deduction_lines.append((0, 0, {
                    "payslip_id": payslip.id,
                    "name": _("Unreturned Kit: %s (Replacement Cost)") % alloc.equipment_type_id.name,
                    "code": "UNRETURNED_KIT",
                    "quantity": 1.0,
                    "rate": cost,
                    "amount": cost,
                }))

            if deduction_lines:
                # Append deduction lines to the payslip
                payslip.write({"deduction_line_ids": deduction_lines})
                _logger.info("Equipment Bridge | Deducted N$ %s from final payslip for Employee %s due to %s unreturned items",
                             sum(line[2]["amount"] for line in deduction_lines), payslip.employee_id.name, len(unreturned_allocations))
                payslip._compute_totals()


class SecurityEquipmentType(models.Model):
    _inherit = "security.equipment.type"

    stock_level = fields.Float(compute="_compute_stock_level", string="Available Stock")
    minimum_threshold = fields.Float(string="Minimum Alert Stock Threshold", default=5.0)

    @api.depends("minimum_threshold")
    def _compute_stock_level(self):
        """
        Calculates active stock quantities. If Odoo's native 'stock' or 'product' module is installed,
        it links and pulls real stock counts. Otherwise, it defaults to remaining items in the registry.
        """
        has_stock_module = "product.product" in self.env
        for eq_type in self:
            if has_stock_module:
                # Try to locate a matching product
                product = self.env["product.product"].search([("default_code", "=", eq_type.code)], limit=1)
                if product:
                    eq_type.stock_level = product.qty_available
                    # Trigger alert if stock is below minimum threshold
                    if product.qty_available < eq_type.minimum_threshold:
                        eq_type._trigger_low_stock_warning(product.qty_available)
                    continue

            # Fallback check using our security.equipment.item database records (where state = 'available')
            available_items_count = self.env["security.equipment.item"].search_count([
                ("equipment_type_id", "=", eq_type.id),
                ("state", "=", "available"),
            ])
            eq_type.stock_level = float(available_items_count)

            if float(available_items_count) < eq_type.minimum_threshold:
                eq_type._trigger_low_stock_warning(float(available_items_count))

    def _trigger_low_stock_warning(self, current_qty):
        """Dispatches an equipment.low_stock alert to the Central Intelligence Bus."""
        for eq_type in self:
            # Check if alert was already dispatched today to avoid spam
            today = fields.Date.today()
            duplicate_check = self.env["security.event.log"].search_count([
                ("name", "=", f"LOW STOCK WARNING: {eq_type.name}"),
                ("create_date", ">=", str(today)),
            ])
            if duplicate_check > 0:
                return

            payload = {
                "eq_type": eq_type.name,
                "current_qty": current_qty,
                "threshold": eq_type.minimum_threshold,
            }

            self.env["security.event.log"].register_event(
                name="equipment.low_stock",
                source_model="security.equipment.type",
                source_id=eq_type.id,
                payload=payload,
            )


class SecurityEquipmentPayrollBridge(models.AbstractModel):
    _name = "security.equipment.payroll.bridge"
    _description = "Security Equipment and Payroll Intelligence Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        """
        Processes events from the central intelligence bus, raising alerts to procurement.
        """
        _logger.info("Equipment Bridge | Processing event: %s", event_name)

        if event_name == "equipment.low_stock":
            eq_type = payload.get("eq_type", "")
            current_qty = payload.get("current_qty", 0.0)
            threshold = payload.get("threshold", 0.0)

            _logger.warning("Equipment Bridge | Equipment category '%s' is low on stock! Level: %s (Threshold: %s)", eq_type, current_qty, threshold)

            alert_msg = _(
                "LOW STOCK PROCUREMENT ALERT:\n"
                "The inventory level for security equipment '%s' has dropped below the minimum reserve threshold!\n\n"
                "Current Stock: %s units\n"
                "Minimum Target Threshold: %s units\n\n"
                "Please place a purchase requisition immediately to avoid deployment delays."
            ) % (eq_type, current_qty, threshold)

            self.env["security.event.log"].create({
                "name": f"LOW STOCK WARNING: {eq_type}",
                "event_type": "equipment_low_stock",
                "severity": "medium",
                "description": alert_msg,
            })
