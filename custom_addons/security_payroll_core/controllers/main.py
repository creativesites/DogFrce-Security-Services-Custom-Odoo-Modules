from odoo import http
from odoo.http import request
import json
import logging

_logger = logging.getLogger(__name__)


class CallableFalse(object):
    """
    Bulletproof sentinel that never fails subscripting, method calls, string
    conversions or iterations, returning False for boolean checks.
    """
    def __call__(self, *args, **kwargs):
        return self

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
    """
    High-fidelity mock record object that safely mimics Odoo recordsets in QWeb.
    """
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

    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
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

    def with_context(self, *args, **kwargs):
        return self

    def _origin(self):
        return self

    def name_get(self):
        return [(1, getattr(self, 'name', 'Mock'))]


class PayslipDesignerController(http.Controller):

    def _get_mock_payslip(self, company):
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
        return MockObject(
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
            company_id=company,
            get_ytd_totals=mock_ytd_totals,
            get_leave_balances=mock_leave_balances,
            employee_id=MockObject(
                _name="hr.employee",
                name='John Doe (Guard Mockup)',
                security_grade_id=MockObject(name='Grade A'),
                security_ssc_number='SSC-98231-M',
                security_tax_number='TAX-772183-A',
                security_napsa_number='NAPSA-112233',
                security_nhima_number='NHIMA-889900',
                security_tpin='TPIN-55667788',
                security_bank_name='First National Bank',
                security_bank_branch='280172',
                security_bank_account_number='6288192312',
            ),
            period_id=MockObject(
                name='July 2026',
                rule_set_id=MockObject(
                    country_code='ZM',
                    currency_id=MockObject(name='ZMW'),
                    template_id=False,
                ),
            ),
            earning_line_ids=[
                MockObject(name='Basic Salary', quantity=176.0, rate=25.50, amount=4488.00),
                MockObject(name='Overtime Pay', quantity=12.0, rate=38.25, amount=459.00),
                MockObject(name='Night Shift Allowance', quantity=48.0, rate=5.00, amount=240.00),
                MockObject(name='Saturday Duty Bonus', quantity=16.0, rate=12.75, amount=204.00),
                MockObject(name='Sunday Shift Bonus', quantity=8.0, rate=25.50, amount=204.00),
                MockObject(name='Transport Allowance', quantity=1.0, rate=219.00, amount=219.00),
            ],
            deduction_line_ids=[
                MockObject(name='Social Security (SSC)', quantity=1.0, rate=150.00, amount=150.00),
                MockObject(name='Income Tax (PAYE)', quantity=1.0, rate=300.00, amount=300.00),
            ],
        )

    @http.route('/payroll/designer/preview', type='json', auth='user')
    def preview_payslip(self, template_data=None):
        """
        Renders a preview of a payslip using the given transient template data.
        """
        if not template_data:
            return {}

        company = request.env.company
        payslip = request.env['security.payslip'].search([], limit=1)
        if not payslip:
            payslip = self._get_mock_payslip(company)

        docs = [payslip] if not isinstance(payslip, request.env['security.payslip'].__class__) else payslip

        values = {
            'docs': docs,
            'template_data': template_data,
            'res_company': company,
            'company': company,
            'company_id': company,
        }

        try:
            html = request.env['ir.qweb']._render('security_payroll_core.report_security_payslip', values)
            return {'html': html}
        except Exception as e:
            _logger.exception("Error in preview_payslip")
            return {'error': str(e)}

    @http.route('/payroll/designer/print', type='http', auth='user')
    def print_payslip_preview(self, template_id=None, download=None, **kwargs):
        """
        Dedicated print and PDF preview route for Payslips.
        Renders the payslip in full printable layout or downloads binary PDF.
        """
        company = request.env.company
        template_data = {}

        if template_id:
            try:
                template = request.env['security.payslip.template'].browse(int(template_id))
                if template.exists():
                    blocks = ['header', 'employee_info', 'attendance', 'earnings_deductions_split', 'totals', 'footer']
                    if template.block_order:
                        try:
                            blocks = json.loads(template.block_order)
                        except Exception:
                            pass
                    template_data = {
                        'name': template.name,
                        'font_family': template.font_family or 'Inter',
                        'primary_color': template.primary_color or '#1B3A6B',
                        'secondary_color': template.secondary_color or '#0D1117',
                        'base_layout': template.base_layout or 'modern',
                        'header_bg_color': template.header_bg_color or '#1B3A6B',
                        'header_text_color': template.header_text_color or '#ffffff',
                        'show_attendance_metrics': template.show_attendance_metrics,
                        'show_leave_balances': template.show_leave_balances,
                        'show_ytd': template.show_ytd,
                        'show_admin_signature': template.show_admin_signature,
                        'show_guard_signature': template.show_guard_signature,
                        'announcement_text': template.announcement_text or '',
                        'label_payslip': template.label_payslip or 'Payslip',
                        'blocks': blocks,
                    }
            except Exception:
                pass

        if not template_data:
            template_data = {
                'name': 'Corporate Navy Standard',
                'font_family': 'Inter',
                'primary_color': '#1B3A6B',
                'secondary_color': '#0D1117',
                'base_layout': 'corporate',
                'header_bg_color': '#1B3A6B',
                'header_text_color': '#ffffff',
                'show_attendance_metrics': True,
                'show_leave_balances': True,
                'show_ytd': True,
                'show_admin_signature': True,
                'show_guard_signature': True,
                'announcement_text': '',
                'label_payslip': 'Payslip',
                'blocks': ['header', 'employee_info', 'attendance', 'earnings_deductions_split', 'totals', 'footer'],
            }

        payslip = request.env['security.payslip'].search([], limit=1) or self._get_mock_payslip(company)
        docs = [payslip] if not isinstance(payslip, request.env['security.payslip'].__class__) else payslip

        values = {
            'docs': docs,
            'template_data': template_data,
            'res_company': company,
            'company': company,
            'company_id': company,
        }

        try:
            rendered_report = request.env['ir.qweb']._render('security_payroll_core.report_security_payslip', values)
        except Exception as e:
            _logger.exception("Error in print_payslip_preview")
            rendered_report = f"<div class='alert alert-danger m-4'><h4>Rendering Error</h4><pre>{str(e)}</pre></div>"

        # If direct download requested, attempt wkhtmltopdf
        if download == '1':
            try:
                pdf_content, _ = request.env['ir.actions.report']._run_wkhtmltopdf([rendered_report])
                filename = f"Payslip_{template_data.get('name', 'Preview').replace(' ', '_')}.pdf"
                return request.make_response(
                    pdf_content,
                    headers=[
                        ('Content-Type', 'application/pdf'),
                        ('Content-Disposition', f'attachment; filename="{filename}"'),
                        ('Content-Length', len(pdf_content)),
                    ]
                )
            except Exception as e:
                _logger.warning("wkhtmltopdf conversion failed: %s, falling back to HTML", e)

        # Standalone printable viewer HTML
        current_url = request.httprequest.url
        download_url = current_url + ("&download=1" if "?" in current_url else "?download=1")

        full_page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>DeployGuard Print Preview - Payslip ({template_data.get('name')})</title>
    <link rel="stylesheet" href="/web/static/lib/bootstrap/css/bootstrap.css"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css"/>
    <style>
        body {{
            background-color: #525659;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }}
        .print-toolbar {{
            position: sticky;
            top: 0;
            left: 0;
            right: 0;
            z-index: 9999;
            background: #1e293b;
            color: #f1f5f9;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 24px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        .print-viewport {{
            padding: 30px 15px;
            display: flex;
            justify-content: center;
        }}
        .paper-sheet {{
            background: #ffffff;
            width: 210mm;
            min-height: 297mm;
            padding: 16mm 18mm;
            box-shadow: 0 4px 20px rgba(0,0,0,0.35);
            box-sizing: border-box;
            border-radius: 2px;
        }}
        @media print {{
            .no-print {{
                display: none !important;
            }}
            body {{
                background: white !important;
            }}
            .print-viewport {{
                padding: 0 !important;
            }}
            .paper-sheet {{
                box-shadow: none !important;
                width: 100% !important;
                min-height: auto !important;
                padding: 0 !important;
                border-radius: 0 !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="print-toolbar no-print">
        <div class="d-flex align-items-center gap-3">
            <span class="badge bg-primary px-2.5 py-1.5 fw-semibold" style="letter-spacing: 0.5px;">DEPLOYGUARD</span>
            <span class="text-white fw-bold" style="font-size: 14px;">Print &amp; PDF Layout — Payslip</span>
            <span class="badge bg-secondary opacity-75">{template_data.get('name')}</span>
        </div>
        <div class="d-flex align-items-center gap-2">
            <button class="btn btn-sm btn-success px-3 fw-semibold shadow-sm" onclick="window.print()">
                <i class="fa fa-print me-1"></i> Print / Save as PDF
            </button>
            <a class="btn btn-sm btn-outline-light px-3" href="{download_url}">
                <i class="fa fa-download me-1"></i> Download PDF
            </a>
            <button class="btn btn-sm btn-outline-secondary text-light px-3" onclick="window.close()">
                Close Preview
            </button>
        </div>
    </div>
    <div class="print-viewport">
        <div class="paper-sheet">
            {rendered_report}
        </div>
    </div>
</body>
</html>"""

        return request.make_response(full_page, headers=[('Content-Type', 'text/html; charset=utf-8')])
