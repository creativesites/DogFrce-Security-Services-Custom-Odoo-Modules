from odoo import api, fields, models


class SecurityPayrollRuleSetZM(models.Model):
    _inherit = "security.payroll.rule.set"

    # NAPSA — National Pension Scheme Authority
    # Rate: 5% employee + 5% employer = 10% total
    # Source: NAPSA Act Cap 256 (as amended); 2025 earnings ceiling confirmed ZMW 34,164/month
    employee_napsa_rate = fields.Float(
        string="Employee NAPSA Rate",
        digits=(16, 4),
        default=0.05,
        help="Employee NAPSA contribution rate. Standard rate is 5% (0.05).",
    )
    employer_napsa_rate = fields.Float(
        string="Employer NAPSA Rate",
        digits=(16, 4),
        default=0.05,
        help="Employer NAPSA contribution rate. Standard rate is 5% (0.05).",
    )
    napsa_salary_cap = fields.Float(
        string="NAPSA Monthly Earnings Ceiling (ZMW)",
        default=34164.0,
        help="Monthly earnings ceiling for NAPSA contributions. Update annually from the NAPSA gazette notice.",
    )

    # NHIMA — National Health Insurance Management Authority
    # Rate: 0.5% employee + 0.5% employer = 1% total
    # Source: NHIMA Act No. 2 of 2018
    employee_nhima_rate = fields.Float(
        string="Employee NHIMA Rate",
        digits=(16, 4),
        default=0.005,
        help="Employee NHIMA levy rate. Standard rate is 0.5% (0.005).",
    )
    employer_nhima_rate = fields.Float(
        string="Employer NHIMA Rate",
        digits=(16, 4),
        default=0.005,
        help="Employer NHIMA levy rate. Standard rate is 0.5% (0.005).",
    )

    # WCF — Workers' Compensation Fund Control Board (WCFCB)
    # Employer-only levy; rate is set by risk classification, not a flat industry rate.
    # Private security typically falls under Class IX (Miscellaneous/Services).
    # Assessment rate range: 1.25% – 2.00% of total gross payroll, depending on whether
    # operations are predominantly unarmed static guarding (lower end) or include armed
    # cash-in-transit or high-risk duties (higher end).
    # Default pre-configured to 1.75% (mid-range for mixed private security operations).
    # Update annually: submit wage returns and confirm your rate via the WCFCB eWorkers Portal.
    employer_wcf_rate = fields.Float(
        string="Employer WCF Rate",
        digits=(16, 4),
        default=0.0,
        help=(
            "Employer-only Workers' Compensation Fund (WCFCB) levy.\n\n"
            "Private security companies are typically assessed under Class IX "
            "(Miscellaneous/Services). The assessment rate ranges from 1.25% to 2.00% "
            "of total gross payroll, based on your specific risk profile:\n"
            "  • 1.25–1.50% — predominantly unarmed static guarding\n"
            "  • 1.50–1.75% — mixed operations (static + patrol)\n"
            "  • 1.75–2.00% — armed operations, cash-in-transit, or high-risk sites\n\n"
            "Assessable earnings include basic salary, allowances, overtime, and bonuses.\n"
            "No earnings ceiling applies (unlike NAPSA).\n\n"
            "Update annually: confirm your exact rate and submit wage returns via the "
            "WCFCB eWorkers Portal (eworkers.wcf.org.zm). "
            "Ref: Workers' Compensation Act Cap 271, Laws of Zambia."
        ),
    )
    wcf_salary_cap = fields.Float(
        string="WCF Monthly Earnings Ceiling (ZMW)",
        default=0.0,
        help=(
            "Monthly earnings ceiling for WCF levy calculation. "
            "Leave at 0.0 for uncapped (standard — WCF assessable earnings have no statutory ceiling)."
        ),
    )


class HrEmployeeZM(models.Model):
    _inherit = "hr.employee"

    security_napsa_number = fields.Char(
        string="NAPSA Member Number",
        help="Employee's National Pension Scheme Authority (NAPSA) membership number.",
    )
    security_tpin = fields.Char(
        string="TPIN",
        help="Taxpayer Identification Number issued by the Zambia Revenue Authority (ZRA).",
    )
    security_nhima_number = fields.Char(
        string="NHIMA Member Number",
        help="Employee's National Health Insurance Management Authority (NHIMA) member number.",
    )


