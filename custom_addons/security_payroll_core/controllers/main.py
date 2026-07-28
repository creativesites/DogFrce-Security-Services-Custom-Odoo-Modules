from odoo import http
from odoo.http import request
import json

class CallableFalse(object):
    def __call__(self, *args, **kwargs):
        return False
    def __bool__(self):
        return False
    def __str__(self):
        return ""
    def __repr__(self):
        return ""
    def __getattr__(self, name):
        return self
    def __getitem__(self, key):
        return self
    def __contains__(self, key):
        return False
    def __iter__(self):
        return iter([])
    def __len__(self):
        return 0
    def __add__(self, other):
        return str(other) if other else ""
    def __radd__(self, other):
        return str(other) if other else ""
    def __html__(self):
        return ""
    def replace(self, *args, **kwargs):
        return ""


class MockObject(object):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if callable(v):
                setattr(self, k, v)
            elif isinstance(v, dict):
                setattr(self, k, MockObject(**v))
            elif isinstance(v, list) and all(isinstance(x, dict) for x in v):
                setattr(self, k, [MockObject(**x) for x in v])
            else:
                setattr(self, k, v)
                
    def __getattr__(self, name):
        return CallableFalse()

    def __contains__(self, key):
        return hasattr(self, key) or key in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)

    def __len__(self):
        return len(self.__dict__) or 1

    def __bool__(self):
        return True

    def sudo(self, *args, **kwargs):
        return self

    def _origin(self):
        return self



class PayslipDesignerController(http.Controller):

    @http.route('/payroll/designer/preview', type='json', auth='user')
    def preview_payslip(self, template_data=None):
        """
        Renders a preview of a payslip using the given transient template data.
        """
        if not template_data:
            return {}

        # Search for a real payslip, or use a high-fidelity mock fallback if none exist
        payslip = request.env['security.payslip'].search([], limit=1)
        
        if not payslip:
            # Generate high-fidelity mock data so the designer is fully functional on empty databases
            mock_ytd_totals = lambda *args, **kwargs: {
                'earnings': 23412.00,
                'deductions': 1800.00,
                'net_pay': 21612.00,
            }
            mock_leave_balances = lambda *args, **kwargs: [
                {'type_name': 'Annual Leave', 'balance_days': 14.5},
                {'type_name': 'Sick Leave', 'balance_days': 7.0},
                {'type_name': 'Compassionate Leave', 'balance_days': 3.0},
            ]
            
            payslip = MockObject(
                _name="security.payslip",
                state='Draft',
                worked_days=22.0,
                normal_hours=176.0,
                saturday_hours=16.0,
                sunday_hours=8.0,
                public_holiday_hours=0.0,
                night_hours=48.0,
                overtime_hours=12.0,
                unpaid_hours=0.0,
                awol_occurrences=0,
                hourly_rate=25.50,
                total_earnings=5814.00,
                total_deductions=450.00,
                net_pay=5364.00,
                get_ytd_totals=mock_ytd_totals,
                get_leave_balances=mock_leave_balances,
                employee_id={
                    'name': 'John Doe (Guard Mockup)',
                    'security_grade_id': {'name': 'Grade A'},
                    'security_ssc_number': 'SSC-98231-M',
                    'security_tax_number': 'TAX-772183-A',
                    'security_napsa_number': 'NAPSA-112233',
                    'security_nhima_number': 'NHIMA-889900',
                    'security_tpin': 'TPIN-55667788',
                    'security_bank_name': 'First National Bank',
                    'security_bank_branch': '280172',
                    'security_bank_account_number': '6288192312'
                },
                period_id={
                    'name': 'July 2026',
                    'rule_set_id': {
                        'country_code': 'ZM',
                        'currency_id': {'name': 'ZMW'},
                        'template_id': False
                    }
                },
                earning_line_ids=[
                    {'name': 'Basic Salary', 'quantity': 176.0, 'rate': 25.50, 'amount': 4488.00},
                    {'name': 'Overtime Pay', 'quantity': 12.0, 'rate': 38.25, 'amount': 459.00},
                    {'name': 'Night Shift Allowance', 'quantity': 48.0, 'rate': 5.00, 'amount': 240.00},
                    {'name': 'Saturday Duty Bonus', 'quantity': 16.0, 'rate': 12.75, 'amount': 204.00},
                    {'name': 'Sunday Shift Bonus', 'quantity': 8.0, 'rate': 25.50, 'amount': 204.00},
                    {'name': 'Transport Allowance', 'quantity': 1.0, 'rate': 219.00, 'amount': 219.00},
                ],
                deduction_line_ids=[
                    {'name': 'Social Security (SSC)', 'quantity': 1.0, 'rate': 150.00, 'amount': 150.00},
                    {'name': 'Income Tax (PAYE)', 'quantity': 1.0, 'rate': 300.00, 'amount': 300.00},
                ]
            )

        # Wrap in list since the QWeb template expects a recordset
        docs = [payslip] if not isinstance(payslip, request.env['security.payslip'].__class__) else payslip
        
        values = {
            'docs': docs,
            'template_data': template_data,
        }
        
        html = request.env['ir.qweb']._render('security_payroll_core.report_security_payslip', values)
        return {'html': html}
