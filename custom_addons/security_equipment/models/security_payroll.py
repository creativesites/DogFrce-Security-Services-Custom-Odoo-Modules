from odoo import api, fields, models


class SecurityPayslip(models.Model):
    _inherit = "security.payslip"

    equipment_damage_ids = fields.One2many(
        "security.equipment.damage",
        "payslip_id",
        string="Equipment Loss & Damage Deductions",
    )

    def action_compute_from_sources(self):
        for payslip in self:
            # Release previously linked damage registers so they can be recalculated
            linked_damages = self.env["security.equipment.damage"].search(
                [("payslip_id", "=", payslip.id)]
            )
            if linked_damages:
                linked_damages.write(
                    {
                        "state": "approved",
                        "payslip_id": False,
                    }
                )

        # Call original core payslip calculation (which unlinks past deduction lines)
        res = super(SecurityPayslip, self).action_compute_from_sources()

        damage_model = self.env["security.equipment.damage"]
        for payslip in self:
            if not payslip.employee_id or not payslip.period_id:
                continue

            # Query approved damages inside active payslip period
            damages = damage_model.search(
                [
                    ("employee_id", "=", payslip.employee_id.id),
                    ("occurrence_date", ">=", payslip.period_id.date_from),
                    ("occurrence_date", "<=", payslip.period_id.date_to),
                    ("state", "=", "approved"),
                    ("deduction_amount", ">", 0.0),
                ]
            )

            if not damages:
                continue

            deduction_lines = []
            for dmg in damages:
                deduction_lines.append(
                    (
                        0,
                        0,
                        {
                            "name": f"Equipment Deduct: {dmg.equipment_type_id.name} ({dmg.name})",
                            "code": "EQUIPMENT_LOSS",
                            "quantity": 1.0,
                            "rate": dmg.deduction_amount,
                            "amount": dmg.deduction_amount,
                        },
                    )
                )
                dmg.write(
                    {
                        "payslip_id": payslip.id,
                        "state": "deducted",
                    }
                )

            # Append equipment deductions after the core payroll computation has
            # already rebuilt normal statutory, loan, and incident deductions.
            payslip.write({"deduction_line_ids": deduction_lines})
            # Recalculate net payslip earnings after adding deductions
            payslip._compute_totals()

        return res
