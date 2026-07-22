{
    "name": "Security Billing Sales Integration",
    "summary": "Tightly integrates DeployGuard security billing plans with standard Odoo Sales Orders.",
    "version": "19.0.1.0.0",
    "category": "Security/Sales",
    "author": "Winston Zulu",
    "license": "LGPL-3",
    "depends": ["security_billing", "sale"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "auto_install": True,
    "installable": True,
}
