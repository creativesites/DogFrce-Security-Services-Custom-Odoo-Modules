from odoo.tests.common import TransactionCase


class TestZMPayrollStatutory(TransactionCase):
    """Unit tests for the Zambia statutory deduction engine.

    Covers: PAYE bracket logic, NAPSA cap, NHIMA computation,
    and floor-cap re-application in _apply_zm_statutory_deductions().
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        zmw = cls.env["res.currency"].search([("name", "=", "ZMW")], limit=1)
        if not zmw:
            zmw = cls.env.ref("base.USD")

        cls.rule_set = cls.env["security.payroll.rule.set"].create({
            "name": "Test ZM Rule Set 2025",
            "country_code": "ZM",
            "currency_id": zmw.id,
            "effective_from": "2025-01-01",
            "employee_ssc_rate": 0.0,
            "employer_ssc_rate": 0.0,
            "ssc_salary_cap": 0.0,
            "employee_napsa_rate": 0.05,
            "employer_napsa_rate": 0.05,
            "napsa_salary_cap": 34164.0,
            "employee_nhima_rate": 0.005,
            "employer_nhima_rate": 0.005,
            "deduction_floor_pct": 0.30,
        })

        # ZM PAYE annual brackets (2025 ZRA gazette)
        cls.env["security.tax.bracket"].create([
            {
                "rule_set_id": cls.rule_set.id,
                "lower_bound": 0.0,
                "upper_bound": 57600.0,
                "fixed_amount": 0.0,
                "rate": 0.0,
            },
            {
                "rule_set_id": cls.rule_set.id,
                "lower_bound": 57600.01,
                "upper_bound": 819000.0,
                "fixed_amount": 0.0,
                "rate": 0.20,
            },
            {
                "rule_set_id": cls.rule_set.id,
                "lower_bound": 819000.01,
                "upper_bound": 1000000.0,
                "fixed_amount": 152280.0,
                "rate": 0.30,
            },
            {
                "rule_set_id": cls.rule_set.id,
                "lower_bound": 1000000.01,
                "upper_bound": 0.0,
                "fixed_amount": 206280.0,
                "rate": 0.375,
            },
        ])

        cls.employee = cls.env["hr.employee"].create({
            "name": "Test ZM Guard",
            "security_napsa_number": "NAPSA-TEST-001",
            "security_nhima_number": "NHIMA-TEST-001",
            "security_tpin": "1234567890",
        })

        cls.period = cls.env["security.payroll.period"].create({
            "name": "ZM Test Period Jan 2025",
            "date_from": "2025-01-01",
            "date_to": "2025-01-31",
            "rule_set_id": cls.rule_set.id,
        })

    def _make_payslip(self, gross):
        """Return a fresh payslip with a single earning line at the given gross amount."""
        payslip = self.env["security.payslip"].create({
            "employee_id": self.employee.id,
            "period_id": self.period.id,
        })
        self.env["security.payslip.earning.line"].create({
            "payslip_id": payslip.id,
            "name": "Basic Salary",
            "code": "BASIC",
            "quantity": 1.0,
            "rate": gross,
            "amount": gross,
        })
        return payslip

    def _sum_deduction(self, payslip, code):
        lines = payslip.deduction_line_ids.filtered(lambda l: l.code == code)
        return sum(lines.mapped("amount"))

    # ─── NAPSA ──────────────────────────────────────────────────────────

    def test_napsa_below_cap(self):
        """NAPSA = 5% of gross when gross is below the ZMW 34,164 ceiling."""
        gross = 10000.0
        payslip = self._make_payslip(gross)
        payslip._apply_zm_statutory_deductions()
        self.assertAlmostEqual(
            self._sum_deduction(payslip, "NAPSA"),
            round(gross * 0.05, 2),
            places=2,
        )

    def test_napsa_above_cap(self):
        """NAPSA is capped at 5% of the earnings ceiling, not 5% of gross."""
        gross = 50000.0
        payslip = self._make_payslip(gross)
        payslip._apply_zm_statutory_deductions()
        self.assertAlmostEqual(
            self._sum_deduction(payslip, "NAPSA"),
            round(34164.0 * 0.05, 2),
            places=2,
        )

    # ─── NHIMA ──────────────────────────────────────────────────────────

    def test_nhima_no_cap(self):
        """NHIMA = 0.5% of gross (no earnings ceiling)."""
        gross = 50000.0
        payslip = self._make_payslip(gross)
        payslip._apply_zm_statutory_deductions()
        self.assertAlmostEqual(
            self._sum_deduction(payslip, "NHIMA"),
            round(gross * 0.005, 2),
            places=2,
        )

    # ─── PAYE ───────────────────────────────────────────────────────────

    def test_paye_napsa_deductible(self):
        """PAYE is computed on gross minus NAPSA (NAPSA is tax-deductible per ZRA rules)."""
        gross = 10000.0
        payslip = self._make_payslip(gross)
        payslip._apply_zm_statutory_deductions()

        napsa = self._sum_deduction(payslip, "NAPSA")
        taxable_monthly = gross - napsa
        annual_taxable = taxable_monthly * 12.0
        # Bracket: 20% on amount over 57,600
        expected_paye = round(max(annual_taxable - 57600.0, 0.0) * 0.20 / 12.0, 2)
        self.assertAlmostEqual(
            self._sum_deduction(payslip, "PAYE"),
            expected_paye,
            places=2,
        )

    def test_paye_zero_below_threshold(self):
        """No PAYE when annual taxable income falls below ZMW 57,600."""
        # gross 4,000 → NAPSA 200 → taxable monthly 3,800 → annual 45,600 < 57,600
        gross = 4000.0
        payslip = self._make_payslip(gross)
        payslip._apply_zm_statutory_deductions()
        self.assertAlmostEqual(self._sum_deduction(payslip, "PAYE"), 0.0, places=2)

    # ─── Floor cap ──────────────────────────────────────────────────────

    def test_floor_cap_protects_net(self):
        """Net pay after all deductions must be at least 30% of gross.

        A large LOAN is added before the ZM computation; the floor cap
        should reduce it (not the statutory lines) to honour the 30% floor.
        """
        gross = 1000.0
        payslip = self._make_payslip(gross)
        self.env["security.payslip.deduction.line"].create({
            "payslip_id": payslip.id,
            "name": "Loan Repayment",
            "code": "LOAN",
            "quantity": 1.0,
            "rate": 800.0,
            "amount": 800.0,
        })
        payslip._apply_zm_statutory_deductions()
        total_ded = sum(payslip.deduction_line_ids.mapped("amount"))
        net = gross - total_ded
        # Net must be >= 30% of gross (allow 1c rounding tolerance)
        self.assertGreaterEqual(net, gross * 0.30 - 0.01)

    def test_floor_cap_reduces_loan_before_statutory(self):
        """LOAN is reduced before statutory deductions when the floor cap triggers."""
        gross = 1000.0
        payslip = self._make_payslip(gross)
        self.env["security.payslip.deduction.line"].create({
            "payslip_id": payslip.id,
            "name": "Loan Repayment",
            "code": "LOAN",
            "quantity": 1.0,
            "rate": 800.0,
            "amount": 800.0,
        })
        payslip._apply_zm_statutory_deductions()
        # The statutory NAPSA/NHIMA lines should still be present and unchanged
        self.assertGreater(self._sum_deduction(payslip, "NAPSA"), 0.0)
        self.assertGreater(self._sum_deduction(payslip, "NHIMA"), 0.0)
        # The LOAN should have been reduced (capped), not the statutory deductions
        loan_remaining = self._sum_deduction(payslip, "LOAN")
        self.assertLess(loan_remaining, 800.0)
