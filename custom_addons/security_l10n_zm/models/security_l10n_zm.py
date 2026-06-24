from odoo import fields, models


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

    # WCF — Workers' Compensation Fund
    # Employer-only levy; rate is industry-specific.
    # NOTE: The rate for the private security industry must be confirmed from the WCF
    # risk category schedule before this field is used in payslip computation (Phase 2).
    employer_wcf_rate = fields.Float(
        string="Employer WCF Rate",
        digits=(16, 4),
        default=0.0,
        help="Employer-only Workers' Compensation Fund levy. Rate varies by industry risk category. "
             "Confirm the correct rate for private security from the WCF schedule before activating.",
    )
    wcf_salary_cap = fields.Float(
        string="WCF Monthly Earnings Ceiling (ZMW)",
        default=0.0,
        help="Monthly earnings ceiling for WCF (if applicable). Leave at 0.0 if uncapped.",
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
