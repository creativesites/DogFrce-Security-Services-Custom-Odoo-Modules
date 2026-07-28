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


class DocumentDesignerController(http.Controller):

    @http.route('/billing/designer/preview_invoice', type='json', auth='user')
    def preview_invoice(self, template_data=None):
        if not template_data:
            return {}

        invoice = request.env['security.billing.invoice'].search([], limit=1)
        if not invoice:
            # High-fidelity Mock fallback
            invoice = MockObject(
                _name="security.billing.invoice",
                name="INV/2026/07/0088",
                invoice_date="2026-07-28",
                invoice_date_due="2026-08-27",
                due_date="2026-08-27",
                payment_reference="INV-0088-DF",
                state="posted",
                payment_state="not_paid",
                amount_untaxed=14520.00,
                amount_tax=2178.00,
                amount_total=16698.00,
                subtotal_amount=14520.00,
                vat_amount=2178.00,
                total_amount=16698.00,
                company_id={
                    'name': 'DogForce Security Services',
                    'phone': '+264 61 290 0000',
                    'email': 'info@dogforce.com',
                    'company_details': 'DogForce Security Services Ltd - Windhoek, Namibia',
                    'vat': 'VAT12345678',
                    'street': '101 Independence Ave',
                    'city': 'Windhoek'
                },
                partner_id={
                    'name': 'Corporate Offices Group Ltd (Mockup)',
                    'street': '44 Independence Ave',
                    'city': 'Windhoek',
                    'phone': '+264 61 290 2000'
                },
                invoice_line_ids=[
                    {
                        'name': 'Day Shift Guard (Armed) - Grade A',
                        'quantity': 176.0,
                        'price_unit': 45.00,
                        'price_subtotal': 7920.00,
                        'tax_ids': [{'name': 'VAT 15%', 'amount': 15.0}],
                        'tax_id': [{'name': 'VAT 15%', 'amount': 15.0}]
                    },
                    {
                        'name': 'Night Shift Canine Patrol & Handler',
                        'quantity': 120.0,
                        'price_unit': 55.00,
                        'price_subtotal': 6600.00,
                        'tax_ids': [{'name': 'VAT 15%', 'amount': 15.0}],
                        'tax_id': [{'name': 'VAT 15%', 'amount': 15.0}]
                    }
                ],
                line_ids=[
                    {
                        'name': 'Day Shift Guard (Armed) - Grade A',
                        'quantity': 176.0,
                        'price_unit': 45.00,
                        'price_subtotal': 7920.00,
                        'tax_ids': [{'name': 'VAT 15%', 'amount': 15.0}],
                        'tax_id': [{'name': 'VAT 15%', 'amount': 15.0}]
                    },
                    {
                        'name': 'Night Shift Canine Patrol & Handler',
                        'quantity': 120.0,
                        'price_unit': 55.00,
                        'price_subtotal': 6600.00,
                        'tax_ids': [{'name': 'VAT 15%', 'amount': 15.0}],
                        'tax_id': [{'name': 'VAT 15%', 'amount': 15.0}]
                    }
                ]
            )

        values = {
            'docs': [invoice] if not isinstance(invoice, request.env['security.billing.invoice'].__class__) else invoice,
            'template_data': template_data,
        }
        
        try:
            html = request.env['ir.qweb']._render('security_billing.report_security_invoice', values)
            return {'html': html}
        except Exception as e:
            return {'error': str(e)}

    @http.route('/billing/designer/preview_quotation', type='json', auth='user')
    def preview_quotation(self, template_data=None):
        if not template_data:
            return {}

        quotation = request.env['sale.order'].search([], limit=1)
        if not quotation:
            # High-fidelity Mock fallback
            quotation = MockObject(
                _name="sale.order",
                name="S00184",
                date_order="2026-07-28",
                validity_date="2026-08-27",
                state="draft",
                amount_untaxed=22500.00,
                amount_tax=3375.00,
                amount_total=25875.00,
                company_id={
                    'name': 'DogForce Security Services',
                    'phone': '+264 61 290 0000',
                    'email': 'info@dogforce.com',
                    'company_details': 'DogForce Security Services Ltd - Windhoek, Namibia',
                    'vat': 'VAT12345678',
                    'street': '101 Independence Ave',
                    'city': 'Windhoek'
                },
                partner_id={
                    'name': 'Secure Assets Holdings (Mockup)',
                    'street': '77 Sam Nujoma Dr',
                    'city': 'Windhoek',
                    'phone': '+264 61 319 9000'
                },
                order_line=[
                    {
                        'name': 'DogForce Security Guarding - Site Assessment & Setup',
                        'product_uom_qty': 1.0,
                        'quantity': 1.0,
                        'price_unit': 4500.00,
                        'price_subtotal': 4500.00,
                        'tax_ids': [{'name': 'VAT 15%', 'amount': 15.0}],
                        'tax_id': [{'name': 'VAT 15%', 'amount': 15.0}]
                    },
                    {
                        'name': 'Guarding Services (Day/Night 24/7 Deployment)',
                        'product_uom_qty': 300.0,
                        'quantity': 300.0,
                        'price_unit': 60.00,
                        'price_subtotal': 18000.00,
                        'tax_ids': [{'name': 'VAT 15%', 'amount': 15.0}],
                        'tax_id': [{'name': 'VAT 15%', 'amount': 15.0}]
                    }
                ]
            )

        values = {
            'docs': [quotation] if not isinstance(quotation, request.env['sale.order'].__class__) else quotation,
            'template_data': template_data,
        }
        
        try:
            html = request.env['ir.qweb']._render('security_billing_sale.report_security_quotation', values)
            return {'html': html}
        except Exception as e:
            return {'error': str(e)}
