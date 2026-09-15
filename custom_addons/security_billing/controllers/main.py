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


class DocumentDesignerController(http.Controller):

    def _get_mock_invoice(self, company, partner=None):
        partner_obj = partner or MockObject(
            _name="res.partner",
            name="Corporate Offices Group Ltd (Mockup)",
            street="44 Independence Ave",
            city="Windhoek",
            phone="+264 61 290 2000",
            vat="VAT99887766",
        )
        return MockObject(
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
            company_id=company,
            partner_id=partner_obj,
            invoice_line_ids=[
                MockObject(
                    name="Day Shift Guard (Armed) - Grade A",
                    quantity=176.0,
                    price_unit=45.00,
                    price_subtotal=7920.00,
                    subtotal=7920.00,
                    tax_ids=[MockObject(name="VAT 15%", amount=15.0)],
                ),
                MockObject(
                    name="Night Shift Canine Patrol & Handler",
                    quantity=120.0,
                    price_unit=55.00,
                    price_subtotal=6600.00,
                    subtotal=6600.00,
                    tax_ids=[MockObject(name="VAT 15%", amount=15.0)],
                ),
            ],
            line_ids=[
                MockObject(
                    name="Day Shift Guard (Armed) - Grade A",
                    quantity=176.0,
                    price_unit=45.00,
                    price_subtotal=7920.00,
                    subtotal=7920.00,
                    tax_ids=[MockObject(name="VAT 15%", amount=15.0)],
                ),
                MockObject(
                    name="Night Shift Canine Patrol & Handler",
                    quantity=120.0,
                    price_unit=55.00,
                    price_subtotal=6600.00,
                    subtotal=6600.00,
                    tax_ids=[MockObject(name="VAT 15%", amount=15.0)],
                ),
            ],
        )

    def _get_mock_quotation(self, company, partner=None):
        partner_obj = partner or MockObject(
            _name="res.partner",
            name="Secure Assets Holdings (Mockup)",
            street="77 Sam Nujoma Dr",
            city="Windhoek",
            phone="+264 61 319 9000",
            vat="VAT99887766",
        )
        return MockObject(
            _name="sale.order",
            name="S00184",
            date_order="2026-07-28",
            validity_date="2026-08-27",
            state="draft",
            amount_untaxed=22500.00,
            amount_tax=3375.00,
            amount_total=25875.00,
            company_id=company,
            partner_id=partner_obj,
            order_line=[
                MockObject(
                    name="DogForce Security Guarding - Site Assessment & Setup",
                    product_uom_qty=1.0,
                    quantity=1.0,
                    price_unit=4500.00,
                    price_subtotal=4500.00,
                    tax_ids=[MockObject(name="VAT 15%", amount=15.0)],
                ),
                MockObject(
                    name="Guarding Services (Day/Night 24/7 Deployment)",
                    product_uom_qty=300.0,
                    quantity=300.0,
                    price_unit=60.00,
                    price_subtotal=18000.00,
                    tax_ids=[MockObject(name="VAT 15%", amount=15.0)],
                ),
            ],
        )

    @http.route('/billing/designer/preview_invoice', type='json', auth='user')
    def preview_invoice(self, template_data=None):
        if not template_data:
            return {}

        company = request.env.company
        invoice = request.env['security.billing.invoice'].search([], limit=1)
        if not invoice:
            partner = request.env['res.partner'].search([], limit=1)
            invoice = self._get_mock_invoice(company, partner=partner)

        values = {
            'docs': [invoice] if not isinstance(invoice, request.env['security.billing.invoice'].__class__) else invoice,
            'template_data': template_data,
            'res_company': company,
            'company': company,
            'company_id': company,
        }

        try:
            html = request.env['ir.qweb']._render('security_billing.report_security_invoice', values)
            return {'html': html}
        except Exception as e:
            _logger.exception("Error rendering invoice preview")
            return {'error': str(e)}

    @http.route('/billing/designer/preview_quotation', type='json', auth='user')
    def preview_quotation(self, template_data=None):
        if not template_data:
            return {}

        company = request.env.company
        quotation = request.env['sale.order'].search([], limit=1)
        if not quotation:
            partner = request.env['res.partner'].search([], limit=1)
            quotation = self._get_mock_quotation(company, partner=partner)

        values = {
            'docs': [quotation] if not isinstance(quotation, request.env['sale.order'].__class__) else quotation,
            'template_data': template_data,
            'res_company': company,
            'company': company,
            'company_id': company,
        }

        try:
            html = request.env['ir.qweb']._render('security_billing_sale.report_security_quotation', values)
            return {'html': html}
        except Exception as e:
            _logger.exception("Error rendering quotation preview")
            return {'error': str(e)}

    @http.route('/billing/designer/print', type='http', auth='user')
    def print_document_preview(self, type='invoice', template_id=None, download=None, **kwargs):
        """
        Dedicated print and PDF preview route.
        Renders the document in full-bleed printable format or downloads binary PDF.
        Works 100% reliably regardless of whether DB records exist.
        """
        company = request.env.company
        template_data = {}

        if template_id:
            try:
                template = request.env['security.document.template'].browse(int(template_id))
                if template.exists():
                    blocks = ['header', 'client_info', 'line_items', 'totals', 'terms', 'footer']
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
                        'header_bg_color': template.header_bg_color or '#1e293b',
                        'header_text_color': template.header_text_color or '#ffffff',
                        'show_payment_terms': template.show_payment_terms,
                        'show_bank_details': template.show_bank_details,
                        'show_company_logo': template.show_company_logo,
                        'show_watermark': template.show_watermark,
                        'show_tax_column': template.show_tax_column,
                        'logo_height': template.logo_height or 60,
                        'logo_alignment': template.logo_alignment or 'left',
                        'label_billed_to': template.label_billed_to or 'Billed To',
                        'custom_footer_note': template.custom_footer_note or '',
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
                'header_bg_color': '#1e293b',
                'header_text_color': '#ffffff',
                'show_payment_terms': True,
                'show_bank_details': True,
                'show_company_logo': True,
                'show_watermark': False,
                'show_tax_column': True,
                'logo_height': 60,
                'logo_alignment': 'left',
                'label_billed_to': 'Billed To',
                'custom_footer_note': '',
                'blocks': ['header', 'client_info', 'line_items', 'totals', 'terms', 'footer'],
            }

        is_quotation = (type == 'quotation')
        report_xml_id = 'security_billing_sale.report_security_quotation' if is_quotation else 'security_billing.report_security_invoice'
        doc_title = "Quotation" if is_quotation else "Tax Invoice"

        if is_quotation:
            doc = request.env['sale.order'].search([], limit=1) or self._get_mock_quotation(company)
        else:
            doc = request.env['security.billing.invoice'].search([], limit=1) or self._get_mock_invoice(company)

        values = {
            'docs': [doc] if not isinstance(doc, (request.env['security.billing.invoice'].__class__, request.env['sale.order'].__class__)) else doc,
            'template_data': template_data,
            'res_company': company,
            'company': company,
            'company_id': company,
        }

        try:
            rendered_report = request.env['ir.qweb']._render(report_xml_id, values)
        except Exception as e:
            _logger.exception("Error in print_document_preview")
            rendered_report = f"<div class='alert alert-danger m-4'><h4>Rendering Error</h4><pre>{str(e)}</pre></div>"

        # If direct download requested, attempt wkhtmltopdf
        if download == '1':
            try:
                pdf_content, _ = request.env['ir.actions.report']._run_wkhtmltopdf([rendered_report])
                filename = f"{doc_title.replace(' ', '_')}_{template_data.get('name', 'Preview').replace(' ', '_')}.pdf"
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
    <title>DeployGuard Print Preview - {doc_title} ({template_data.get('name')})</title>
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
            <span class="text-white fw-bold" style="font-size: 14px;">Print &amp; PDF Layout — {doc_title}</span>
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