class SecurityPayslipZM(models.Model):
    _inherit = "security.payslip"

    def action_compute_from_sources(self):
        """Run standard payslip computation then apply ZM statutory deductions."""
        super().action_compute_from_sources()
        zm_payslips = self.filtered(
            lambda p: p.period_id.rule_set_id and p.period_id.rule_set_id.country_code == "ZM"
        )
        for payslip in zm_payslips:
            payslip._apply_zm_statutory_deductions()

    def _apply_zm_statutory_deductions(self):
        """Replace SSC-based deductions with NAPSA, NHIMA, and corrected PAYE for ZM payrolls.

        The standard engine computes PAYE on full gross (SSC = 0 for ZM rule sets).
        This method:
          1. Restores any lines the standard floor-cap reduced, so totals are correct.
          2. Removes the incorrectly computed PAYE line.
          3. Adds employee NAPSA contribution (5% of capped gross).
          4. Adds employee NHIMA levy (0.5% of gross).
          5. Recomputes PAYE with NAPSA-adjusted taxable income (NAPSA is tax-deductible
             under Zambia Income Tax Act Cap 323).
          6. Re-applies the deduction floor cap.
        """
        self.ensure_one()
        rule_set = self.period_id.rule_set_id

        # Step 1: restore lines capped by the standard floor-cap pass so that our
        # deduction totals are accurate before we begin modifying them.
        for line in self.deduction_line_ids.filtered(lambda l: l.capped):
            line.amount += line.carry_forward_amount
            line.carry_forward_amount = 0.0
            line.capped = False

        # Step 2: remove the PAYE line computed on the wrong taxable base.
        self.deduction_line_ids.filtered(lambda l: l.code == "PAYE").unlink()

        gross = sum(self.earning_line_ids.mapped("amount"))

        # Step 3: NAPSA employee contribution — capped at the monthly earnings ceiling.
        napsa_cap = rule_set.napsa_salary_cap or 34164.0
        napsa_rate = rule_set.employee_napsa_rate or 0.05
        napsa_base = min(gross, napsa_cap)
        napsa_amount = round(napsa_base * napsa_rate, 2)
        if napsa_amount > 0:
            self.env["security.payslip.deduction.line"].create({
                "payslip_id": self.id,
                "name": "NAPSA Contribution",
                "code": "NAPSA",
                "quantity": 1.0,
                "rate": napsa_amount,
                "amount": napsa_amount,
            })

        # Step 4: NHIMA employee levy — no earnings ceiling documented.
        nhima_rate = rule_set.employee_nhima_rate or 0.005
        nhima_amount = round(gross * nhima_rate, 2)
        if nhima_amount > 0:
            self.env["security.payslip.deduction.line"].create({
                "payslip_id": self.id,
                "name": "NHIMA Levy",
                "code": "NHIMA",
                "quantity": 1.0,
                "rate": nhima_amount,
                "amount": nhima_amount,
            })

        # Step 5: PAYE — NAPSA is tax-deductible; apply ZM annual brackets.
        taxable_monthly = max(gross - napsa_amount, 0.0)
        annual_taxable = taxable_monthly * 12.0
        brackets = self.env["security.tax.bracket"].search(
            [("rule_set_id", "=", rule_set.id)], order="lower_bound"
        )
        paye_amount = 0.0
        for bracket in brackets:
            upper = bracket.upper_bound or float("inf")
            if bracket.lower_bound <= annual_taxable <= upper:
                annual_tax = bracket.fixed_amount + (annual_taxable - bracket.lower_bound) * bracket.rate
                paye_amount = round(max(annual_tax / 12.0, 0.0), 2)
                break
        if paye_amount > 0:
            self.env["security.payslip.deduction.line"].create({
                "payslip_id": self.id,
                "name": "Pay As You Earn (PAYE)",
                "code": "PAYE",
                "quantity": 1.0,
                "rate": paye_amount,
                "amount": paye_amount,
            })

        # Step 6: re-apply deduction floor cap with the updated deduction mix.
        floor_pct = rule_set.deduction_floor_pct or 0.30
        min_net = gross * floor_pct
        total_deductions = sum(self.deduction_line_ids.mapped("amount"))
        if total_deductions > gross - min_net:
            excess = total_deductions - (gross - min_net)
            # Reduce LOAN/INCIDENT first, then statutory deductions if still over floor.
            ded_lines = self.deduction_line_ids.sorted(
                key=lambda l: (l.code not in ("LOAN", "INCIDENT"), l.id)
            )
            for line in reversed(list(ded_lines)):
                if excess <= 0:
                    break
                remove = min(line.amount, excess)
                line.carry_forward_amount = remove
                line.amount -= remove
                line.capped = True
                excess -= remove
                if line.amount <= 0:
                    line.unlink()
